# FRA Operations Forecast — Flightpath

The approved direction is **A / Flightpath**: an F shaped by a continuous path,
with two forward-cut arms. The visual design uses soft white surfaces, graphite
type, a single blue accent and generous space around operational information.

## Start here

- [Visual identity board](identity-board.png)
- [Desktop app design](mockups/app-desktop.png) — editable [SVG](mockups/app-desktop.svg)
- [Mobile app design](mockups/app-mobile.png) — editable [SVG](mockups/app-mobile.svg)
- [Logo and icon files](assets/)
- [CSS design tokens](tokens.css)
- [Usage and handoff guide](guidelines.md)
- [Packaged handoff](fra-flightpath-kit.zip)

These are static design mockups for the teammate implementing the UI. All
displayed values are illustrative. Backend code, JSON contracts and application
routes have not been changed by this design work.

## Assets

| Need | File |
| --- | --- |
| Full name on light surfaces | `assets/fra-logo-horizontal-graphite.svg` |
| Full name on dark surfaces | `assets/fra-logo-horizontal-white.svg` |
| Compact header | `assets/fra-logo-compact-graphite.svg` |
| Standalone wordmark | `assets/fra-wordmark-graphite.svg` |
| Stacked composition | `assets/fra-logo-stacked-graphite.svg` |
| Symbol | `assets/fra-symbol-graphite.svg` or `fra-symbol-blue.svg` |
| Small symbol | `assets/fra-symbol-small.svg` |
| Presentation app icon | `assets/fra-app-icon.svg` |
| Transparent PNG exports | `assets/png/` |
| Browser, home-screen and PWA icons | `assets/web/` |

The finished logo masters use paths, including outlined type. No font install
is needed to display them. SVG mockup labels remain editable text. The demo
board is a presentation, not an additional logo variant.

## Rebuilding

`python3 branding/source/build_identity.py` regenerates the vector masters and
mockups using the saved type outlines. It needs only Python's standard library.
The optional `source/outline_type.swift` records how those outlines were
obtained from macOS CoreText; it is not needed to use or rebuild the kit.

PNG and icon exports were rendered with the logo-design skill's tools using
the installed `rsvg-convert` backend. No external font, icon or image service is
required by the assets.
