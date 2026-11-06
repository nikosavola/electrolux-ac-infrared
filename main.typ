#import "@preview/touying:0.7.4": *
#import "@preview/tiaoma:0.3.0": qrcode
#import "theme/cycler.typ": *
#import "figures.typ"

#set text(lang: "fi")

#show: cycler-theme.with(
  aspect-ratio: "16-9",
  bibliography: bibliography(title: none, "refs.bib"),
  config-info(
    title: [Electrolux-ilmastointilaite \ Home Assistantiin],
    subtitle: [Integraatio laitteelle, jota ohjataan vain infrapunalla],
    short-title: [Electrolux Home Assistantiin],
    author: [Niko Savola],
    date: [Home Assistant Community Day, Helsinki, 7.11.2026],
  ),
)

#title-slide()

#speaker-note[Noin 8 minuuttia ja kysymykset: vajaa minuutti diaa kohden.]

== Ilmastointilaite, jossa on vain kaukosäädin

#slide(composer: (1fr, 0.75fr, 1.35fr))[
  - Ei Wi-Fiä, ei sovellusta
  - Vain *IR-lähetin*

  #v(0.4em)
  #set text(size: 0.8em)
  #callout(color: cycle.green, title: [Raportoitu toimivaksi])[
    EXP26U339HW \
    EXP26U558CW \
    EXP28U340CW \
    EXP34U338HW
  ]
][
  #align(center, image("images/ac.jpg", height: 9cm))
  #align(center, text(
    size: 0.55em,
    fill: cycle.grey,
  )[Electrolux ChillFlex Pro EXP34U338CW. Kuva: Verkkokauppa.com])
][
  #align(center, box(radius: 10pt, clip: true, stroke: 0.6pt + cycle.grey.lighten(40%), image(
    "images/ha-climate.png",
    width: 100%,
  )))
  #align(center, text(size: 0.8em)[Tavoite: `climate`-entiteetti])
]

#speaker-note[Electroluxin siirrettävät ja ikkunamallit. Tavoite: toimintatilat, puhallin, suuntaus ja tavoitelämpötila Home Assistantiin.]

== Home Assistant 2026.4 toi infrapunarakennuspalikan

#figures.chain

#v(1em)

- Mikä tahansa IR-sovitin käy, koska rakennuspalikka antaa sille yhtenevän rajapinnan

#speaker-note[Rakennuspalikka teki projektista pienen. Integraatio puhuu aina samalle rajapinnalle, oli sovitin mikä tahansa.]

== Integraatio matkii kaukosäädintä

// TODO: swap in a photo of the real Electrolux remote; this one is a stand-in.
#align(center, image("images/remote-example.jpg", height: 10cm))
#align(center, text(
  size: 0.55em,
  fill: cycle.grey,
)[Samantyyppinen kaukosäädin, ei Electroluxin. Kuva: Curpharar, CC BY-SA 4.0, Wikimedia Commons])

#speaker-note[Electroluxin oma kaukosäädin on samaa tyyppiä: LCD-näyttö ja napit tilalle, puhaltimelle ja lämpötilalle. Se on ainoa tapa ohjata laitetta. Seuraavaksi katsotaan, mitä se lähettää.]

== Yksi napinpainallus lähettää koko tilan

#align(center, figures.whole-frame(figures.example-frame))

#v(0.6em)

#figures.frame-strip(figures.example-frame)

#v(0.6em)

#align(center, text(size: 0.8em)[
  13 tavua, koko tila joka kerta @explodingkitten2025
])

#speaker-note[Tämä on ainoa dia, jossa koko protokolla näkyy kerralla. Tässä jäähdytys, 24 °C, puhallin automaattisella. Jokainen kehys sisältää kaiken, joten saman kehyksen voi aina lähettää uudelleen. Kehykset ja ajoitukset on tarkistettu omalla enkooderilla, ei vain blogin perusteella.]

== Bitit ovat taukojen pituuksia

#align(center, figures.first-byte)

#v(0.8em)

#align(center, text(size: 0.85em)[
  Pulssi 563 µs, sitten tauko: 538 µs tarkoittaa bittiä `0` ja 1690 µs bittiä `1` @explodingkitten2025
])

#speaker-note[Pitkä aloituspulssi herättää vastaanottimen. Sen jälkeen luetaan bitit taukojen pituudesta: tässä tavu 0, eli 0xC3.]

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
  #callout(color: cycle.green, title: [Loppu on boilerplatea])[
    Asennusikkuna, laitteen entiteetti ja kuvaustiedosto: tekoäly tekee ne hetkessä.
  ]
]

#speaker-note[Tämä on electrolux_ac.py:n koodauspuoli ilman docstringejä, ja vakiot on kirjoitettu auki numeroiksi. Varsinainen työ oli selvittää, miten protokolla toimii, ei kirjoittaa Home Assistant -koodia.]

== Boilerplate on lähinnä täytettäviä kenttiä

#slide(align: top, composer: (1fr, 1fr))[
  #set text(size: 0.78em)
  *Integraation kuvaus* #text(fill: cycle.grey)[`manifest.json`]
  ```json
  {
    "domain": "electrolux_ac_infrared",
    "name": "Electrolux AC Infrared",
    "config_flow": true,
    "dependencies": ["infrared"],
    "integration_type": "device",
    "iot_class": "assumed_state",
    "requirements": [
      "infrared-protocols>=8.2.1"
    ]
  }
  ```
][
  #set text(size: 0.78em)
  *Laitteen ominaisuudet* #text(fill: cycle.grey)[`climate.py`]
  ```python
  class ElectroluxAcClimate(
      InfraredEmitterConsumerEntity,
      ClimateEntity,
      RestoreEntity,
  ):
      _attr_assumed_state = True
      _attr_hvac_modes = [
          HVACMode.OFF, HVACMode.COOL, ...
      ]
      _attr_fan_modes = [FAN_AUTO, FAN_LOW, ...]
      _attr_swing_modes = [SWING_OFF, SWING_VERTICAL]

      async def async_set_hvac_mode(self, hvac_mode):
          await self._async_apply(hvac_mode=hvac_mode)
  ```
]

#speaker-note[Lyhennetty mainista. Kuvaustiedosto kertoo Home Assistantille, mikä integraatio on ja mitä se tarvitsee. Entiteetti luettelee, mitä laite osaa, ja ohjaa jokaisen muutoksen samaan lähetysfunktioon.]

== Entiteetti muistaa, mitä se viimeksi lähetti

#figures.state-flow

#speaker-note[Yksi napinpainallus alusta loppuun. Vastausta ei tule, joten entiteetti muistaa itse, mitä se viimeksi lähetti. Joka muutos lähettää koko tilan. Kuivaus- ja puhallintilan rajoitukset tulevat kaukosäätimestä. Kun laite on pois päältä, tila odottaa seuraavaa käynnistystä.]

== Kokeile

#slide(composer: (1.4fr, 1fr))[
  - Asenna HACSilla suoraan GitHubista
    - tai HA 2026.11:stä lähtien marketplacesta
  - HA 2026.4+ ja mikä tahansa IR-lähetin

  #v(0.4em)
  #text(size: 0.8em, link("https://github.com/nikosavola/electrolux-ac-infrared"))
][
  #align(center + horizon, qrcode(
    "https://github.com/nikosavola/electrolux-ac-infrared",
    width: 6.5cm,
  ))
]

#speaker-note[Käytössä oikealla laitteella localtuya_rc:n kautta. Jos kysytään: vastaanottoa ei vielä ole.]

#focus-slide[Kiitos! \ Kysymyksiä?]
