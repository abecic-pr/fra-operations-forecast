# Izvori podataka za prognozu operativnog smjera aerodroma Frankfurt

Istraženo 30. 10. 2026. Ovo je podatkovna specifikacija za FraAlliance hackathon; ne predlaže UI niti implementira model. Popis obuhvaća najrelevantnije pronađene javne izvore, arhive i komercijalne alternative. Nije moguće jamčiti iscrpan popis svih internetskih servisa.

## Preporuka za prvu verziju

Koristiti četiri skupine podataka:

1. **Stvarna mjerenja:** DWD Frankfurt/Main `01420`, uključujući desetominutni vjetar i udare; METAR/SPECI `EDDF` kao aerodromski izvor i provjeru.
2. **Prognoza sljedećih 48 sati:** Open-Meteo/DWD ICON, uz ICON-EU ili MOSMIX za dio horizonta koji najnoviji ICON-D2 ne pokriva. Bright Sky je najjednostavniji dodatni pristup DWD opažanjima i MOSMIX-u.
3. **Prognoze kakve su stvarno bile dostupne u prošlosti:** Open-Meteo Single Runs za testiranje na 1, 6 i 24 sata. Pohraniti vrijeme inicijalizacije i vrijeme dostupnosti prognoze.
4. **Stvarni ishodi:** zapis smjera 07/25 i njegovih promjena te korištenja/statusa RWY18 iz DFS/Fraport/UNH ili provjerene rekonstrukcije letova. Ovo je najveća otvorena podatkovna potreba.

Potvrđeno je preuzimanje ključnih meteoroloških podataka. **Nije potvrđen javni, dokumentirani i potpuni povijesni API za stvarni smjer operacija i upotrebljivost RWY18.** Stranica s prikazom podataka nije isto što i dostupan skup podataka za treniranje.

## Identifikatori i geografski kontekst

| Sustav | Identifikator | Napomena |
|---|---|---|
| ICAO | `EDDF` | METAR, TAF i identifikacija aerodroma |
| IATA | `FRA` | Komercijalni servisi letova |
| DWD CDC | `01420` | Frankfurt/Main; zadržati početnu nulu |
| WMO / MOSMIX / Meteostat | `10637` | Razlikovati od DWD identifikatora |
| IEM mreža | `DE__ASOS`, stanica `EDDF` | Povijesni METAR/SPECI |
| DWD Kleiner Feldberg/Taunus | `02601` | Opcionalna dodatna postaja za dolazak sjevernog vjetra; nije zamjena za aerodrom |
| DWD Offenbach-Wetterpark | `07341` | Opcionalan prostorni kontekst |

