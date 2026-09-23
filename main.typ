#import "@preview/touying:0.7.4": *
#import "@preview/tiaoma:0.3.0": qrcode
#import "theme/cycler.typ": *
#import "figures.typ"

#set text(lang: "fi")

#show: cycler-theme.with(
  aspect-ratio: "16-9",
  bibliography: bibliography(title: none, "refs.bib"),
  config-info(
    title: [Home Assistant oppii puhumaan Electroluxia],
    subtitle: [Oma integraatio ilmastointilaitteelle, jota ohjataan vain infrapunalla],
    short-title: [Electroluxia infrapunalla],
    author: [Niko Savola],
    institution: [Home Assistant Community Day, Helsinki],
    date: none,
  ),
)

#title-slide()

#speaker-note[Noin 8 minuuttia ja kysymykset: vajaa minuutti diaa kohden.]

== Ilmastointilaite, jossa on vain kaukosäädin

#slide(composer: (1.2fr, 1fr))[
  - Ei Wi-Fiä, ei sovellusta
  - Vain *IR-kaukosäädin*
  - Tavoite: `climate`-entiteetti
][
  #callout(color: cycle.green, title: [Raportoitu toimivaksi])[
    EXP26U339HW \
    EXP26U558CW \
    EXP28U340CW \
    EXP34U338HW
  ]
]

#speaker-note[Electroluxin siirrettävät ja ikkunamallit. Tavoite: tilat, puhallin, suuntaus ja tavoitelämpötila Home Assistantiin.]

== Home Assistant 2026.4 toi infrapunan rakennuspalikan

#figures.chain

#v(1em)

- IR-lähettimet entiteetteinä
- Integraatio ei koske laitteistoon

#speaker-note[Tämä teki projektista pienen. Mikä tahansa sovitin, joka tarjoaa infrapunaentiteetin, käy.]

== Yksi napinpainallus lähettää koko tilan

#align(center, figures.whole-frame(figures.example-frame))

#v(0.6em)

#figures.frame-strip(figures.example-frame)

#v(0.6em)

#align(center, text(size: 0.8em)[
  13 tavua, koko tila joka kerta @explodingkitten2025
])

#speaker-note[Ainoa protokolladia. Tässä jäähdytys, 24 °C, puhallin automaattisella. Jokainen kehys sisältää kaiken, joten saman kehyksen voi aina lähettää uudelleen.]

== Bitit ovat taukojen pituuksia

#align(center, figures.first-byte)

#v(0.8em)

#align(center, text(size: 0.85em)[
  Pulssi 563 µs + tauko: 538 µs = `0`, 1690 µs = `1` @explodingkitten2025
])

#speaker-note[Pitkä aloituspulssi herättää vastaanottimen. Sen jälkeen luetaan bitit taukojen pituudesta: tässä tavu 0, eli 0xC3.]

== Oman integraation rakenne

#slide(composer: (1.7fr, 1fr))[
  #set text(size: 1.1em)
  ```text
  custom_components/electrolux_ac_infrared/
  ├── __init__.py       käynnistys
  ├── manifest.json     metatiedot
  ├── config_flow.py    lähettimen valinta
  ├── climate.py        entiteetti
  ├── electrolux_ac.py  protokolla
  ├── strings.json      tekstit
  └── brand/            kuvakkeet
  tests/                pytest
  pyproject.toml        työkalut
  hacs.json             HACS
  ```
][
  - \~700 riviä Pythonia
  - `hassfest` validoi
]

== Kolme kerrosta, jokaisella yksi tehtävä

#figures.layers

#v(1em)

- Riippuvuudet vain alaspäin
- Protokolla siirrettävissä `infrared-protocols`-kirjastoon

#speaker-note[Tämä jako on koko suunnitelma. Kaikki Home Assistantiin liittyvä pysyy poissa protokollamoduulista.]

== Protokolla on muutama kymmenen riviä Pythonia

