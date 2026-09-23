![Electrolux AC Infrared](custom_components/electrolux_ac_infrared/brand/logo.svg)

[![Test](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/test.yml/badge.svg)](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/test.yml)
[![Validate](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/validate.yml/badge.svg)](https://github.com/nikosavola/electrolux-ac-infrared/actions/workflows/validate.yml)
[![codecov](https://codecov.io/gh/nikosavola/electrolux-ac-infrared/graph/badge.svg)](https://codecov.io/gh/nikosavola/electrolux-ac-infrared)
[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=nikosavola_electrolux-ac-infrared&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nikosavola_electrolux-ac-infrared)
[![License: GPL v3](https://img.shields.io/github/license/nikosavola/electrolux-ac-infrared)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/nikosavola/electrolux-ac-infrared)](https://github.com/nikosavola/electrolux-ac-infrared/releases)

______________________________________________________________________

Home Assistant custom integration for Electrolux air conditioners controlled with an infrared
remote. It builds on the
[Infrared building block integration](https://www.home-assistant.io/integrations/infrared/)
added in Home Assistant 2026.4, so any IR transmitter Home Assistant exposes as an
infrared emitter (an ESPHome node with an IR LED, a SMLIGHT SLZB adapter, a Broadlink
blaster) can drive the air conditioner.

The integration only encodes the Electrolux IR protocol; it doesn't talk to hardware
directly.

## How it fits together

This integration is one link in a chain: the `infrared` building block is the interface
to whatever hardware actually emits (and optionally receives) infrared, provided by a
separate adapter integration:

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

This integration only produces or parses IR frames. The "Adapter integration" box is
whichever one matches your IR hardware, set up independently of this one. See the
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

Go to **Settings → Devices & services → Add integration**, pick **Electrolux AC Infrared**,
and select the infrared transmitter pointed at the air conditioner (optionally also a
receiver).

One transmitter drives one air conditioner; add another entry, with its own transmitter,
for a second unit. Change the transmitter or receiver later through **Reconfigure** on
the integration entry.

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

- **Assumed state.** Infrared is one-way, so the entity shows what was last sent, not the
  unit's actual state. Using the physical remote or power-cycling the AC can drift it out
  of sync; state is restored across restarts.
- **Receive path is unverified against real hardware.** An infrared receiver reduces that
  drift: remote frames are decoded and applied to the entity. It's implemented from the
  same protocol description as transmit, but hasn't been checked against real hardware;
  an undecodable frame is just ignored, so it can't break sending.
- **No temperature readback.** The AC's own temperature sensor isn't readable over
  infrared, so the entity reports none. Pair it with a separate sensor if you need one.
- **Off means stored, not sent.** Changing fan speed, swing, or target temperature while
  off stores it for the next power-on instead of transmitting, since the AC can't act on
  it while off and firing the transmitter would just resend a power-off frame.
- **Restart-while-off loses the last mode.** A restart while the unit is off makes
  `climate.turn_on` fall back to cool rather than the last-used mode, since only the off
  state is restored.
- **Availability follows both entities.** With a receiver configured, the entity goes
  unavailable if *either* entity does, even though it could still transmit. That's Home
  Assistant core's shared infrared helper, not this integration.

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
carrier. There's no separate repeat or toggle bit, so re-sending the same frame is
always safe.

![One frame to scale: a long header, then 104 bits, above the 13 frame bytes colored by field](docs/images/frame.svg)

### Frame layout

Bit positions in the order they're sent, 32 per row:

```mermaid
packet
  0-7: "header 0xC3"
  8-10: "swing"
  11-15: "temp - 8 (reversed)"
  16-31: "reserved"
  32-39: "fan"
  40-47: "reserved"
  48-55: "mode"
  56-71: "reserved"
  72-79: "power"
  80-95: "reserved"
  96-103: "checksum"
```

| Byte(s)                          | Field                  | Values                                                             |
| -------------------------------- | ---------------------- | ------------------------------------------------------------------ |
| `0`                              | header                 | always `0xC3`                                                      |
| `1`                              | swing (bits 7-5)       | `111` off, `000` vertical                                          |
|                                  | temperature (bits 4-0) | `temp_c - 8` for 16–32 °C, as five bits, bit-reversed (see below)  |
| `4`                              | fan speed              | `0x02` medium, `0x04` high, `0x05` auto, `0x06` low                |
| `6`                              | operating mode         | `0x00` auto, `0x01` heat, `0x02` dry, `0x03` fan only, `0x04` cool |
| `9`                              | power                  | `0x04` on, `0x00` off                                              |
| `12`                             | checksum               | see below                                                          |
| `2`-`3`, `5`, `7`-`8`, `10`-`11` | reserved               | always `0x00`                                                      |

Within a byte, bits are numbered from the least significant bit, bit 0. Power only uses
bit 2 of byte 9, which is worth `0x04`:

| Byte 9 bit |  7  |  6  |  5  |  4  |  3  |   2   |  1  |  0  | Value  |
| ---------- | :-: | :-: | :-: | :-: | :-: | :---: | :-: | :-: | :----: |
| Power on   |  0  |  0  |  0  |  0  |  0  | **1** |  0  |  0  | `0x04` |
| Power off  |  0  |  0  |  0  |  0  |  0  |   0   |  0  |  0  | `0x00` |

For example, cool mode, 24 °C, fan auto, power on encodes to:

```text
c3 e1 00 00 05 00 04 00 00 04 00 00 54
```

Changing one setting only changes its own byte and the checksum (marked with `^^`):

```diff
- c3 e1 00 00 05 00 04 00 00 04 00 00 54   cool, 24 °C, fan auto, on
+ c3 f1 00 00 05 00 04 00 00 04 00 00 4c   24 -> 25 °C
     ^^                               ^^
- c3 e1 00 00 05 00 04 00 00 04 00 00 54
+ c3 e1 00 00 04 00 04 00 00 04 00 00 55   fan auto -> high
              ^^                      ^^
- c3 e1 00 00 05 00 04 00 00 04 00 00 54
+ c3 e1 00 00 05 00 04 00 00 00 00 00 50   power on -> off
                             ^^       ^^
```

Byte 1 of that frame shows the bit reversal: 24 °C is sent as `24 - 8 = 16`, which is
`10000` in five bits, reversed to `00001`. With swing off (`111`) in front, that gives
`11100001`, or `0xE1`.

![Byte 1 as eight bits: swing off 111, then temperature 00001](docs/images/byte1.svg)

The checksum uses the same trick. Bit-reverse each of bytes 0 to 11, add them up, keep the
low byte, and bit-reverse the result. For the example frame, the non-zero bytes reverse to
`c3 87 a0 20 20`, which sum to `0x22A`. The low byte `0x2A` reversed is `0x54`, the last
byte of the frame.

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

Each of the 104 bits is a fixed-length mark followed by one of two space lengths, which
is what encodes its value. Here's the header and byte 0 (`0xC3`) to scale:

![Header mark and space, then byte 0 as bits 1 1 0 0 0 0 1 1](docs/images/first-byte.svg)

Each mark is itself a burst of the 38 kHz carrier, which the receiver strips off:

![A 0 bit and a 1 bit, zoomed into the 38 kHz carrier inside a mark](docs/images/carrier.svg)

The figures are generated from [`docs/figures.typ`](docs/figures.typ) with [Typst](https://typst.app).

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

## Related projects

- [`tuya-smart-ir-ac`](https://github.com/EnzoD86/tuya-smart-ir-ac): drives IR air
  conditioners (and other IR devices) through a Tuya Smart IR hub over Tuya's own cloud
  API, instead of the `infrared` building block this integration uses. Worth a look if
  your air conditioner isn't Electrolux, or you'd rather not set up a separate adapter
  integration.
- [`localtuya_rc`](https://github.com/ClusterM/localtuya_rc): a local, non-cloud Tuya
  remote-control integration whose `infrared` adapter entity was used to verify this
  integration on real hardware.
- [`ha-electrolux`](https://github.com/TTLucian/ha-electrolux): talks to Electrolux's own
  cloud API instead of infrared. Use this one if your AC connects to the Electrolux app
  directly, rather than shipping with just a remote.

## Credits

The protocol implemented here comes from
[the IR remote write-up on exploding-kitten.com](https://exploding-kitten.com/2025/05-diy-ir-remote)
and the [`esphome-electrolux-ac`](https://github.com/sys27/esphome-electrolux-ac)
ESPHome component by [@sys27](https://github.com/sys27), including the device quirks
above. This integration is licensed GPL-3.0 to match that component.
