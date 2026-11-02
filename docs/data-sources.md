# Data sources for forecasting the Frankfurt Airport operating direction

Researched on 30 October 2026. This is a data specification for the FraAlliance hackathon; it does not propose a UI or implement a model. The list covers the most relevant public sources, archives and commercial alternatives found. It cannot be guaranteed to be an exhaustive list of all online services.

## Recommendation for the first version

Use four groups of data:

1. **Actual measurements:** DWD Frankfurt/Main `01420`, including 10-minute wind and gusts; METAR/SPECI `EDDF` as the aerodrome source and cross-check.
2. **Forecast for the next 48 hours:** Open-Meteo/DWD ICON, with ICON-EU or MOSMIX for the part of the horizon that the latest ICON-D2 run does not cover. Bright Sky is the simplest additional route to DWD observations and MOSMIX.
3. **Forecasts as they were actually available in the past:** Open-Meteo Single Runs for testing at 1, 6 and 24 hours. Store the initialisation time and the time the forecast became available.
4. **Actual outcomes:** a record of the 07/25 direction and its changes, and of RWY18 use/status, from DFS/Fraport/UNH or a verified reconstruction from flights. This is the largest open data need.

Downloading the key meteorological data has been confirmed. **A public, documented and complete historical API for the actual operating direction and RWY18 usability has not been confirmed.** A page that displays data is not the same as an available training dataset.

## Identifiers and geographic context

| System | Identifier | Note |
|---|---|---|
| ICAO | `EDDF` | METAR, TAF and aerodrome identification |
| IATA | `FRA` | Commercial flight services |
| DWD CDC | `01420` | Frankfurt/Main; keep the leading zero |
| WMO / MOSMIX / Meteostat | `10637` | Distinguish from the DWD identifier |
| IEM network | `DE__ASOS`, station `EDDF` | Historical METAR/SPECI |
| DWD Kleiner Feldberg/Taunus | `02601` | Optional additional station for incoming northerly wind; not a substitute for the aerodrome |
| DWD Offenbach-Wetterpark | `07341` | Optional spatial context |

