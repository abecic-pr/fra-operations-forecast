# Flightpath — usage and UI handoff

## Logo

Use graphite on light backgrounds, white on graphite or blue, and blue when a
small brand accent is useful. Use the provided paths rather than recreating the
wordmark. The white symbol is slightly thinner to balance its apparent weight
on dark backgrounds. A simplified, square-ended cut is supplied for small icons.

Keep one stem width of clear space around the visible artwork: **36 units on
the 256-unit symbol grid**. The SVG canvas includes some of this space. Keep
the original proportions and orientation. Do not add gradients, shadows or
outlines to the logo itself.

| Version | Minimum displayed size |
| --- | --- |
| Small symbol / favicon | 16 × 16 px |
| Standard symbol | 24 × 24 px |
| Compact FRA lockup | 112 px wide |
| Full horizontal lockup | 300 px wide |
| Stacked full-name lockup | 320 px wide |

Below the full-name minimum, use the compact lockup or symbol and place the app
name in accessible UI text. The long descriptor is not intended to be readable
in a 16px favicon. Keep the HTML image's alt text appropriate to context; use
empty alt text when an adjacent visible label already names the app.

## Palette

| Role | HEX | RGB | Use |
| --- | --- | --- | --- |
| Canvas | `#F5F5F7` | 245, 245, 247 | Main background |
| Surface | `#FFFFFF` | 255, 255, 255 | Primary content surfaces |
| Graphite | `#17191D` | 23, 25, 29 | Logo, headings, main text |
| Secondary | `#656B75` | 101, 107, 117 | Supporting text |
| Flight blue | `#0066CC` | 0, 102, 204 | Selection, forecast line, app icon |
| Line | `#DDE1E7` | 221, 225, 231 | Nonessential separators |
| Suitable | `#167247` | 22, 114, 71 | Weather suitability, with a check and label |
| Attention | `#8A5700` | 138, 87, 0 | Uncertain conditions, with an icon and label |
| Unsuitable | `#B4232C` | 180, 35, 44 | Weather rules not satisfied, with a label |

Status backgrounds and remaining tokens are in `tokens.css`. Reserve status
colours for their meaning; blue does not mean a runway is safe or officially
open. Unknown data uses neutral text, an explicit label and a gap or dashed
outline in time series. Never convert a missing value into zero or a green state.

This is an RGB digital kit. The included vector PDF is RGB too. CMYK and spot
colour matches have not been specified or proofed for print.

## Typography and layout

App type stack: `system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue",
Arial, sans-serif`. Use the platform font; no font files are bundled. The logo's
type was outlined from the locally installed Helvetica Neue using CoreText.
The symbol is custom vector geometry. No Apple symbol or SF font file is used.

Use 14–16px body text, 12px captions, 20–24px section headings and 28–36px page
titles. Major runway numerals can reach 64–104px on desktop. Use medium weight
for headings and tabular numerals for values and timestamps. Small chart labels
in these scaled mockups may be enlarged in the implementation.

Desktop: compact 224px navigation rail, 40–56px content margins, a single
overview surface followed by the forecast surface. Mobile: stack the overview
and forecast, use 20–24px margins, move navigation to the bottom and let content
scroll. The mobile illustration shows the entire scrollable content, not one
fixed viewport. Controls need at least 44px touch targets and visible keyboard
focus in the implemented UI.

Use a 4px spacing unit, 20px primary panel radii and 8px controls. Separate
information with space and fine rules. Use labels and line styles as well as
colour. Respect reduced-motion preferences if motion is added.

## Data presentation

- **Observed direction** is a sourced operation record, with its observation
  time. It must never be filled from the weather baseline and labelled observed.
- **Forecast direction** belongs in the future timeline. The example shows a
  potential change window, not a minute-accurate promise.
- **RWY18 weather suitability** and **official runway status** are separate
  rows. “Suitable” never implies “open”. Unknown official status remains visible.
- The blue dashed line is forecast wind in knots; the graphite dot is the
  observation at the start of the displayed horizon. Provide a text legend.
- Keep forecast issue time, observation time and valid time separate. These
  mockups explicitly use UTC. Include the date across midnight and the 48-hour
  horizon. Local-time implementations must display their timezone.
- The mockup values and sample provenance are illustrative. The picture is not
  a weather-rule calculation or validation result. Replace them with the existing
  backend response; keep its field names and rules intact.
- Do not display confidence percentages for a deterministic baseline. Hide
  probability UI or show “Unavailable” until calibrated estimates exist.

## Verification and handoff

The three concepts went through two visual passes. Final symbol geometry was
inspected at 16, 24, 32 and 64px, on light and dark surfaces, mirrored and rotated.
SVG structural audits were run on the final symbol and full lockups. Full-name
lockups are intentionally more complex because they contain outlined text;
their descriptor has a minimum display size. Small usage has separate assets.

Final mockups were rendered and visually inspected, including a correction to
overlapping runway labels. Colour contrast was calculated for the supplied text
and status pairs; results are in `validation.json`. This checks the palette,
not a complete accessibility audit of a working application.

Final logo masters contain no live text, raster images, filters or external
references. PNG transparency and web icon dimensions were checked. No trademark
clearance is claimed. The editable mockups and tokens are ready for the teammate
to implement; no application code integration was performed.
