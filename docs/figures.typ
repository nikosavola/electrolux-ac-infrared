// Protocol figures for the README. Regenerate one with, e.g.:
//   typst compile --ignore-system-fonts --input fig=frame docs/figures.typ docs/images/frame.svg
// for each of: carrier, first-byte, frame, byte1.
#import "@preview/cetz:0.4.2"

#let fig = sys.inputs.at("fig", default: "frame")

#set page(width: auto, height: auto, margin: 0.4cm, fill: white)
#set text(font: "DejaVu Sans Mono", size: 11pt, fill: rgb("#1a1a1a"))

#let blue = rgb("#5A7EA8")
#let red = rgb("#c0504d")
#let green = rgb("#4f9a6a")
#let yellow = rgb("#c9a227")
#let purple = rgb("#8064a2")
#let ink = rgb("#1a1a1a")
#let muted = rgb("#8b8b8b")

// Same constants as electrolux_ac.py.
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

#let encode(mode: 0x04, temperature: 24, fan: 0x05, swing: false, power: true) = {
  let f = (0,) * 13
  f.at(0) = 0xC3
  f.at(1) = (if swing { 0b000 } else { 0b111 })
    .bit-lshift(5)
    .bit-or(reverse-bits(temperature - 8, bits: 5))
  f.at(4) = fan
  f.at(6) = mode
  f.at(9) = if power { 0x04 } else { 0 }
  f.at(12) = checksum(f)
  f
}

#let hex(b) = {
  let s = lower(str(b, base: 16))
  if s.len() == 1 { "0" + s } else { s }
}

// Cool, 24 °C, fan auto: the example frame in the README.
#let example = encode()
#assert.eq(example.map(hex).join(" "), "c3 e1 00 00 05 00 04 00 00 04 00 00 54")

#let bit-segs(byte) = (
  range(7, -1, step: -1)
    .map(s => (
      (bit-mark, true),
      (if byte.bit-rshift(s).bit-and(1) == 1 { one-space } else { zero-space }, false),
    ))
    .flatten()
    .chunks(2)
)

#let timings(frame) = (
  ((header-mark, true), (header-space, false))
    + frame.map(bit-segs).flatten().chunks(2)
    + ((bit-mark, true), (footer-space, false))
)

#let train(segs, sx, high: 1.2, color: blue, stroke-width: 1.6pt) = {
  import cetz.draw: *
  let x = 0
  let pts = ((0, 0),)
  for (d, on) in segs {
    let y = if on { high } else { 0 }
    pts.push((x, y))
    x += d * sx
    pts.push((x, y))
  }
  line(..pts, stroke: stroke-width + color, fill: color.transparentize(80%))
}

#let width(segs, sx) = segs.map(s => s.at(0)).sum() * sx

#let span(x0, x1, y, body, size: 10pt, above: false) = {
  import cetz.draw: *
  line((x0, y), (x1, y), mark: (start: ">", end: ">", size: 0.14, fill: ink), stroke: 0.6pt + ink)
  content(((x0 + x1) / 2, if above { y + 0.4 } else { y - 0.45 }), text(size: size, body))
}

#let carrier = cetz.canvas(length: 1cm, {
  import cetz.draw: *
  let segs = ((bit-mark, true), (zero-space, false), (bit-mark, true), (one-space, false))
  let sx = 14.0 / width(segs, 1)
  train(segs, sx)
  let end = width(segs, sx)
  line((0, 0), (end + 0.2, 0), stroke: 0.8pt + ink)
  span(0, (bit-mark + zero-space) * sx, -0.35, [0: 563 + 538 µs])
  span((bit-mark + zero-space) * sx, end, -0.35, [1: 563 + 1690 µs])
  content((end + 0.4, 0.6), anchor: "west", text(fill: muted, [receiver output]))

  // A mark is really a burst of 38 kHz carrier, about 21 cycles of 26.3 µs.
  let y0 = -3.6
  let period = 0.62
  let pts = ((0, y0),)
  for k in range(10) {
    let x = k * period
    pts += ((x, y0), (x, y0 + 1.2), (x + period / 3, y0 + 1.2), (x + period / 3, y0))
  }
  pts.push((10 * period + 0.2, y0))
  line(..pts, stroke: 1.4pt + red)
  let dash = (paint: muted, dash: "dashed", thickness: 0.6pt)
  line((0, 1.25), (0, y0 + 1.3), stroke: dash)
  line((bit-mark * sx, 1.25), (10 * period, y0 + 1.3), stroke: dash)
  span(0, period, y0 - 0.35, [26.3 µs])
  content((10 * period + 0.6, y0 + 0.6), anchor: "west", text(
    fill: muted,
    [LED: 38 kHz bursts, \~21 cycles per mark],
  ))
})