In the downloaded DWD catalogue, Frankfurt/Main has coordinates 50.0259, 8.5213 and an elevation of approximately 100 m. AWC returns 50.045, 8.598 and 113 m for EDDF. The test forecast query used the point 50.0333, 8.5706. These are different locations within the wider aerodrome area, so one should not overwrite another. To correct the forecast towards the station, use the station coordinate; add points along the runways later. [DWD catalogue](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/FF_Stundenwerte_Beschreibung_Stationen.txt), [IEM EDDF](https://mesonet.agron.iastate.edu/sites/site.php?network=DE__ASOS&station=EDDF).

## Weather measurements

| Source | Relevant data available | Access and limitations | Recommended role |
|---|---|---|---|
| [DWD CDC: 10-minute wind](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/) | Mean speed `FF_10`, direction `DD_10`, time, station and quality `QN` | ZIP with semicolon-separated text; no key. `historical` for quality-controlled history, `recent` up to the previous day, `now` for the latest data | Primary historical wind; resolution useful for 30-minute persistence |
| [DWD CDC: extreme wind](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/) | Maximum `FX_10`, direction of maximum `DX_10`, additional extremes `FNX_10`, `FMX_10` | Separate dataset; join by station and time | Required for assessing crosswind with gusts |
| [Aviation Weather Center API](https://aviationweather.gov/data/api/) | METAR/SPECI: wind, gusts when reported, direction variability, visibility, clouds, temperature, dew point, pressure, weather phenomena; TAF and SIGMET | JSON and raw text; public API. Documentation currently states up to 30 days of history, with query limits | Current conditions and aerodrome forecast; not a multi-year archive |
| [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/request/download.phtml) | Archive of METAR/SPECI, `drct`, `sknt`, `gust`, temperature, dew point, visibility, clouds and raw METAR | CSV and public HTTP queries; check coverage for the selected period. Include routine and special reports | Simplest archive of aerodrome observations |
| [Bright Sky](https://brightsky.dev/) | DWD observations, MOSMIX forecasts, wind and gust speed and direction, temperature, humidity, pressure, visibility, precipitation and clouds; also warnings and radar | Free JSON with no key. Keep `source_id` and `observation_type` to distinguish measurements from forecasts | Fastest DWD integration; fallback route alongside the direct files |
| [NOAA NCEI Global Hourly / ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | Multi-year measurements of wind, gusts, temperature, pressure, visibility, clouds and other meteorological elements | File downloads and data services; quality flags and special markers for missing values | Fallback historical database and coverage check |
| [Meteostat](https://dev.meteostat.net/api/stations/hourly) | Hourly `wdir`, `wspd`, `wpgt`, `temp`, `dwpt`, `rhum`, `pres`, `prcp`, `coco` and more | JSON via RapidAPI requires a key; Python/CLI and bulk options exist. Check whether data gaps are filled by a model | Quick exploratory retrieval, but direct DWD gives clearer data provenance |
| [CheckWX](https://www.checkwxapi.com/documentation/version2) | Raw and decoded METAR/TAF | API key and the terms of the chosen plan; EDDF was not tested separately in this check | Fallback service, not needed for the MVP |

DWD's 10-minute resolution does not mean the file is published every ten minutes: `now` is refreshed approximately hourly, `recent` daily. Speeds are in m/s. `-999` means a missing value. For data before 2000, respect the historical time reference given in the documentation. [Wind description](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/DESCRIPTION_obsgermany_climate_10min_wind_en.pdf), [gust description](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/DESCRIPTION_obsgermany_climate_10min_extreme_wind_en.pdf).

**Verified DWD links for Frankfurt:**

- [Latest wind, `01420_now.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/10minutenwerte_wind_01420_now.zip): the file's presence in the catalogue is confirmed; its content was not downloaded separately.
- [Recent wind, `01420_akt.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/recent/10minutenwerte_wind_01420_akt.zip): downloaded and read.
- [Recent gusts, `01420_akt.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/recent/10minutenwerte_extrema_wind_01420_akt.zip): downloaded and read.
- [Historical wind](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/historical/): files found for `01420` from 5 March 1993 to the end of 2025; file names do not guarantee that there are no individual gaps.
- [Hourly wind](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/): a simpler alternative, but loses short-lived changes.

## Numerical and aerodrome forecasts

| Source | What we get | Access and limitations | Recommendation |
|---|---|---|---|
| [Open-Meteo DWD ICON](https://open-meteo.com/en/docs/dwd-api) | Wind and gusts at 10 m, wind at higher levels, temperature, pressure, precipitation, clouds, visibility and more | JSON. ICON-D2 about 2 km, approximately 2 days, new runs every 3 hours; 15-minute data exist for some variables | Primary forecast for the MVP |
| [DWD ICON-D2 directly](https://opendata.dwd.de/weather/nwp/icon-d2/grib/) | Original model fields, including wind components; more points and heights | GRIB2, model runs; requires spatial processing. The open catalogue is not a promise of a complete multi-year archive | If full control of the data is needed; more work than JSON |
| [DWD MOSMIX Frankfurt/M](https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/10637/kml/) | Point forecast: `FF`, `DD`, `FX1`, `TTT`, `Td`, `PPPP`, `VV`, precipitation, clouds and event probabilities | KMZ/KML; MOSMIX_L is issued 4 times a day, documented horizon about 10 days. Also available through Bright Sky | Good additional model and horizon extension |
| [TAF for EDDF](https://aviationweather.gov/api/data/taf?ids=EDDF&format=json) | Forecast of wind, gusts, visibility, clouds, phenomena and `BECMG`/`TEMPO`/`PROB` groups when present | Read `issueTime` and the validity interval. The amended TAF that was checked covered 28 h; it does not necessarily cover 48 h | Independent aerodrome comparison and context |
| [Open-Meteo Ensemble](https://open-meteo.com/en/docs/ensemble-api) | Multiple forecast members for estimating spread and the probability of exceeding thresholds | ICON EPS, ECMWF, GFS and others available. The archive of individual members in this API is limited to 3 days | Add once the basic pipeline works; start saving our own copies immediately |

**For the full t+48 h, do not rely on ICON-D2 alone.** Its horizon is counted from initialisation, and by the time of download part of that time has already passed. For the end of the horizon, use ICON-EU/ICON seamless or MOSMIX and label which model provides each record. A forecast from a second service is not independent if both services relay the same DWD model.

Interpret MOSMIX parameters and their time intervals according to the [DWD parameter table](https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_parameteruebersicht.pdf?__blob=publicationFile&v=4) and the [KML format description](https://www.dwd.de/EN/ourservices/met_application_mosmix/mosmix_kml_format_description.pdf?__blob=publicationFile&v=4). Do not assume that units in the original KML are the same as Bright Sky's JSON units.

## Historical forecasts for valid testing

| Source | What it is good for | Key limitation |
|---|---|---|
| [Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api) | Full output of an individual run, selected with the UTC parameter `run` | For most models the archive starts on 2 April 2026. Initialisation is not the moment of public availability. Older IFS 9 km history is also labelled as hindcast; for a strict test, check that the specific product existed at the time |
| [Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api) | Comparison of forecasts at fixed daily offsets; most models from 2024, some later | Daily offsets are not directly the complete runs needed for a precise 1 h / 6 h test |
| [Open-Meteo Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api) | Continuous historical series assembled from short forecast segments | Do not automatically treat it as a 24-hour forecast issued the previous day |
| [ECMWF TIGGE](https://ecds.ecmwf.int/datasets/tigge-forecasts) | Long archive of ensemble forecasts from 2006; useful for longer periods | GRIB/MARS/ECDS access, larger volume and complexity; check the time resolution and variables for the chosen model |
| [NOAA Open Data: GFS and other models](https://www.noaa.gov/nodd/datasets) | Alternative archive of original runs in public cloud storage | Coverage and retention vary by dataset; download runs and forecast steps, not just analyses |
| [Copernicus ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) | Climate context, analysis of past weather and research | Reanalysis using later observations; not a forecast that was available to the operator at the time in question |

**Recommended choice:** first test a common period for which both actual operations labels and archived ICON runs exist. A shorter, verifiable period is better than a seemingly excellent multi-year result that uses data from the future. ERA5 and later-corrected observations can serve as an outcome reference, but must not be used as inputs at the historical prediction time without checking their availability.

## Actual operating direction and runway 18

| Source | What is confirmed available | What still needs to be checked / obtained |
|---|---|---|
| [Umwelthaus / UNH](https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/) | Current 07/25 and the time since when it applies; DFS is named as the source of the status. Separately publishes its own forecast in 8-hour intervals | Documented access, right of reuse and archive export. The page mentions a data service on request |
| [Fraport: current direction](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/aktuelles/aktuelle-betriebsrichtung.html) | Official page for the current direction | No public historical API confirmed. First choice for a request to export operational labels, together with DFS/UNH |
| [DFLD Frankfurt](https://www.dfld.de/Mess/StatTag.php?D=20.04.2026&E=D&L=G&R=001&StatNr=137) | Historical pages, direction and noise displays; CSV export of part of the data | The tested CSV contains overflight times and dB(A), **not** a 07/25 series. Do not present it as a ready-made direction dataset. Request a suitable export |
| [Fraport FRA.NoM / interactive maps](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/interaktive-karten.html) | Flight tracks and noise data for visual checking | Bulk access, permitted reuse, historical range and sufficient precision near the runway |
| [OpenSky Network](https://opensky-network.org/data/) | ADS-B positions and track history; public API and a separate historical database | Access to the full history through Trino is not universally open: there are criteria for researchers and licensing for private/commercial users |
| [Flightradar24 API](https://fr24api.flightradar24.com/docs/endpoints/overview), [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/) | Commercial flights, positions, tracks and history depending on product/plan | Price, right of use and coverage near the ground. Not confirmed to provide a ready-made "RWY18 usable" label |
| [City of Frankfurt: monitoring](https://frankfurt.de/fluglaermschutz/monitoring/monitoring-flugbewegungen) | Aggregates and reports on operations | Daily/monthly statistics serve to check distributions, not to label change times precisely |

**What to request from data owners:** `valid_from_utc`, `valid_to_utc`, direction `07/25`, RWY18 status, reason for unavailability, the actual runway of each take-off/landing, the time the information was published, and record quality. For the hackathon, the most valuable item is a timestamped CSV of status changes, including the test days.

**If an export is not available:** flight tracks can be used to estimate the final-approach direction and the departure runway. These are derived labels with their own uncertainty. No departures from RWY18 can mean low traffic, the night regime, choice of another runway, missing reception or an actual prohibition. Do not assign a negative "unusable" label just because there are no flights. Actual use, official status and meteorological usability must be separate fields.

## Additional data that may explain exceptions

| Source | Data | Priority |
|---|---|---|
| [DFS AIS portal and AIP](https://www.dfs.de/homepage/de/services/allgemeine-luftfahrt/) | Aerodrome procedures, AIP, operational notices and briefing; request NOTAMs on works/closures through an authorised service | Useful for distinguishing weather-based from actual availability. No public automated API confirmed |
| [OurAirports open data](https://ourairports.com/data/) | Coordinates of the aerodrome and runway ends, designators, dimensions, headings and static status | Quick metadata source. The closure field is not a live NOTAM nor proof of current availability |
| [DWD CAP](https://opendata.dwd.de/weather/alerts/cap/) and [AWC SIGMET](https://aviationweather.gov/data/api/) | Meteorological warnings, area, type of phenomenon and validity interval | P1, risk context |
| [DWD radar](https://opendata.dwd.de/weather/radar/) | Precipitation and convective structures, radar products | P2, only if short-term storm changes are needed |
| Nearby DWD stations and forecast wind at 80/120/180 m or 925 hPa | Arrival of a wind change, difference between surface and upper-level flow | P1 for model improvement; do not compare upper-level wind directly with the surface threshold |

## Specific verified queries

These are GET queries without keys. Dates in the archive examples are deliberately fixed; adjust them to the desired period.

- [METAR EDDF, previous 2 hours](https://aviationweather.gov/api/data/metar?ids=EDDF&format=json&hours=2).
- [TAF EDDF](https://aviationweather.gov/api/data/taf?ids=EDDF&format=json).
- [ICON seamless, 49 hourly points and wind in knots](https://api.open-meteo.com/v1/forecast?latitude=50.0333&longitude=8.5706&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&models=icon_seamless&wind_speed_unit=kn&timezone=UTC&forecast_hours=49).
- [Archived ICON-D2 run of 20 October 2026 at 00 UTC](https://single-runs-api.open-meteo.com/v1/forecast?latitude=50.0333&longitude=8.5706&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&models=icon_d2&wind_speed_unit=kn&timezone=UTC&run=2026-10-20T00:00&forecast_days=2).
- [Bright Sky, current measurements for station 01420](https://api.brightsky.dev/current_weather?dwd_station_id=01420).
- [Bright Sky, historical measurements](https://api.brightsky.dev/weather?dwd_station_id=01420&date=2026-10-20&last_date=2026-10-21).
- [MOSMIX_L, latest run for 10637](https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/10637/kml/MOSMIX_L_LATEST_10637.kmz).
- [IEM CSV for EDDF, 20 October 2026](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=EDDF&data=drct&data=sknt&data=gust&data=metar&year1=2026&month1=10&day1=20&year2=2026&month2=10&day2=21&tz=Etc%2FUTC&format=onlycomma&latlon=no&elev=no&missing=M&trace=T&direct=no&report_type=3&report_type=4).

These 49 forecast points include the current rounded hour. The application must explicitly select 48 future hourly targets from its issue time. `forecast_days=2` means two calendar days in the requested run, not automatically every requested future moment up to t+48.

## What was actually verified

The probes were run on 30 October 2026, approximately 11:33–11:36 Europe/Berlin time. The sample confirms availability on that day; it is not a measurement of SLA or of the completeness of the entire archive.

| Check | Result |
|---|---|
| AWC METAR | HTTP 200, four EDDF reports in the requested two hours |
| AWC TAF | HTTP 200, one forecast report with detailed intervals |
| Open-Meteo forecast | HTTP 200, 49 values for speed, direction and gusts |
| Open-Meteo Single Runs | HTTP 200, 48 hourly speed/direction values, 47 gusts; one missing gust |
| IEM history | HTTP 200, 48 reports for 20 October 2026 |
| DWD wind and gusts | Both ZIPs read; each with 79,200 rows from 28 April 2025 to 29 October 2026 |
| DWD historical catalogue | Four archive parts found for 01420, starting 5 March 1993 |
| Bright Sky history | HTTP 200, 25 hourly records in the requested inclusive interval; station 01420 confirmed |
| Bright Sky current | HTTP 200; the actual observation time is older than the download time and must be displayed |
| MOSMIX | HTTP 200, station FRANKFURT/M, 09 UTC run; FF, DD, FX1 and other parameters found |
| DFLD CSV | HTTP 200, but the content is overflight times and noise, with no 07/25 label |

A summary of the automated checks is in `source-checks.json`. A row count does not mean that all values are valid: missing values must be counted and the quality of each field checked.

## Cost, usage rights and order of work

DWD CDC permits use with attribution under the [CC BY 4.0 terms](https://opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.pdf). Bright Sky relays DWD data and its terms. The [Open-Meteo free API](https://open-meteo.com/en/pricing) is intended for non-commercial work, evaluation and prototypes; paid access is intended for commercial applications. A public display by Fraport, UNH or DFLD does not in itself confirm permission for bulk download or redistribution.

Proposed order:

1. Resolve the actual operations labels and their historical range.
2. Load DWD wind/gusts and IEM METAR for the same range.
3. Join the ICON forecast runs that were actually available; store raw responses and the time of receipt.
4. Build a physical baseline according to the challenge rules, then compare the model with it and with the assumption that the current direction persists.
5. Add MOSMIX, ensembles, upper-level wind and nearby stations only if they bring measurable improvement.

**Rule discrepancy to be recorded:** the challenge PDF uses 10 kt for landing, while [Fraport's public explanation](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/laerm-und-luft/flugbetrieb/betriebsrichtung.html) mentions a change at approximately 5 kt tailwind component and consideration of upper-level wind. For the baseline, keep the hackathon rules; take actual labels from observed operations. Version the thresholds; do not replace them silently.
