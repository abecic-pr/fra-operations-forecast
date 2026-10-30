# Frankfurt Airport map data

`frankfurt-airport.geojson` contains real OpenStreetMap geometry, retrieved through the OSM API. It is a static cartographic extract, not a feed of operating conditions.

- Source: [OpenStreetMap](https://www.openstreetmap.org/#map=14/50.033/8.555).
- Attribution: © OpenStreetMap contributors.
- Database license: [Open Database License 1.0](https://www.openstreetmap.org/copyright).
- Each feature includes its original OSM element link in `properties.osmUrl`.
- Extraction time is recorded in the GeoJSON `retrievedAt` field.
- Contents: the EDDF aerodrome outer boundary, four runway centerlines (`07L/25R`, `07C/25C`, `07R/25L`, `18`), and mapped terminal outlines in the requested airport area. The boundary extract omits inner rings.

The layer uses mapped geometry, rather than manually approximated runway coordinates. No runway availability is inferred from these shapes.

## Refresh intentionally

Run `python3 scripts/refresh-airport.py` from the repository root. This makes four bounded OSM map API requests and retrieves the EDDF airport boundary relation. It validates the four expected runway references before replacing the bundled file. Do not run repeatedly or on every page load. Ordinary app users load this bundled GeoJSON and do not query the OSM data API.

The map uses Leaflet with [Esri World Imagery](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer) as its default background. Service metadata checked during integration credits Esri, Vantor, Earthstar Geographics and the GIS User Community. This background is separate from the OpenStreetMap overlays and has its own provider terms. Source credits remain visible on the map.

The optional street map uses standard [OpenStreetMap tiles](https://operations.osmfoundation.org/policies/tiles/), with visible attribution, normal browser caching and no bulk prefetching. Before wider production use, select a tile provider appropriate for the expected traffic. Geographic overlay data is ODbL licensed independently of the app code and satellite imagery.
