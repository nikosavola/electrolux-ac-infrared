// Figures for the Electrolux IR talk. Frames and timings are computed with a port of the
// integration's encoder, pinned by an assert to what the Python encoder produces.
#import "@preview/cetz:0.4.2"
#import "theme/cycler.typ": cycle

#let header-mark = 8950
#let header-space = 4530
#let bit-mark = 563
#let one-space = 1690
#let zero-space = 538
#let footer-space = 10000

#let reverse-bits(v, bits: 8) = {
  let r = 0
  for _ in range(bits) {
    r = r.bit-lshift(1).bit-or(v.bit-and(1))
    v = v.bit-rshift(1)
  }
  r
}

#let checksum(frame) = reverse-bits(frame.slice(0, 12).map(reverse-bits).sum().bit-and(0xFF))

#let modes = ("auto": 0x00, "heat": 0x01, "dry": 0x02, "fan-only": 0x03, "cool": 0x04)
#let fans = ("medium": 0x02, "high": 0x04, "auto": 0x05, "low": 0x06)

#let encode(mode: "cool", temperature: 24, fan: "auto", swing: false, power: true) = {
  let f = (0,) * 13
  f.at(0) = 0xC3
  let swing-bits = if swing { 0b000 } else { 0b111 }
  f.at(1) = swing-bits.bit-lshift(5).bit-or(reverse-bits(temperature - 8, bits: 5))
  f.at(4) = fans.at(fan)
  f.at(6) = modes.at(mode)
  f.at(9) = if power { 0x04 } else { 0 }
  f.at(12) = checksum(f)
  f
}

#let hex(b) = {
  let s = lower(str(b, base: 16))
  if s.len() == 1 { "0" + s } else { s }
}

#let example-frame = encode()
// Output of ElectroluxAcCommand(mode=COOL, temperature=24, fan=AUTO).get_frame().
#assert.eq(example-frame.map(hex).join(" "), "c3 e1 00 00 05 00 04 00 00 04 00 00 54")

/// Mark/space pairs in microseconds, like get_raw_timings but unsigned.
#let timings(frame) = {
  let t = ((header-mark, true), (header-space, false))
  for byte in frame {
    for shift in range(7, -1, step: -1) {
      t.push((bit-mark, true))
      t.push((if byte.bit-rshift(shift).bit-and(1) == 1 { one-space } else { zero-space }, false))
    }
  }
  t + ((bit-mark, true), (footer-space, false))
}

#let ink = rgb("#1a1a1a")
#let muted = rgb("#8b8b8b")

// A mark/space train as a filled step line starting at x = 0.
#let _train(segs, sx, high: 1.2, color: cycle.blue, stroke-width: 1.6pt) = {
  import cetz.draw: *
  let x = 0
  let pts = ((0, 0),)
  for (d, on) in segs {
    let y = if on { high } else { 0 }
    pts.push((x, y))
    x += d * sx
    pts.push((x, y))
  }
  line(..pts, stroke: stroke-width + color, fill: color.transparentize(82%))
}

#let _span(x0, x1, y, body, size: 13pt, above: false) = {
  import cetz.draw: *
  line((x0, y), (x1, y), mark: (start: ">", end: ">", size: 0.14, fill: ink), stroke: 0.6pt + ink)
  content(((x0 + x1) / 2, if above { y + 0.4 } else { y - 0.45 }), text(
    size: size,
    fill: ink,
    body,
  ))
}

/// Header plus byte 0 (0xC3) to scale, labelled with the timings.
#let first-byte = cetz.canvas(length: 1cm, {
  import cetz.draw: *
  let bits = (1, 1, 0, 0, 0, 0, 1, 1)
  let segs = ((header-mark, true), (header-space, false))
  for b in bits {
    segs.push((bit-mark, true))
    segs.push((if b == 1 { one-space } else { zero-space }, false))
  }
  let sx = 23.0 / segs.map(s => s.at(0)).sum()
  _train(segs, sx, high: 1.6)
  let end = segs.map(s => s.at(0)).sum() * sx
  line((0, 0), (end + 0.3, 0), stroke: 0.8pt + ink)
  let hs = (header-mark + header-space) * sx
  _span(0, header-mark * sx, -0.35, [aloituspulssi 8950 µs])
  _span(header-mark * sx, hs, -0.35, [tauko 4530 µs])
  _span(hs, end, -0.35, [tavu 0 = `0xC3`, eniten merkitsevä bitti ensin])
  let bx = hs
  for b in bits {
    let w = (bit-mark + if b == 1 { one-space } else { zero-space }) * sx
    content((bx + w / 2, 2.1), text(size: 16pt, weight: "bold", fill: ink, str(b)))
    bx += w
  }
})

