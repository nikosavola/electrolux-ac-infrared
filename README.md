# Electrolux AC Infrared

Home Assistant custom integration for Electrolux air conditioners that are controlled
with an infrared remote. It builds on the
[Infrared building block integration](https://www.home-assistant.io/integrations/infrared/)
added in Home Assistant 2026.4, so any IR transmitter Home Assistant already exposes as
an infrared emitter — an ESPHome node with an IR LED, a SMLIGHT SLZB adapter, a
Broadlink blaster — can drive the air conditioner.

The integration only encodes the Electrolux IR protocol. It does not talk to any
hardware itself.

## Requirements

- Home Assistant 2026.4 or newer
- At least one `infrared` emitter entity, provided by an adapter integration such as
  ESPHome
- Optionally an `infrared` receiver entity, so Home Assistant follows along when the
  physical remote is used

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nikosavola&repository=electrolux-ac-infrared&category=integration)

1. Add this repository to HACS as a custom repository of type *Integration* (the
   badge above does this for you), then download **Electrolux AC Infrared** from HACS.
1. Restart Home Assistant.

### Manual

Copy `custom_components/electrolux_ac_infrared` into your Home Assistant `config/custom_components`
directory and restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration** and pick **Electrolux AC Infrared**.
Select the infrared transmitter that is pointed at the air conditioner, and optionally an
infrared receiver.

One transmitter drives one air conditioner. Add another entry, with its own transmitter,
for a second unit. The transmitter and receiver can be changed later through
**Reconfigure** on the integration entry.

## Supported functionality

A single `climate` entity is created per air conditioner:

| Feature            | Values                                           |
| ------------------ | ------------------------------------------------ |
| HVAC modes         | off, heat/cool (auto), cool, heat, dry, fan only |
| Target temperature | 16–32 °C in 1 °C steps                           |
| Fan modes          | auto, low, medium, high                          |
| Swing modes        | off, vertical                                    |

Two quirks of the unit are mirrored by the entity, matching what the physical remote
does:

- In dry mode the fan always runs at low.
- Fan-only mode has no auto fan speed; requesting it selects low.

## Known limitations

Infrared is one-way, so the entity is an *assumed state*: it shows what was last sent,
not what the unit is actually doing. If someone uses the physical remote, or the AC is
power cycled, Home Assistant can drift out of sync. The state is restored across
restarts.

Configuring an infrared receiver reduces the drift: frames from the physical remote are
decoded and applied to the entity. The receive path is implemented from the same
protocol description as the transmit path but has not been verified against a physical
remote and a real receiver — a frame that does not decode is ignored, so a mismatch here
cannot break sending.

The air conditioner's own temperature sensor is not readable over infrared, so the
entity reports no current temperature. Pair it with a separate temperature sensor if you
need one.

Changing the fan speed, swing or target temperature while the unit is off stores the
setting for the next power-on instead of transmitting — the air conditioner cannot act
on it while it is off, and firing the transmitter would only resend a power-off frame.

If a restart happens while the unit is off, `climate.turn_on` falls back to cool rather
than the mode it last ran in, since only the off state is restored.

When a receiver is configured, the entity is marked unavailable if *either* the
transmitter or the receiver goes unavailable, even though it could still transmit. This
comes from the shared infrared helper in Home Assistant core rather than this
integration.

## Supported devices

The protocol is shared across the Electrolux portable/window AC range. It has been
reported working on:

- EXP26U339HW
- EXP26U558CW
- EXP28U340CW
- EXP34U338HW

Other Electrolux units using the same remote are likely to work.

## Protocol

Every transmission is a complete 13-byte state frame at 38 kHz:

| Byte   | Contents                                                          |
| ------ | ----------------------------------------------------------------- |
| 0      | `0xC3` constant header                                            |
| 1      | bits 7-5 swing, bits 4-0 temperature (`temp_c - 8`, bit reversed) |
| 4      | fan speed                                                         |
| 6      | operating mode                                                    |
| 9      | bit 2 power                                                       |
| 12     | checksum: bit reversed sum of the bit reversed leading 12 bytes   |
| others | zero                                                              |

Timings are an 8950 µs / 4530 µs header, a 563 µs mark per bit followed by a 1690 µs
space for a one or a 538 µs space for a zero, and a 563 µs / 10000 µs footer.

The encoder lives in
[`electrolux_ac.py`](custom_components/electrolux_ac_infrared/electrolux_ac.py) and
implements the `infrared_protocols.commands.Command` interface, so it could move into
[infrared-protocols](https://github.com/home-assistant-libs/infrared-protocols) if the
protocol is ever added there.

## Versioning

Version numbers follow [ZeroVer](https://0ver.org/): the major version stays at 0
indefinitely, so a 0.y bump can carry breaking changes. See the
[releases](https://github.com/nikosavola/electrolux-ac-infrared/releases) for what
changed between versions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations. Found a security
issue? See [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Credits

The protocol implemented here comes from
[the IR remote write-up on exploding-kitten.com](https://exploding-kitten.com/2025/05-diy-ir-remote)
and the [`esphome-electrolux-ac`](https://github.com/sys27/esphome-electrolux-ac)
ESPHome component by [@sys27](https://github.com/sys27), including the device quirks
above. This integration is licensed GPL-3.0 to match that component.
