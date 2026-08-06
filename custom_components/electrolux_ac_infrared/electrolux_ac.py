"""Electrolux air-conditioner IR protocol.

Every transmission is a complete 13-byte state frame, sent MSB first per byte:

  byte 0:  0xC3 constant header
  byte 1:  bits 7-5 swing, bits 4-0 temperature (``temp_c - 8``, bit reversed)
  byte 4:  fan speed
  byte 6:  operating mode
  byte 9:  bit 2 power
  byte 12: checksum
  others:  zero

The field values are stored bit reversed relative to the on-air bit order, which is
why the checksum sums the reversed bytes and reverses the total again.

Derived from the protocol analysis at
https://exploding-kitten.com/2025/05-diy-ir-remote and the ESPHome component at
https://github.com/sys27/esphome-electrolux-ac.
"""

from enum import IntEnum
from typing import Self, override

from infrared_protocols.commands import Command

MIN_TEMP = 16
MAX_TEMP = 32

_MODULATION = 38000

_HEADER_MARK = 8950
_HEADER_SPACE = 4530
_BIT_MARK = 563
_ONE_SPACE = 1690
_ZERO_SPACE = 538
_FOOTER_SPACE = 10000

_PACKET_SIZE = 13
_FRAME_BITS = _PACKET_SIZE * 8

_HEADER_BYTE = 0xC3

_IDX_SWING_TEMP = 1
_IDX_FAN = 4
_IDX_MODE = 6
_IDX_POWER = 9
# The remote leaves these zero. A frame that uses them carries a feature this encoder
# does not model, so it is rejected rather than silently read as that feature being off.
_IDX_RESERVED = (2, 3, 5, 7, 8, 10, 11)

_TEMP_OFFSET = 8
_TEMP_BITS = 5
_TEMP_MASK = 0x1F

_SWING_SHIFT = 5
_SWING_VERTICAL = 0b000
_SWING_OFF = 0b111

_POWER_ON = 0x04

# Receivers stretch marks through AGC but keep spaces accurate, so the mark gets the
# looser tolerance of the two.
_HEADER_MARK_TOLERANCE = 0.7
_HEADER_SPACE_TOLERANCE = 0.25
# A receiver skews a bit by roughly a fixed number of microseconds rather than a fixed
# proportion. 350 covers the skew seen in practice and still keeps the zero and one
# spaces apart (188-888 vs 1340-2040).
_BIT_TOLERANCE = 350


class ElectroluxAcMode(IntEnum):
    """AC operating mode; value is the mode byte at frame byte 6."""

    AUTO = 0x00
    HEAT = 0x01
    DRY = 0x02
    FAN_ONLY = 0x03
    COOL = 0x04


class ElectroluxAcFanSpeed(IntEnum):
    """Fan speed; value is the fan byte at frame byte 4."""

    MEDIUM = 0x02
    HIGH = 0x04
    AUTO = 0x05
    LOW = 0x06


def _reverse_bits(value: int, bits: int = 8) -> int:
    """Reverse the low ``bits`` bits of ``value``."""
    result = 0
    for _ in range(bits):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _checksum(frame: bytes) -> int:
    """Return the checksum byte for the first 12 bytes of a frame."""
    total = sum(_reverse_bits(byte) for byte in frame[: _PACKET_SIZE - 1]) & 0xFF
    return _reverse_bits(total)


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check whether a timing is within the given relative tolerance."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


def _decode_bit(mark: int, space: int) -> int | None:
    """Decode one bit from its mark and space, or None if it matches neither."""
    if abs(mark - _BIT_MARK) > _BIT_TOLERANCE:
        return None
    if abs(space - _ZERO_SPACE) <= _BIT_TOLERANCE:
        return 0
    if abs(space - _ONE_SPACE) <= _BIT_TOLERANCE:
        return 1
    return None