/// A whole 13-byte frame, to scale, with byte boundaries marked.
#let whole-frame(frame) = cetz.canvas(length: 1cm, {
  import cetz.draw: *
  let t = timings(frame)
  let total = t.map(s => s.at(0)).sum()
  let scale = 24.0 / total
  _train(t, scale, high: 1.0, stroke-width: 0.9pt)
  line((0, 0), (24.2, 0), stroke: 0.6pt + ink)
  let x = (header-mark + header-space) * scale
  let i = 0
  for byte in frame {
    let w = (
      range(8)
        .map(s => (
          bit-mark + if byte.bit-rshift(7 - s).bit-and(1) == 1 { one-space } else { zero-space }
        ))
        .sum()
        * scale
    )
    let c = if byte == 0 { muted } else { ink }
    content((x + w / 2, -0.4), text(size: 11pt, fill: c, raw(hex(byte))))
    x += w
    i += 1
  }
  _span(
    0,
    total * scale,
    1.45,
    [yksi painallus: #calc.round(total / 1000, digits: 0) ms, #(t.len()) ajoitusta],
    size: 12pt,
    above: true,
  )
})

/// The 13 bytes as a strip of cells, colored by field.
#let frame-strip(frame) = {
  let field-color = (
    "0": cycle.grey,
    "1": cycle.red,
    "4": cycle.green,
    "6": cycle.purple,
    "9": cycle.yellow,
    "12": cycle.blue,
  )
  let cells = frame
    .enumerate()
    .map(((i, b)) => {
      let c = field-color.at(str(i), default: none)
      box(
        width: 100%,
        inset: (y: 0.35em),
        fill: if c == none { none } else { c.transparentize(78%) },
        stroke: 0.6pt + if c == none { muted.lighten(40%) } else { c },
        align(center, text(size: 0.8em, fill: if c == none { muted } else { ink }, raw(hex(b)))),
      )
    })
  let idx = range(13).map(i => align(center, text(size: 0.55em, fill: muted, str(i))))
  let key(c, label) = box({
    box(
      width: 0.7em,
      height: 0.7em,
      baseline: 0.05em,
      fill: c.transparentize(78%),
      stroke: 0.6pt + c,
    )
    h(0.3em)
    label
  })
  grid(columns: (1fr,) * 13, column-gutter: 3pt, row-gutter: 4pt, ..cells, ..idx)
  v(0.3em)
  align(center, text(size: 0.6em, fill: muted, (
    key(cycle.grey, [otsake]),
    key(cycle.red, [suuntaus + lämpötila]),
    key(cycle.green, [puhallin]),
    key(cycle.purple, [tila]),
    key(cycle.yellow, [virta: `04` päällä, `00` pois]),
    key(cycle.blue, [tarkistussumma]),
  ).join(h(1.2em))))
}

/// Home Assistant side: who talks to whom.
#let chain = {
  let node(body, hl: false) = box(
    inset: (x: 0.6em, y: 0.5em),
    radius: 3pt,
    fill: if hl { cycle.blue } else { cycle.blue.transparentize(90%) },
    stroke: 0.8pt + cycle.blue,
    text(size: 0.72em, fill: if hl { white } else { ink }, body),
  )
  let arrow = text(fill: muted, sym.arrow.l.r)
  set align(center + horizon)
  grid(
    columns: 9,
    column-gutter: 0.4em,
    node[Kojelaudat, \ automaatiot],
    arrow,
    node(hl: true)[#text(weight: "bold")[Electrolux AC Infrared] \ climate-entiteetti],
    arrow,
    node[`infrared`-rakennuspalikka \ HA core 2026.4+],
    arrow,
    node[Infrapunasovitin \ ESPHome, SLZB, \ Broadlink, LocalTuya],
    text(size: 1.6em, fill: cycle.red, sym.arrow.r.squiggly),
    node[Electrolux-\ ilmastointilaite],
  )
}