#let first-byte = cetz.canvas(length: 1cm, {
  import cetz.draw: *
  let bits = (1, 1, 0, 0, 0, 0, 1, 1)
  let segs = ((header-mark, true), (header-space, false)) + bit-segs(0xC3)
  let sx = 23.0 / width(segs, 1)
  train(segs, sx, high: 1.6)
  let end = width(segs, sx)
  line((0, 0), (end + 0.3, 0), stroke: 0.8pt + ink)
  let hs = (header-mark + header-space) * sx
  span(0, header-mark * sx, -0.35, [header mark 8950 µs])
  span(header-mark * sx, hs, -0.35, [space 4530 µs])
  span(hs, end, -0.35, [byte 0 = 0xC3, MSB first])
  let bx = hs
  for b in bits {
    let w = (bit-mark + if b == 1 { one-space } else { zero-space }) * sx
    content((bx + w / 2, 2.1), text(size: 13pt, weight: "bold", str(b)))
    bx += w
  }
})

#let field-color = (
  "0": muted,
  "1": red,
  "4": green,
  "6": purple,
  "9": yellow,
  "12": blue,
)

#let strip(frame) = {
  let cells = frame
    .enumerate()
    .map(((i, b)) => {
      let c = field-color.at(str(i), default: none)
      box(
        width: 100%,
        inset: (y: 0.35em),
        fill: if c == none { none } else { c.transparentize(78%) },
        stroke: 0.6pt + if c == none { muted.lighten(40%) } else { c },
        align(center, text(fill: if c == none { muted } else { ink }, hex(b))),
      )
    })
  let idx = range(13).map(i => align(center, text(size: 8pt, fill: muted, str(i))))
  grid(columns: (1fr,) * 13, column-gutter: 3pt, row-gutter: 4pt, ..cells, ..idx)
}

#let frame = block(width: 24.5cm, {
  cetz.canvas(length: 1cm, {
    import cetz.draw: *
    let t = timings(example)
    let sx = 24.0 / width(t, 1)
    train(t, sx, high: 1.0, stroke-width: 0.9pt)
    line((0, 0), (24.2, 0), stroke: 0.6pt + ink)
    let total = width(t, 1)
    span(
      0,
      total * sx,
      1.45,
      [one frame: #calc.round(total / 1000) ms, #t.len() timings],
      above: true,
    )
  })
  v(0.4em)
  strip(example)
  v(0.2em)
  align(center, text(size: 9pt, fill: muted)[
    cool, 24 °C, fan auto #h(1em)
    #box(width: 0.7em, height: 0.7em, fill: red.transparentize(78%), stroke: 0.6pt + red) swing/temp
    #box(width: 0.7em, height: 0.7em, fill: green.transparentize(78%), stroke: 0.6pt + green) fan
    #box(width: 0.7em, height: 0.7em, fill: purple.transparentize(78%), stroke: 0.6pt + purple) mode
    #box(width: 0.7em, height: 0.7em, fill: yellow.transparentize(78%), stroke: 0.6pt + yellow) power
    #box(width: 0.7em, height: 0.7em, fill: blue.transparentize(78%), stroke: 0.6pt + blue) checksum
  ])
})

#let byte1 = {
  let value = example.at(1)
  let bits = range(8).map(i => value.bit-rshift(7 - i).bit-and(1))
  let fields = (([swing off], 3, red), ([temperature], 5, green))
  let cells = ()
  let i = 0
  for (_, w, c) in fields {
    for _ in range(w) {
      cells.push(box(
        width: 1.8em,
        height: 2em,
        fill: c.transparentize(75%),
        stroke: 0.8pt + c,
        align(center + horizon, text(size: 13pt, weight: "bold", str(bits.at(i)))),
      ))
      i += 1
    }
  }
  let labels = fields.map(((label, w, c)) => grid.cell(colspan: w, align(center, text(
    size: 9pt,
    fill: c.darken(20%),
    label,
  ))))
  grid(
    columns: 2,
    column-gutter: 1.5em,
    align: horizon,
    grid(columns: 8, column-gutter: 2pt, row-gutter: 6pt, ..cells, ..labels),
    text(size: 10pt)[
      byte 1 = 0x#upper(hex(value)) \
      swing off #sym.arrow 111 \
      24 °C #sym.arrow 24 - 8 = 16 = 10000 \
      bit-reversed #sym.arrow 00001
    ],
  )
}

#(
  carrier: carrier,
  first-byte: first-byte,
  frame: frame,
  byte1: byte1,
).at(fig)