U preuzetom DWD katalogu Frankfurt/Main ima koordinate 50.0259, 8.5213 i visinu približno 100 m. AWC za EDDF vraća 50.045, 8.598 i 113 m. Za probni upit prognoze korištena je točka 50.0333, 8.5706. To su različite lokacije unutar šireg aerodromskog područja, pa ih ne treba prepisivati jednu preko druge. Za korekciju prognoze prema postaji koristiti koordinatu postaje; kasnije dodati točke uz piste. [DWD katalog](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/FF_Stundenwerte_Beschreibung_Stationen.txt), [IEM EDDF](https://mesonet.agron.iastate.edu/sites/site.php?network=DE__ASOS&station=EDDF).

## Mjerenja vremena

| Izvor | Dostupni relevantni podaci | Pristup i ograničenja | Preporučena uloga |
|---|---|---|---|
| [DWD CDC: desetominutni vjetar](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/) | Srednja brzina `FF_10`, smjer `DD_10`, vrijeme, postaja i kvaliteta `QN` | ZIP s tekstom odvojenim točkom-zarezom; bez ključa. `historical` za kontroliranu povijest, `recent` do prethodnog dana, `now` za najnovije podatke | Primarni povijesni vjetar; razlučivost korisna za 30-minutnu postojanost |
| [DWD CDC: ekstremni vjetar](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/) | Maksimum `FX_10`, smjer maksimuma `DX_10`, dodatni ekstremi `FNX_10`, `FMX_10` | Poseban dataset; povezati po postaji i vremenu | Obavezno za procjenu bočnog vjetra s udarima |
| [Aviation Weather Center API](https://aviationweather.gov/data/api/) | METAR/SPECI: vjetar, udari kad su prijavljeni, promjenjivost smjera, vidljivost, oblaci, temperatura, rosište, tlak, vremenske pojave; TAF i SIGMET | JSON i izvorni tekst; javni API. Dokumentacija trenutačno navodi do 30 dana povijesti, uz ograničenja upita | Aktualno stanje i aerodromska prognoza; nije višegodišnja arhiva |
| [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/request/download.phtml) | Arhiva METAR/SPECI, `drct`, `sknt`, `gust`, temperatura, rosište, vidljivost, oblaci i izvorni METAR | CSV i javni HTTP upiti; provjeriti pokrivenost odabranog razdoblja. Uključiti redovne i posebne izvještaje | Najjednostavnija arhiva aerodromskih opažanja |
| [Bright Sky](https://brightsky.dev/) | DWD opažanja, MOSMIX prognoze, brzina i smjer vjetra i udara, temperatura, vlaga, tlak, vidljivost, oborine i oblaci; dodatno upozorenja i radar | Besplatan JSON bez ključa. Čuvati `source_id` i `observation_type` radi razlikovanja mjerenja i prognoza | Najbrža integracija DWD-a; rezervni put uz izravne datoteke |
| [NOAA NCEI Global Hourly / ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | Višegodišnja mjerenja vjetra, udara, temperature, tlaka, vidljivosti, oblaka i drugih meteoroloških elemenata | Preuzimanje datoteka i podatkovni servisi; zastavice kvalitete i posebne oznake nedostajućih vrijednosti | Rezervna povijesna baza i provjera pokrivenosti |
| [Meteostat](https://dev.meteostat.net/api/stations/hourly) | Satni `wdir`, `wspd`, `wpgt`, `temp`, `dwpt`, `rhum`, `pres`, `prcp`, `coco` i drugo | JSON preko RapidAPI-ja zahtijeva ključ; postoje Python/CLI i bulk mogućnosti. Provjeriti popunjavanje podataka modelom | Brzi istraživački dohvat, ali izravni DWD je jasniji za podrijetlo podataka |
| [CheckWX](https://www.checkwxapi.com/documentation/version2) | Sirovi i dekodirani METAR/TAF | API ključ i uvjeti odabranog plana; EDDF nije zasebno testiran u ovoj provjeri | Rezervni servis, nije potreban za MVP |

Desetominutna razlučivost DWD-a ne znači da se datoteka objavljuje svakih deset minuta: `now` se osvježava približno satno, `recent` dnevno. Brzine su u m/s. `-999` znači nedostajuću vrijednost. Za podatke prije 2000. treba poštovati povijesnu vremensku referencu iz dokumentacije. [Opis vjetra](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/DESCRIPTION_obsgermany_climate_10min_wind_en.pdf), [opis udara](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/DESCRIPTION_obsgermany_climate_10min_extreme_wind_en.pdf).

**Provjereni DWD linkovi za Frankfurt:**

- [Najnoviji vjetar, `01420_now.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/10minutenwerte_wind_01420_now.zip): potvrđena prisutnost datoteke u katalogu; njezin sadržaj nije posebno preuzet.
- [Nedavni vjetar, `01420_akt.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/recent/10minutenwerte_wind_01420_akt.zip): preuzeto i pročitano.
- [Nedavni udari, `01420_akt.zip`](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/extreme_wind/recent/10minutenwerte_extrema_wind_01420_akt.zip): preuzeto i pročitano.
- [Povijesni vjetar](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/historical/): pronađene datoteke za `01420` od 5. 3. 1993. do kraja 2025.; nazivi datoteka ne jamče da nema pojedinačnih praznina.
- [Satni vjetar](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/): jednostavnija alternativa, ali gubi kratke promjene.

## Numeričke i aerodromske prognoze

| Izvor | Što dobivamo | Pristup i ograničenja | Preporuka |
|---|---|---|---|
| [Open-Meteo DWD ICON](https://open-meteo.com/en/docs/dwd-api) | Vjetar i udari na 10 m, vjetar na višim razinama, temperatura, tlak, oborine, oblaci, vidljivost i drugo | JSON. ICON-D2 oko 2 km, približno 2 dana, novi ciklusi svaka 3 sata; za dio varijabli postoje 15-minutni podaci | Primarna prognoza za MVP |
| [DWD ICON-D2 izravno](https://opendata.dwd.de/weather/nwp/icon-d2/grib/) | Izvorna modelska polja, uključujući komponente vjetra; više točaka i visina | GRIB2, ciklusi modela; zahtijeva prostornu obradu. Otvoreni katalog nije obećanje potpune višegodišnje arhive | Ako treba potpuna kontrola podataka; više rada od JSON-a |
| [DWD MOSMIX Frankfurt/M](https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/10637/kml/) | Točkasta prognoza: `FF`, `DD`, `FX1`, `TTT`, `Td`, `PPPP`, `VV`, oborine, oblaci i vjerojatnosti pojava | KMZ/KML; MOSMIX_L izlazi 4 puta dnevno, dokumentiran horizont oko 10 dana. Dostupan i kroz Bright Sky | Dobar dodatni model i dopuna horizonta |
| [TAF za EDDF](https://aviationweather.gov/api/data/taf?ids=EDDF&format=json) | Prognoza vjetra, udara, vidljivosti, oblaka, pojava i grupa `BECMG`/`TEMPO`/`PROB` kada postoje | Čitati `issueTime` i interval valjanosti. Provjereni izmijenjeni TAF trajao je 28 h; ne pokriva nužno 48 h | Neovisna aerodromska usporedba i kontekst |
| [Open-Meteo Ensemble](https://open-meteo.com/en/docs/ensemble-api) | Više prognoznih članova za procjenu raspona i vjerojatnosti prekoračenja pragova | Dostupni ICON EPS, ECMWF, GFS i drugi. Arhiva pojedinačnih članova u ovom API-ju ograničena je na 3 dana | Dodati kad osnovni pipeline radi; početi odmah spremati vlastite kopije |

**Za punih t+48 h ne oslanjati se samo na ICON-D2.** Njegov horizont računa se od inicijalizacije, a do trenutka preuzimanja dio vremena je prošao. Za kraj horizonta koristiti ICON-EU/ICON seamless ili MOSMIX i označiti koji model daje svaki zapis. Prognoza s drugog servisa nije neovisna ako oba servisa prenose isti DWD model.

MOSMIX parametre i njihove vremenske intervale tumačiti prema [DWD tablici parametara](https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_parameteruebersicht.pdf?__blob=publicationFile&v=4) i [opisu KML formata](https://www.dwd.de/EN/ourservices/met_application_mosmix/mosmix_kml_format_description.pdf?__blob=publicationFile&v=4). Jedinice iz izvornog KML-a ne pretpostavljati jednakima JSON jedinicama Bright Skyja.

## Povijesne prognoze za valjano testiranje

| Izvor | Za što je dobar | Ključno ograničenje |
|---|---|---|
| [Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api) | Puni izlaz pojedinačnog ciklusa, odabranog pomoću UTC parametra `run` | Za većinu modela arhiva od 2. 4. 2026. Inicijalizacija nije trenutak javne dostupnosti. Starija IFS 9 km povijest označena je i kao hindcast; za strogi test provjeriti da je konkretan proizvod tada postojao |
| [Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api) | Usporedba prognoza fiksnih dnevnih odmaka; većina modela od 2024., neki kasnije | Dnevni odmaci nisu izravno potpuni ciklusi potrebni za precizan 1 h / 6 h test |
| [Open-Meteo Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api) | Kontinuirana povijesna serija sastavljena iz kratkih dijelova prognoza | Ne tretirati je automatski kao 24-satnu prognozu izdanu prethodnog dana |
| [ECMWF TIGGE](https://ecds.ecmwf.int/datasets/tigge-forecasts) | Duga arhiva ensemble prognoza od 2006.; korisna za dulja razdoblja | GRIB/MARS/ECDS pristup, veći obujam i složenost; provjeriti vremensku rezoluciju i varijable za izabrani model |
| [NOAA Open Data: GFS i drugi modeli](https://www.noaa.gov/nodd/datasets) | Alternativna arhiva originalnih ciklusa na javnim cloud spremištima | Pokrivenost i zadržavanje razlikuju se po datasetu; preuzimati cikluse i forecast korake, ne samo analize |
| [Copernicus ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) | Klimatski kontekst, analiza povijesnog vremena i istraživanje | Reanaliza s naknadnim opažanjima; nije prognoza koja je bila dostupna operateru u promatranom trenutku |

**Moj izbor:** prvo testirati zajedničko razdoblje za koje postoje stvarne oznake operacija i arhivirani ICON ciklusi. Bolje je kraće, provjerljivo razdoblje nego prividno odličan višegodišnji rezultat koji koristi podatke iz budućnosti. ERA5 i kasnije ispravljena opažanja mogu biti referenca za ishod, ali se ne smiju bez provjere dostupnosti koristiti kao ulazi u povijesnom trenutku predviđanja.

## Stvarni smjer operacija i pista 18

| Izvor | Što je potvrđeno dostupno | Što još treba provjeriti / dobiti |
|---|---|---|
| [Umwelthaus / UNH](https://www.umwelthaus.org/fluglaerm/anwendungen-service/aktuelle-betriebsrichtung-und-prognose/) | Aktualni 07/25, vrijeme od kada vrijedi; kao izvor stanja naveden DFS. Odvojeno objavljuje vlastitu prognozu u 8-satnim intervalima | Dokumentirani pristup, pravo daljnjeg korištenja i arhivski izvoz. Stranica spominje podatkovni servis na upit |
| [Fraport: aktualni smjer](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/aktuelles/aktuelle-betriebsrichtung.html) | Službena stranica aktualnog smjera | Nije potvrđen javni povijesni API. Prvi izbor za upit o izvozu operativnih oznaka zajedno s DFS/UNH |
| [DFLD Frankfurt](https://www.dfld.de/Mess/StatTag.php?D=20.04.2026&E=D&L=G&R=001&StatNr=137) | Povijesne stranice, prikazi smjera i buke; CSV izvoz dijela podataka | Testirani CSV sadrži vrijeme i dB(A) preleta, **ne** niz 07/25. Ne navoditi ga kao gotov dataset smjera. Zatražiti odgovarajući izvoz |
| [Fraport FRA.NoM / interaktivne karte](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/interaktive-karten.html) | Putanje letova i podaci o buci za vizualnu provjeru | Bulk pristup, dopuštena ponovna uporaba, povijesni raspon i dovoljna preciznost uz pistu |
| [OpenSky Network](https://opensky-network.org/data/) | ADS-B položaji i povijest putanja; javni API i zasebna povijesna baza | Pristup cijeloj povijesti kroz Trino nije univerzalno otvoren: postoje kriteriji za istraživače i licenciranje za privatne/komercijalne korisnike |
| [Flightradar24 API](https://fr24api.flightradar24.com/docs/endpoints/overview), [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/) | Komercijalni letovi, položaji, putanje i povijest prema proizvodu/planu | Cijena, pravo korištenja i pokrivenost uz tlo. Nije potvrđeno da daju gotovu oznaku „RWY18 usable” |
| [Grad Frankfurt: monitoring](https://frankfurt.de/fluglaermschutz/monitoring/monitoring-flugbewegungen) | Agregati i izvještaji o operacijama | Dnevne/mjesečne statistike služe provjeri distribucije, ne preciznom označavanju vremena promjene |

**Što tražiti od vlasnika podataka:** `valid_from_utc`, `valid_to_utc`, smjer `07/25`, status RWY18, razlog nedostupnosti, stvarna pista pojedinog polijetanja/slijetanja, vrijeme kada je informacija objavljena te kvaliteta zapisa. Za hackathon najvrjedniji je CSV promjena stanja s vremenskim oznakama, uključujući testne dane.

**Ako izvoz nije dostupan:** putanjama se može procijeniti smjer završnog prilaza i pista polijetanja. To su izvedene oznake s vlastitom nesigurnošću. Nema polijetanja na RWY18 može značiti slab promet, noćni režim, izbor druge piste, manjak prijema ili stvarnu zabranu. Negativnu oznaku „neupotrebljiva” ne dodjeljivati samo zato što nema letova. Stvarno korištenje, službeno stanje i meteorološka upotrebljivost moraju biti zasebna polja.

## Dodatni podaci koji mogu objasniti iznimke

| Izvor | Podaci | Prioritet |
|---|---|---|
| [DFS AIS portal i AIP](https://www.dfs.de/homepage/de/services/allgemeine-luftfahrt/) | Aerodromski postupci, AIP, operativne obavijesti i briefing; NOTAM o radovima/zatvaranju tražiti kroz ovlašteni servis | Korisno za razliku vremenske i stvarne dostupnosti. Javni automatizirani API nije potvrđen |
| [OurAirports open data](https://ourairports.com/data/) | Koordinate aerodroma i krajeva pista, oznake, dimenzije, pravci i statički status | Brz metapodatkovni izvor. Polje zatvaranja nije živi NOTAM ni dokaz trenutačne dostupnosti |
| [DWD CAP](https://opendata.dwd.de/weather/alerts/cap/) i [AWC SIGMET](https://aviationweather.gov/data/api/) | Meteorološka upozorenja, područje, vrsta pojave i interval valjanosti | P1, kontekst rizika |
| [DWD radar](https://opendata.dwd.de/weather/radar/) | Oborinske i konvektivne strukture, radarski proizvodi | P2, tek ako trebaju kratkoročne olujne promjene |
| DWD postaje u okolici i prognozni vjetar na 80/120/180 m ili 925 hPa | Dolazak promjene vjetra, razlika prizemnog i visinskog strujanja | P1 za poboljšanje modela; visinski vjetar ne uspoređivati izravno s prizemnim pragom |

## Konkretni provjereni upiti

Ovo su GET upiti bez ključeva. Datumi u arhivskim primjerima namjerno su fiksni; prilagoditi ih željenom razdoblju.

- [METAR EDDF, prethodna 2 sata](https://aviationweather.gov/api/data/metar?ids=EDDF&format=json&hours=2).
- [TAF EDDF](https://aviationweather.gov/api/data/taf?ids=EDDF&format=json).
- [ICON seamless, 49 satnih točaka i vjetar u čvorovima](https://api.open-meteo.com/v1/forecast?latitude=50.0333&longitude=8.5706&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&models=icon_seamless&wind_speed_unit=kn&timezone=UTC&forecast_hours=49).
- [Arhivirani ICON-D2 ciklus 20. 10. 2026. u 00 UTC](https://single-runs-api.open-meteo.com/v1/forecast?latitude=50.0333&longitude=8.5706&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&models=icon_d2&wind_speed_unit=kn&timezone=UTC&run=2026-10-20T00:00&forecast_days=2).
- [Bright Sky, trenutačna mjerenja postaje 01420](https://api.brightsky.dev/current_weather?dwd_station_id=01420).
- [Bright Sky, povijesna mjerenja](https://api.brightsky.dev/weather?dwd_station_id=01420&date=2026-10-20&last_date=2026-10-21).
- [MOSMIX_L, posljednji ciklus za 10637](https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/10637/kml/MOSMIX_L_LATEST_10637.kmz).
- [IEM CSV za EDDF, 20. 10. 2026.](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=EDDF&data=drct&data=sknt&data=gust&data=metar&year1=2026&month1=10&day1=20&year2=2026&month2=10&day2=21&tz=Etc%2FUTC&format=onlycomma&latlon=no&elev=no&missing=M&trace=T&direct=no&report_type=3&report_type=4).

Ovih 49 prognoznih točaka uključuje tekući zaokruženi sat. Aplikacija mora izričito odabrati 48 budućih satnih ciljeva od svog vremena izdavanja. `forecast_days=2` znači dva kalendarska dana u zatraženom ciklusu, ne automatski svaki traženi budući trenutak t+48.

## Što je stvarno provjereno

Probe su izvršene 30. 10. 2026., približno 11:33–11:36 po vremenu Europe/Berlin. Uzorak potvrđuje dostupnost tog dana; nije mjerenje SLA-a ni potpunosti cijele arhive.

| Provjera | Rezultat |
|---|---|
| AWC METAR | HTTP 200, četiri EDDF izvještaja u zatražena dva sata |
| AWC TAF | HTTP 200, jedan prognozni izvještaj s razrađenim intervalima |
| Open-Meteo prognoza | HTTP 200, 49 vrijednosti za brzinu, smjer i udare |
| Open-Meteo Single Runs | HTTP 200, 48 satnih vrijednosti brzine/smjera, 47 udara; jedan nedostajući udar |
| IEM povijest | HTTP 200, 48 izvještaja za 20. 10. 2026. |
| DWD vjetar i udari | Oba ZIP-a pročitana; svaki s 79.200 redaka od 28. 4. 2025. do 29. 10. 2026. |
| DWD povijesni katalog | Pronađena četiri arhivska dijela za 01420, početak 5. 3. 1993. |
| Bright Sky povijest | HTTP 200, 25 satnih zapisa u zatraženom uključivom intervalu; potvrđena postaja 01420 |
| Bright Sky aktualno | HTTP 200; stvarno vrijeme opažanja starije je od trenutka preuzimanja i mora se prikazati |
| MOSMIX | HTTP 200, stanica FRANKFURT/M, ciklus 09 UTC; pronađeni FF, DD, FX1 i ostali parametri |
| DFLD CSV | HTTP 200, ali sadržaj su vremena preleta i buka, bez oznake 07/25 |

Sažetak strojnih provjera nalazi se u `provjera-izvora.json`. Broj redaka ne znači da su sve vrijednosti valjane: potrebno je brojiti nedostajuće vrijednosti i provjeriti kvalitetu svakog polja.

## Trošak, prava korištenja i redoslijed rada

DWD CDC dopušta korištenje uz atribuciju prema [CC BY 4.0 uvjetima](https://opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.pdf). Bright Sky prenosi DWD podatke i njihove uvjete. [Open-Meteo besplatni API](https://open-meteo.com/en/pricing) namijenjen je nekomercijalnom radu, evaluaciji i prototipovima; za komercijalnu aplikaciju predviđen je plaćeni pristup. Otvoren prikaz Fraporta, UNH-a ili DFLD-a sam po sebi ne potvrđuje dozvolu za masovno preuzimanje ili redistribuciju.

Predloženi redoslijed:

1. Riješiti oznake stvarnih operacija i njihov povijesni raspon.
2. Učitati DWD vjetar/udare i IEM METAR za isti raspon.
3. Pridružiti stvarno dostupne cikluse ICON prognoza; spremati sirove odgovore i vrijeme primitka.
4. Izraditi fizikalni baseline prema pravilima zadatka, pa model usporediti s njim i s pretpostavkom da trenutni smjer ostaje isti.
5. Dodavati MOSMIX, ensemble, visinski vjetar i okolne postaje samo ako donose mjerljivo poboljšanje.

**Nesklad pravila koji treba evidentirati:** PDF zadatka koristi 10 kt za slijetanje, dok [Fraportovo javno objašnjenje](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/laerm-und-luft/flugbetrieb/betriebsrichtung.html) spominje promjenu pri približno 5 kt leđne komponente i razmatranje visinskog vjetra. Za baseline zadržati pravila hackathona; stvarne oznake uzeti iz opaženih operacija. Pragove verzionirati, ne zamjenjivati prešutno.