#let _layer(title, body, color, note) = grid(
  columns: (1fr, 0.9fr),
  column-gutter: 1em,
  box(
    width: 100%,
    inset: (x: 0.8em, y: 0.55em),
    radius: 3pt,
    fill: color.transparentize(85%),
    stroke: (left: 4pt + color, rest: 0.6pt + color),
    {
      text(weight: "bold", fill: color.darken(20%), title)
      h(0.6em)
      text(size: 0.8em, raw(body))
    },
  ),
  align(horizon, text(size: 0.8em, fill: ink, note)),
)

/// The integration as three layers, each with one job.
#let layers = stack(
  spacing: 0.7em,
  _layer(
    [Config flow],
    "config_flow.py",
    cycle.purple,
    [Lähetin #sym.arrow laite],
  ),
  _layer(
    [Climate-entiteetti],
    "climate.py",
    cycle.blue,
    [Tilat, oikut, oletettu tila],
  ),
  _layer(
    [Protokolla],
    "electrolux_ac.py",
    cycle.green,
    [Tavut ja ajoitukset, ei HA:ta],
  ),
)

/// What a test exercises: a real hass, a fake emitter at the building block boundary.
#let test-flow = {
  let node(body, color) = box(
    inset: (x: 0.6em, y: 0.5em),
    radius: 3pt,
    fill: color.transparentize(85%),
    stroke: 0.8pt + color,
    text(size: 0.75em, body),
  )
  let arrow = text(fill: muted, sym.arrow.r)
  set align(center + horizon)
  grid(
    columns: 7,
    column-gutter: 0.5em,
    node([Toimintokutsu \ `climate.set_hvac_mode`], cycle.grey),
    arrow,
    node([Oikea \ climate-entiteetti], cycle.blue),
    arrow,
    node([Valelähetin \ tallentaa komennon], cycle.green),
    arrow,
    node([Tarkista \ komento], cycle.red),
  )
}

/// One button press, from what the user sees to the emitter, with the IR-driven design notes.
#let state-flow = {
  let step(title, file, body, color, note) = grid(
    columns: (1.25fr, 1fr),
    column-gutter: 1em,
    box(
      width: 100%,
      inset: (x: 0.8em, y: 0.45em),
      radius: 3pt,
      fill: color.transparentize(85%),
      stroke: (left: 4pt + color, rest: 0.6pt + color),
      {
        text(weight: "bold", fill: color.darken(20%), title)
        h(0.5em)
        text(size: 0.7em, fill: muted, raw(file))
        linebreak()
        text(size: 0.75em, body)
      },
    ),
    align(horizon, text(size: 0.7em, fill: ink, note)),
  )
  set text(size: 0.9em)
  let down = pad(left: 1.5em, text(size: 0.8em, fill: muted, sym.arrow.b))
  grid(
    columns: (1fr, 0.36fr),
    column-gutter: 1.2em,
    stack(
      spacing: 0.25em,
      step(
        [climate-entiteetti],
        "climate.py",
        [`hvac_mode`, `target_temperature`, `fan_mode`, `swing_mode`],
        cycle.blue,
        [
          Ei paluukanavaa: `assumed_state` + `RestoreEntity`. Sammutettuna vain tallennetaan.
        ],
      ),
      down,
      step(
        [Komento],
        "electrolux_ac.py",
        [`ElectroluxAcCommand` #sym.arrow.r 13 tavua],
        cycle.green,
        [
          Koko tila joka kehyksessä, joten yksi `_async_apply` kaikille asetuksille
        ],
      ),
      down,
      step([Ajoitukset], "get_raw_timings()", [`[8950, -4530, 563, -1690, ...]` µs], cycle.purple, [
        563 µs pulssi, tauon pituus kertoo bitin
      ]),
      down,
      step([`infrared`], "HA core", [lähettää emitter-entiteetin kautta], cycle.grey, [
        Integraatio ei tiedä, mikä laite lähettää
      ]),
    ),
    align(horizon, stack(
      spacing: 0.5em,
      box(radius: 4pt, clip: true, image("images/ir.jpg", width: 100%)),
      align(center, text(size: 0.7em)[IR-lähetin, esim. Tuya tai ESPHome]),
      align(center, rotate(90deg, text(size: 2em, fill: cycle.red, sym.arrow.r.squiggly))),
      align(center, text(size: 0.7em)[Ilmastointilaite]),
      v(0.4em),
      align(center, text(size: 0.45em, fill: muted)[Kuva: Tuya]),
    )),
  )
}
