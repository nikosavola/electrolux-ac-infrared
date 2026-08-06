"""Tests for the Electrolux AC IR protocol encoder and decoder."""

import pytest

from custom_components.electrolux_infrared.electrolux_ac import (
    MAX_TEMP,
    MIN_TEMP,
    ElectroluxAcCommand,
    ElectroluxAcFanSpeed,
    ElectroluxAcMode,
    _checksum,
)

_HEADER_MARK = 8950
_HEADER_SPACE = -4530
_BIT_MARK = 563
_ONE_SPACE = -1690
_ZERO_SPACE = -538
_FOOTER_SPACE = -10000

_FRAME_BITS = 104


def _reference_command() -> ElectroluxAcCommand:
    """Return a command whose frame exercises every field."""
    return ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=24,
        fan=ElectroluxAcFanSpeed.AUTO,
        swing=True,
    )


def _timings_of(frame: bytes) -> list[int]:
    """Encode an arbitrary frame as raw timings, checksum included as given."""
    timings = [_HEADER_MARK, _HEADER_SPACE]
    for byte in frame:
        for shift in range(7, -1, -1):
            timings += [_BIT_MARK, _ONE_SPACE if byte >> shift & 1 else _ZERO_SPACE]
    return [*timings, _BIT_MARK, _FOOTER_SPACE]


def test_frame_layout() -> None:
    """A frame carries each setting in its documented byte."""
    frame = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=24,
        fan=ElectroluxAcFanSpeed.HIGH,
        swing=True,
    ).get_frame()

    assert len(frame) == 13
    assert frame[0] == 0xC3
    # 24 °C: 24 - 8 = 0b10000, reversed over five bits is 0b00001
    assert frame[1] == 0b00000001
    assert frame[2:4] == b"\x00\x00"
    assert frame[4] == ElectroluxAcFanSpeed.HIGH
    assert frame[5] == 0x00
    assert frame[6] == ElectroluxAcMode.COOL
    assert frame[7:9] == b"\x00\x00"
    assert frame[9] == 0b00000100
    assert frame[10:12] == b"\x00\x00"


def test_power_off_frame() -> None:
    """Powering off clears the power bit, disables swing and sends the auto mode."""
    frame = ElectroluxAcCommand(
        mode=ElectroluxAcMode.AUTO,
        temperature=24,
        fan=ElectroluxAcFanSpeed.AUTO,
        swing=False,
        power=False,
    ).get_frame()

    assert frame[1] >> 5 == 0b111
    assert frame[6] == ElectroluxAcMode.AUTO
    assert frame[9] == 0x00


@pytest.mark.parametrize(
    ("temperature", "expected_temp_bits"),
    [
        pytest.param(16, 0b00010, id="16C"),
        pytest.param(17, 0b10010, id="17C"),
        pytest.param(24, 0b00001, id="24C"),
        pytest.param(32, 0b00011, id="32C"),
    ],
)
def test_temperature_encoding(temperature: int, expected_temp_bits: int) -> None:
    """The temperature is encoded as temp - 8 with its five bits reversed."""
    frame = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=temperature,
        fan=ElectroluxAcFanSpeed.AUTO,
    ).get_frame()

    assert frame[1] & 0b11111 == expected_temp_bits


@pytest.mark.parametrize(
    "swing",
    [pytest.param(True, id="vertical"), pytest.param(False, id="off")],
)
def test_swing_encoding(swing: bool) -> None:
    """Vertical swing clears the swing bits, swing off sets all three."""
    frame = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=24,
        fan=ElectroluxAcFanSpeed.AUTO,
        swing=swing,
    ).get_frame()

    assert frame[1] >> 5 == (0b000 if swing else 0b111)


def test_checksum() -> None:
    """The checksum is the bit reversed sum of the bit reversed leading bytes."""
    command = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=24,
        fan=ElectroluxAcFanSpeed.HIGH,
        swing=True,
    )
    frame = command.get_frame()

    def reverse(byte: int) -> int:
        return int(f"{byte:08b}"[::-1], 2)

    assert frame[12] == reverse(sum(reverse(byte) for byte in frame[:12]) & 0xFF)


@pytest.mark.parametrize(
    "temperature",
    [
        pytest.param(MIN_TEMP - 1, id="too-cold"),
        pytest.param(MAX_TEMP + 1, id="too-hot"),
    ],
)
def test_temperature_out_of_range(temperature: int) -> None:
    """A temperature the frame cannot express is rejected."""
    with pytest.raises(ValueError, match="out of range"):
        ElectroluxAcCommand(
            mode=ElectroluxAcMode.COOL,
            temperature=temperature,
            fan=ElectroluxAcFanSpeed.AUTO,
        )


