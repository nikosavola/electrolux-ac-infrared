![Electrolux AC Infrared](custom_components/electrolux_ac_infrared/brand/logo.svg)

[![Test](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/test.yml/badge.svg)](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/test.yml)
[![Validate](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/validate.yml/badge.svg)](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/validate.yml)
[![codecov](https://codecov.io/gh/nikosavola/electrolux-ac-infrared/graph/badge.svg)](https://codecov.io/gh/nikosavola/electrolux-ac-infrared)
[![License: GPL v3](https://img.shields.io/github/license/nikosavola/electrolux-ac-infrared)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/nikosavola/electrolux-ac-infrared)](https://github.com/nikosavola/electrolux-ac-infrared/releases)

______________________________________________________________________

Home Assistant custom integration for Electrolux air conditioners that are controlled
with an infrared remote. It builds on the
[Infrared building block integration](https://www.home-assistant.io/integrations/infrared/)
added in Home Assistant 2026.4, so any IR transmitter Home Assistant already exposes as
an infrared emitter — an ESPHome node with an IR LED, a SMLIGHT SLZB adapter, a
Broadlink blaster — can drive the air conditioner.

The integration only encodes the Electrolux IR protocol. It does not talk to any
hardware itself.

## How it fits together

This integration is one link in a chain. Home Assistant's `infrared` building block is
the interface between it and whatever hardware actually emits (and optionally receives)
infrared, which is provided by a separate adapter integration:

```mermaid
flowchart LR
    user(["Automations & dashboards"]) --> climate["Electrolux AC Infrared<br>climate entity"]
    climate <--> infrared{{"infrared building block<br>Home Assistant core, 2026.4+"}}
    infrared <--> adapter["Adapter integration<br>ESPHome / SMLIGHT SLZB / Broadlink / LocalTuya / ..."]
    adapter <--> hw[["IR transmitter / receiver<br>hardware"]]
    hw -. "IR light" .-> ac(["Electrolux air conditioner"])
    ac -. "physical remote (optional receive path)" .-> hw

    classDef highlight fill:#5A7EA8,stroke:#022D60,color:#ffffff;
    class climate highlight;
```

This integration only ever produces or parses IR frames — the "Adapter integration" box is
whichever one matches your actual IR hardware, picked when you set up *that* integration,
independently of this one. See the
[full list of `infrared` adapters](https://www.home-assistant.io/integrations/#infrared) for
what's available.

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

- **Assumed state.** Infrared is one-way, so the entity shows what was last sent, not
  what the unit is actually doing. If someone uses the physical remote, or the AC is
  power cycled, Home Assistant can drift out of sync. The state is restored across
  restarts.
- **Receive path is unverified against real hardware.** Configuring an infrared receiver
  reduces drift from the point above: frames from the physical remote are decoded and
  applied to the entity. It's implemented from the same protocol description as the
  transmit path, but hasn't been checked against a physical remote and a real receiver —
  a frame that fails to decode is just ignored, so a mismatch here can't break sending.
- **No temperature readback.** The air conditioner's own temperature sensor isn't
  readable over infrared, so the entity reports no current temperature. Pair it with a
  separate temperature sensor if you need one.
- **Off means stored, not sent.** Changing the fan speed, swing or target temperature
  while the unit is off stores the setting for the next power-on instead of
  transmitting — the air conditioner can't act on it while off, and firing the
  transmitter would only resend a power-off frame.
- **Restart-while-off loses the last mode.** If a restart happens while the unit is off,
  `climate.turn_on` falls back to cool rather than the mode it last ran in, since only
  the off state is restored.
- **Availability follows both entities.** When a receiver is configured, the entity is
  marked unavailable if *either* the transmitter or the receiver goes unavailable, even
  though it could still transmit. This comes from the shared infrared helper in Home
  Assistant core, not this integration.

## Supported devices

The protocol is shared across the Electrolux portable/window AC range. It has been
reported working on:

- EXP26U339HW
- EXP26U558CW
- EXP28U340CW
- EXP34U338HW

Other Electrolux units using the same remote are likely to work.

## Protocol

Every transmission is a single, complete 13-byte state frame sent once at a 38 kHz
carrier — there's no separate repeat or toggle bit, so re-sending the same frame is
always safe.

### Frame layout

| Byte(s)   | Field                                                             |
| --------- | ----------------------------------------------------------------- |
| `0`       | `0xC3` constant header                                            |
| `1`       | bits 7-5 swing, bits 4-0 temperature (`temp_c - 8`, bit-reversed) |
| `2`-`3`   | reserved, `0x00`                                                  |
| `4`       | fan speed                                                         |
| `5`       | reserved, `0x00`                                                  |
| `6`       | operating mode                                                    |
| `7`-`8`   | reserved, `0x00`                                                  |
| `9`       | bit 2 power                                                       |
| `10`-`11` | reserved, `0x00`                                                  |
| `12`      | checksum: bit-reversed sum of the bit-reversed leading 12 bytes   |

For example, cool mode, 24 °C, fan auto, power on encodes to:

```text
c3 e1 00 00 05 00 04 00 00 04 00 00 54
```

### Timings

| Segment              | Duration |
| -------------------- | -------- |
| Header mark          | 8950 µs  |
| Header space         | 4530 µs  |
| Bit mark (every bit) | 563 µs   |
| Space for a `1` bit  | 1690 µs  |
| Space for a `0` bit  | 538 µs   |
| Footer mark          | 563 µs   |
| Footer space         | 10000 µs |

Each of the 104 data bits is sent as a fixed-length mark followed by one of two
space lengths, so the bit value lives entirely in the space that follows it.

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