def _decode_frame(timings: list[int]) -> bytes | None:
    """Decode raw IR timings into a checksummed 13-byte frame, or None."""
    # Header pair (2) + 104 bit pairs (208) + the trailing mark (1)
    if len(timings) < 2 + 2 * _FRAME_BITS + 1:
        return None

    if not _is_close(
        abs(timings[0]), _HEADER_MARK, _HEADER_MARK_TOLERANCE
    ) or not _is_close(abs(timings[1]), _HEADER_SPACE, _HEADER_SPACE_TOLERANCE):
        return None

    if abs(abs(timings[2 + 2 * _FRAME_BITS]) - _BIT_MARK) > _BIT_TOLERANCE:
        return None

    frame = bytearray()
    for byte_start in range(2, 2 + 2 * _FRAME_BITS, 16):
        byte = 0
        for i in range(byte_start, byte_start + 16, 2):
            bit = _decode_bit(abs(timings[i]), abs(timings[i + 1]))
            if bit is None:
                return None
            byte = (byte << 1) | bit
        frame.append(byte)

    if frame[0] != _HEADER_BYTE or frame[-1] != _checksum(bytes(frame)):
        return None

    if any(frame[index] for index in _IDX_RESERVED):
        return None

    return bytes(frame)


class ElectroluxAcCommand(Command):
    """Electrolux air-conditioner IR command.

    The frame always carries every setting, so a command describes the full target
    state of the unit rather than a single keypress.
    """

    mode: ElectroluxAcMode
    temperature: int
    fan: ElectroluxAcFanSpeed
    swing: bool
    power: bool

    def __init__(
        self,
        *,
        mode: ElectroluxAcMode,
        temperature: int,
        fan: ElectroluxAcFanSpeed,
        swing: bool = False,
        power: bool = True,
        modulation: int = _MODULATION,
    ) -> None:
        """Initialize the Electrolux AC IR command."""
        super().__init__(modulation=modulation)

        if not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )

        self.mode = mode
        self.temperature = temperature
        self.fan = fan
        self.swing = swing
        self.power = power

    def get_frame(self) -> bytes:
        """Return the 13-byte frame this command encodes."""
        frame = bytearray(_PACKET_SIZE)
        frame[0] = _HEADER_BYTE
        swing_bits = _SWING_VERTICAL if self.swing else _SWING_OFF
        frame[_IDX_SWING_TEMP] = (swing_bits << _SWING_SHIFT) | _reverse_bits(
            self.temperature - _TEMP_OFFSET, _TEMP_BITS
        )
        frame[_IDX_FAN] = self.fan
        frame[_IDX_MODE] = self.mode
        frame[_IDX_POWER] = _POWER_ON if self.power else 0
        frame[-1] = _checksum(bytes(frame))
        return bytes(frame)

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Electrolux AC command."""
        timings = [_HEADER_MARK, -_HEADER_SPACE]
        for byte in self.get_frame():
            for shift in range(7, -1, -1):
                timings.extend((
                    _BIT_MARK,
                    -(_ONE_SPACE if byte >> shift & 1 else _ZERO_SPACE),
                ))
        timings += [_BIT_MARK, -_FOOTER_SPACE]
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into an ElectroluxAcCommand.

        Returns:
            The decoded command, or None if the timings do not form a valid
            Electrolux AC frame.

        """
        frame = _decode_frame(timings)
        if frame is None:
            return None

        swing_bits = frame[_IDX_SWING_TEMP] >> _SWING_SHIFT
        if swing_bits not in {_SWING_VERTICAL, _SWING_OFF}:
            return None

        temperature = (
            _reverse_bits(frame[_IDX_SWING_TEMP] & _TEMP_MASK, _TEMP_BITS)
            + _TEMP_OFFSET
        )
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            return None

        if frame[_IDX_POWER] not in {0, _POWER_ON}:
            return None

        try:
            mode = ElectroluxAcMode(frame[_IDX_MODE])
            fan = ElectroluxAcFanSpeed(frame[_IDX_FAN])
        except ValueError:
            return None

        return cls(
            mode=mode,
            temperature=temperature,
            fan=fan,
            swing=swing_bits == _SWING_VERTICAL,
            power=frame[_IDX_POWER] == _POWER_ON,
        )