def test_raw_timings() -> None:
    """The raw timings frame the 104 payload bits in a header and a footer."""
    command = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=24,
        fan=ElectroluxAcFanSpeed.HIGH,
        swing=True,
    )
    timings = command.get_raw_timings()

    assert command.modulation == 38000
    assert len(timings) == 2 + 2 * _FRAME_BITS + 2
    assert timings[:2] == [_HEADER_MARK, _HEADER_SPACE]
    assert timings[-2:] == [_BIT_MARK, _FOOTER_SPACE]
    assert all(mark == _BIT_MARK for mark in timings[2:-2:2])
    assert set(timings[3:-2:2]) <= {_ONE_SPACE, _ZERO_SPACE}

    # The leading 0xC3 header byte is sent most significant bit first.
    assert timings[3:19:2] == [
        _ONE_SPACE,
        _ONE_SPACE,
        _ZERO_SPACE,
        _ZERO_SPACE,
        _ZERO_SPACE,
        _ZERO_SPACE,
        _ONE_SPACE,
        _ONE_SPACE,
    ]


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            ElectroluxAcCommand(
                mode=ElectroluxAcMode.COOL,
                temperature=21,
                fan=ElectroluxAcFanSpeed.HIGH,
                swing=True,
            ),
            id="cool",
        ),
        pytest.param(
            ElectroluxAcCommand(
                mode=ElectroluxAcMode.HEAT,
                temperature=MAX_TEMP,
                fan=ElectroluxAcFanSpeed.LOW,
            ),
            id="heat",
        ),
        pytest.param(
            ElectroluxAcCommand(
                mode=ElectroluxAcMode.DRY,
                temperature=MIN_TEMP,
                fan=ElectroluxAcFanSpeed.LOW,
            ),
            id="dry",
        ),
        pytest.param(
            ElectroluxAcCommand(
                mode=ElectroluxAcMode.FAN_ONLY,
                temperature=25,
                fan=ElectroluxAcFanSpeed.MEDIUM,
            ),
            id="fan-only",
        ),
        pytest.param(
            ElectroluxAcCommand(
                mode=ElectroluxAcMode.AUTO,
                temperature=24,
                fan=ElectroluxAcFanSpeed.AUTO,
                power=False,
            ),
            id="off",
        ),
    ],
)
def test_roundtrip(command: ElectroluxAcCommand) -> None:
    """Decoding the timings of a command returns an equal command."""
    decoded = ElectroluxAcCommand.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.get_frame() == command.get_frame()
    assert decoded.mode is command.mode
    assert decoded.temperature == command.temperature
    assert decoded.fan is command.fan
    assert decoded.swing == command.swing
    assert decoded.power == command.power


def test_decode_tolerates_receiver_skew() -> None:
    """Timings that are off by less than the tolerance still decode."""
    command = ElectroluxAcCommand(
        mode=ElectroluxAcMode.COOL,
        temperature=20,
        fan=ElectroluxAcFanSpeed.MEDIUM,
        swing=True,
    )
    skewed = [
        timing + (200 if timing > 0 else -200) for timing in command.get_raw_timings()
    ]

    decoded = ElectroluxAcCommand.from_raw_timings(skewed)

    assert decoded is not None
    assert decoded.get_frame() == command.get_frame()


def _valid_timings() -> list[int]:
    return _reference_command().get_raw_timings()


def test_decode_rejects_short_signal() -> None:
    """A signal that is too short to hold a frame is rejected."""
    assert ElectroluxAcCommand.from_raw_timings(_valid_timings()[:-4]) is None


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 2000, id="header-mark"),
        pytest.param(1, -2000, id="header-space"),
        pytest.param(2, 2000, id="bit-mark"),
        pytest.param(3, -1000, id="bit-space"),
        pytest.param(2 + 2 * _FRAME_BITS, 2000, id="trailing-mark"),
    ],
)
def test_decode_rejects_bad_timing(index: int, value: int) -> None:
    """A timing outside the tolerance of what it should be is rejected."""
    timings = _valid_timings()
    timings[index] = value

    assert ElectroluxAcCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    ("byte_index", "value"),
    [
        pytest.param(0, 0xC2, id="header-byte"),
        pytest.param(1, 0b01000001, id="swing-bits"),
        pytest.param(1, 0b00011000, id="temperature-out-of-range"),
        pytest.param(4, 0x07, id="fan-speed"),
        pytest.param(6, 0x05, id="mode"),
        pytest.param(9, 0x02, id="power-bit"),
        pytest.param(2, 0x01, id="reserved-byte"),
    ],
)
def test_decode_rejects_bad_frame(byte_index: int, value: int) -> None:
    """A frame with a field the protocol does not define is rejected."""
    frame = bytearray(_reference_command().get_frame())
    frame[byte_index] = value
    # Without this the checksum check would reject the frame before the field is read.
    frame[-1] = _checksum(bytes(frame))

    assert ElectroluxAcCommand.from_raw_timings(_timings_of(frame)) is None


def test_decode_rejects_bad_checksum() -> None:
    """A frame whose checksum does not match its contents is rejected."""
    frame = bytearray(_reference_command().get_frame())
    frame[-1] ^= 0xFF

    assert ElectroluxAcCommand.from_raw_timings(_timings_of(frame)) is None