#slide(align: top, composer: (1fr, 1fr))[
  #set text(size: 0.78em)
  ```python
  def _reverse_bits(value, bits=8):
      result = 0
      for _ in range(bits):
          result = (result << 1) | (value & 1)
          value >>= 1
      return result

  def _checksum(frame):
      total = sum(map(_reverse_bits, frame[:12])) & 0xFF
      return _reverse_bits(total)

  def get_raw_timings(self):
      timings = [8950, -4530]
      for byte in self.get_frame():
          for shift in range(7, -1, -1):
              bit = byte >> shift & 1
              timings += [563, -(1690 if bit else 538)]
      return timings + [563, -10000]
  ```
][
  #set text(size: 0.78em)
  ```python
  def get_frame(self):
      frame = bytearray(13)
      frame[0] = 0xC3
      swing = 0b000 if self.swing else 0b111
      frame[1] = swing << 5 | _reverse_bits(
          self.temperature - 8, 5
      )
      frame[4] = self.fan
      frame[6] = self.mode
      frame[9] = 0x04 if self.power else 0
      frame[12] = _checksum(frame)
      return bytes(frame)
  ```
  #v(0.3em)
  #set text(size: 1.05em)
  #callout(color: cycle.green, title: [Loppu on pohjakoodia])[
    Config flow, entiteetti, manifesti: avoin tekoälymalli tekee ne lounastauolla.
  ]
]

#speaker-note[Tämä on electrolux_ac.py:n koodauspuoli ilman docstringejä, ja vakiot on kirjoitettu auki numeroiksi. Varsinainen työ oli protokollan selvittäminen, ei Home Assistant -koodi.]

== Infrapuna sanelee suunnittelun

#slide(composer: (1fr, 1fr))[
  #callout(color: cycle.blue, title: [Yksisuuntainen yhteys])[
    `assumed_state` + `RestoreEntity`
  ]
  #v(0.4em)
  #callout(color: cycle.green, title: [Koko tila joka kehyksessä])[
    Yksi `_async_apply` kaikille asetuksille
  ]
][
  #callout(color: cycle.purple, title: [Toimi kuin kaukosäädin])[
    Kuivaus: puhallin pienellä \
    Puhallintila: ei automaattia
  ]
  #v(0.4em)
  #callout(color: cycle.red, title: [Sammutettuna vain tallennetaan])[
    Asetukset talteen, ei lähetystä
  ]
]

#speaker-note[Entiteetti näyttää, mitä se viimeksi lähetti. Joka muutos lähettää koko tilan. Kuivaus- ja puhallintilan rajoitukset tulevat kaukosäätimestä. Kun laite on pois päältä, asetukset odottavat seuraavaa käynnistystä.]

== Testattu ilman laitetta

#figures.test-flow

#v(1em)

- Valelähetin rakennuspalikan rajapinnassa
- Oikea `hass` jokaisessa testissä
- Samat tarkistukset paikallisesti ja CI:ssä

#speaker-note[Tätä suosittelisin kaikille, jotka tekevät laitteistointegraatiota: kaikki toimii läppärillä ilman IR-laitteita.]

== Kokeile

#slide(composer: (1.4fr, 1fr))[
  - HACS #sym.arrow mukautettu repositorio
  - HA 2026.4+ ja mikä tahansa IR-lähetin
  - Lähetys testattu, vastaanotto ei vielä
  - Protokolla: Exploding Kitten @explodingkitten2025, sys27 @kyshchenko2025

  #v(0.4em)
  #text(size: 0.8em, link("https://github.com/nikosavola/electrolux-ac-infrared"))
][
  #align(center + horizon, qrcode(
    "https://github.com/nikosavola/electrolux-ac-infrared",
    width: 6.5cm,
  ))
]

#speaker-note[Lähetys on testattu localtuya_rc:n kautta oikealla laitteella, vastaanottoa ei vielä.]

#focus-slide[Pidä protokolla erillään, \ mockaa laitteisto, \ anna *CI:n* hoitaa loput.]

#focus-slide[Kiitos! \ Kysymyksiä?]
