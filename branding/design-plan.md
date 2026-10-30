# Flightpath visual direction

Chosen by the user: A / Flightpath. 30 October 2026.

## Design plan

The recognisable feature is a quiet runway-direction schematic paired with an
hourly outlook. A compact sidebar creates a familiar desktop-app frame. Keep
the content left aligned; use one large, continuous forecast surface rather
than a grid of equally prominent metrics.

```text
Brand / navigation | Frankfurt outlook                 Demo data
                   | Observed direction     Runway schematic
                   | Next change            RWY18 weather suitability
                   | 48-hour outlook / direction bands / wind chart
                   | Data provenance / status
```

Core palette: Canvas #F5F5F7, Surface #FFFFFF, Graphite #17191D,
Secondary #656B75, Line #DDE1E7, Flight blue #0066CC.

Use system-ui, -apple-system, BlinkMacSystemFont, Helvetica Neue, sans-serif.
It feels native on macOS without distributing or embedding Apple fonts. Font
sizes: 12, 14, 16, 20, 28, 36, 64. Body 14–16px, medium headings, tabular figures.

Spacing uses 4px increments. Main content has 40px margins. Cards use 20px
radii; controls 8px; small status indicators are pills. Surfaces rely on
spacing and fine dividers rather than repeating shadows.

## Review against brief

White surfaces, system typography and blue controls are intentional responses
to the Apple-like brief. The runway diagram and paired 07/25 direction bands
make this specific to the project. No generic analytics percentages, growth
cards or decorative charts. A chart represents wind in knots, and observation
and forecast segments use different line styles plus labels.

## Scope and honesty

Deliver a static, editable visual mockup, logo assets, tokens and a compact
handoff guide. This supports the teammate's UI implementation. All values in
the visual mockup are explicitly illustrative. Official runway status is
unknown; weather suitability is a distinct labelled field. Model probabilities
are absent because the baseline is deterministic.
