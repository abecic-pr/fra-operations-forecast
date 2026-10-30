# Podaci aplikacije i modela

Preporučeni podatkovni ugovor, 30. 10. 2026. Obuhvat: Frankfurt/EDDF, smjer operacija 07/25, meteorološka upotrebljivost RWY18 i prognoza po satima do 48 h. Izvori i provjerene poveznice nalaze se u `izvori-podataka.md`.

Zahtjevi su izdvojeni iz korisnikova PDF-a `AI_Week_2026_Hackathon_-_FraAlliance_Case.pdf`, stranica 1, odjeljci 1–4. Dodatna polja ispod su preporuka za provedbu, a ne dodatni zahtjevi organizatora.

## Podaci koje osoba koja prati aplikaciju mora moći dobiti

| Podatak | Preporučeno polje | Sadržaj / jedinica | Prioritet |
|---|---|---|---|
| Aerodrom i vremenska zona | `airport_icao`, `display_timezone` | EDDF, Europe/Berlin | P0 |
| Aktualni opaženi smjer operacija | `observed_operating_direction` | `07`, `25` ili `unknown`; nikad vremenska prognoza predstavljena kao opažanje | P0 |
| Od kada vrijedi aktualni smjer | `operating_direction_since` | Vremenska oznaka ili null ako nije poznato | P0 |
| Izvor i vrijeme provjere smjera | `operating_direction_source`, `operating_direction_observed_at` | DFS/UNH, Fraport ili izvedeno iz letova, uz oznaku pouzdanosti | P0 |
| Srednja brzina vjetra | `wind_speed_kt` | Čvorovi; uz razdoblje usrednjavanja | P0 |
| Smjer iz kojeg vjetar puše | `wind_from_deg_true` | 0–360° u odnosu na pravi sjever; null za nepoznat/promjenjiv smjer | P0 |
| Promjenjivost smjera | `wind_variable`, `wind_sector_from_deg`, `wind_sector_to_deg` | Sačuvati VRB i raspon iz sirovog METAR-a | P0 |
| Udari vjetra | `wind_gust_kt`, `gust_from_deg_true` | Maksimum i njegov smjer kad je poznat; null nije 0 | P0 |
| Čeona/leđna komponenta za 07, 25 i 18 | `runway_wind[].headwind_kt`, `tailwind_kt` | Izračunato iz smjera, brzine i orijentacije piste | P0 |
| Bočna komponenta i komponenta udara | `runway_wind[].crosswind_kt`, `gust_crosswind_kt` | Posebno za svaki smjer, uz oznaku aproksimacije ako smjer udara nije poznat | P0 |
| Odmak od pragova | `tailwind_margin_kt`, `crosswind_margin_kt` | Pozitivna vrijednost znači preostali odmak; granični uvjeti prema pravilima ispod | P0 |
| Procjena trenutačne meteorološke upotrebljivosti 18 | `rwy18_weather_state` | `usable`, `not_usable`, `uncertain`, `unknown` | P0 |
| Potvrđen operativni status 18 | `rwy18_operational_status` | `open`, `closed`, `restricted`, `unknown`; samo uz odgovarajući izvor | P0 |
| Prognozirani smjer za svaki budući sat | `forecast[].operating_direction` | `07`, `25` ili `unknown` | P0 |
| Vjerojatnosti smjera | `forecast[].p_od07`, `p_od25` | Broj 0–1; zbroj 1 kad je klasifikacija raspoloživa | P0 |
| Vjerojatnost upotrebljivosti 18 | `forecast[].p_rwy18_weather_usable` | Broj 0–1; jasno da se odnosi na vremenske uvjete | P0 |
| Prognoza vjetra i udara po satu | `forecast[].wind_speed_kt`, `wind_from_deg_true`, `wind_gust_kt` | Iste jedinice i definicije kao opažanja | P0 |
| Sljedeća očekivana promjena smjera | `next_od_change` | Od/do kojeg smjera, vrijeme ili vremenski prozor, vjerojatnost i status | P0 |
| Sljedeća očekivana promjena upotrebljivosti 18 | `next_rwy18_change` | Pogoršanje/poboljšanje, vremenski prozor i vjerojatnost | P0 |
| Razlog procjene ili upozorenja | `reason_codes`, `reason_text` | Npr. leđni vjetar, bočni udari, trajanje nepovoljnog vjetra, neslaganje modela | P0 |
| Starost i kvaliteta podataka | `data_age_seconds`, `quality_status` | Svjež, zastario, nepotpun, bez podataka; po izvoru | P0 |
| Vrijeme izdavanja i horizont | `forecast_issued_at`, `valid_time`, `lead_time_hours` | Ne miješati vrijeme generiranja i vrijeme na koje se prognoza odnosi | P0 |
| Dodatni meteorološki kontekst | `visibility_m`, `ceiling_ft_agl`, `weather_codes`, `temperature_c`, `dew_point_c`, `qnh_hpa` | Vidljivost, baza najnižeg BKN/OVC sloja ili vertikalna vidljivost, pojave, temperatura, rosište, tlak | P1 |
| Upozorenja i nevremenski razlozi | `weather_alerts`, `operational_restrictions` | SIGMET/CAP/NOTAM s područjem i intervalom valjanosti | P1 |
| Kvaliteta modela na testu | `model_metrics_by_horizon` | Rezultati za 1, 6, 24 h, testno razdoblje i broj uzoraka/događaja | P0 za evaluaciju |

P0 = prva verzija; P1 = koristan dodatak nakon osnovnog toka. Polje može biti obavezno u ugovoru i imati `null`/`unknown` kada izvor nije dostupan. To je točnije od izmišljanja vrijednosti.

`next_*_change` treba imati status `change_expected`, `no_change_within_horizon` ili `unknown`. Null vrijeme bez statusa nije dovoljno. Satna prognoza ne opravdava prividnu preciznost promjene na minutu; prikladniji je interval. Vjerojatnost događaja u intervalu nije isto što i vjerojatnost jedne klase u jednom satu.

## Ulazni podaci koje treba spremati za model

| Skup | Minimalna polja | Zašto |
|---|---|---|
| Opažanja vjetra | Vrijeme, brzina, smjer, udar, smjer udara, interval mjerenja, zastavice kvalitete | Glavni prediktori i izračun komponenti |
| Nedavna povijest | Posljednjih 10/30/60/180 min, u/v komponente, varijabilnost, maksimumi, promjena smjera/brzine | Razlikuje prolazni udar od postojane promjene |
| Aktualne operacije | Opaženi OD, vrijeme posljednje promjene, status 18 ako je poznat, starost podatka | Postojanost i početno stanje modela |
| Prognozni ciklusi | Model, ciklus, trenutak dostupnosti, valjano vrijeme, horizont, vjetar/udari | Uvjeti u budućnosti bez korištenja informacija koje još nisu postojale |
| Dodatna meteorologija | Temperatura, rosište, tlak i njegova promjena, vidljivost, oblaci, oborine | Ispitati poboljšava li predviđanje |
| Prostorni/visinski kontekst | Okolne postaje, koordinata prognozne ćelije, vjetar iznad tla | Mogući dolazak promjene iz smjera Taunusa |
| Ishodi za učenje | Stvarni OD po vremenu, promjene OD, stvarna pista leta, status 18 i razlog, izvor oznake | Za treniranje i nezavisnu evaluaciju |
| Podrijetlo svakog zapisa | URL/proizvod, identifikator postaje, vrijeme preuzimanja, sirovi zapis, verzija parsera | Reprodukcija i razlikovanje izvora |

Predloženi početni skup značajki: `u10`, `v10`, udar, leđna i bočna komponenta za 07/25/18, trenutni OD, trajanje trenutnog OD, trajanje leđnog vjetra, trend vjetra kroz 30/60 min te prognozni u/v i udari za ciljni sat. Temperaturu/tlak/visinski vjetar dodati tek nakon usporedbe rezultata. Sezonski i satni pokazatelji mogu biti korisni, ali sami ne zamjenjuju meteorološke ulaze.

Vjetar iz DWD-a, Bright Skyja i Meteostata može potjecati iz iste postaje. Ne brojiti takve kopije kao tri neovisna mjerenja.

## Pravila zadatka i izvedeni podaci

Za baseline koristiti orijentacije iz PDF-a: 07 = 70°T, 25 = 250°T, 18 = 180°T. Za stvarnu geometriju zasebno spremiti provjerene orijentacije iz AIP-a ili metapodataka; ne miješati magnetske oznake piste s pravim sjeverom.

Za brzinu `V`, smjer iz kojeg vjetar puše `theta` i orijentaciju piste `psi`:

```text
delta = theta - psi                    # trigonometrija koristi radijane
headwind = V * cos(delta)              # pozitivno: čeoni vjetar
tailwind = max(0, -headwind)
crosswind = abs(V * sin(delta))
```

Ako je poznat smjer udara, komponente udara računati iz njega. Ako nije, uporaba srednjeg smjera uz brzinu udara je aproksimacija i mora biti označena. Ne kombinirati neusklađene maksimume i smjerove iz različitih intervala kao da su ista pojava. Za VRB ili širok raspon smjera može se prikazati raspon komponenti, umjesto jedne lažno precizne vrijednosti.

| Pravilo iz PDF-a | Podatak koji mora postojati |
|---|---|
| Leđni vjetar za slijetanje mora biti < 10 kt; pri ≥ 10 kt slijedi promjena OD | Leđna komponenta na trenutno aktivnom smjeru |
| Leđni vjetar za polijetanje mora biti < 15 kt | Komponenta za odabranu pistu polijetanja |
| Na RWY18 leđna komponenta ≥ 15 kt onemogućuje polijetanje | `tailwind_18_kt`, odstupanje od 15 kt |
| Bočni vjetar > 40 kt, uključujući udare, zatvara pistu | Srednja bočna komponenta i bočna komponenta udara |
| Slabiji leđni vjetar može trajati do 30 min prije promjene | Vremenska serija i trajanje neprekinutog intervala, ne samo jedan satni prosjek |

Primjeri iz zadatka: 090°/20 kt daje približno 18,8 kt leđne komponente na smjeru 25; 330°/20 kt daje približno 17,3 kt leđnog vjetra na RWY18.

Odmak `limit - component` tumačiti zajedno s operatorom: pri leđnom vjetru odmak 0 znači dosegnut zabranjeni prag, dok je bočni prag u PDF-u strogo `>40`. Spremiti `ruleset_version` za ovakve rubne uvjete.

Ako su oba paralelna smjera nepovoljna zbog bočnog vjetra, to treba biti zaseban status ograničenja. Forsirani izbor 07/25 ne znači da su operacije moguće. Smjer operacija i dostupnost pista nisu ista ciljna varijabla.

Fraport javno opisuje promjenu pri približno 5 kt leđne komponente, različito od 10 kt u zadatku. Za usporedbu s hackathon baselineom zadržati PDF pravila, a stvarne ishode učiti iz nezavisnih opažanja. [Izvor za stvarni operativni kontekst](https://www.fraport.com/de/nachhaltigkeit/nachbarschaftsdialog/laerm-und-luft/flugbetrieb/betriebsrichtung.html).

## Vrijeme, jedinice i nedostajući podaci

- Sva vremena spremati kao UTC s eksplicitnim `Z`/offsetom. Europe/Berlin koristiti za prikaz. Pri promjeni ljetnog/zimskog vremena lokalni sat nije jedinstveni ključ.
- Razlikovati `observed_at`, `interval_start/end`, `issued_at`, `model_run_at`, `available_at`, `fetched_at`, `valid_time`. Inicijalizacija modela prethodi objavi; u provjeri ne smije biti dostupna prije stvarnog vremena objave. [Open-Meteo objašnjenje ciklusa](https://open-meteo.com/en/docs/single-runs-api).
- `generationtime_ms` u Open-Meteo odgovoru jest vrijeme obrade API zahtjeva, a ne vrijeme izdavanja meteorološke prognoze.
- Koristiti čvorove za operativne pragove: m/s × 1,943844; km/h ÷ 1,852. Čuvati i izvorne jedinice. Bright Sky koristi km/h za brzinu, a provjereni Open-Meteo upit izričito traži `kn`.
- Smjer vjetra usrednjavati kružno ili preko u/v komponenti; prosjek 350° i 10° nije 180°. Za meteorološki smjer iz kojeg puše: `u=-V*sin(theta)`, `v=-V*cos(theta)`.
- Tišina, promjenjiv smjer i nedostajući smjer tri su različita stanja. `VRB` nije nula stupnjeva. Izostanak prijavljenog udara u METAR-u nije dokaz da je udar 0 kt.
- METAR vidljivost i oblaci imaju vlastite jedinice i kodove. U testiranom AWC JSON-u `visib="6+"` nije šest metara; sirovi `9999` znači najmanje 10 km. Pravilno parsirati `CAVOK`, `NSC`, `BKN` i `OVC`, bez izmišljanja točne vidljivosti/baze.
- Popunjavanje nedostajućeg gust polja ne smije tiho pretvoriti nepoznatu komponentu udara u „sigurno”. Smanjiti kvalitetu procjene ili vratiti `unknown` za pogođenu provjeru.
- Provjeravati posljednji **valjani zapis**, ne samo HTTP 200. Predloženi pragovi zastarjelosti trebaju biti konfigurabilni po izvoru i vezani uz izmjerenu kadencu.
- Čuvati izvorni METAR/TAF i ulazni forecast odgovor: parser može propustiti varijabilnost smjera, posebne grupe ili naknadne izmjene.

## Stvarni ishodi, vjerojatnosti i testiranje

Četiri različite vrste podataka ne spajati u jedno polje: **mjerenje vremena**, **numerička prognoza vremena**, **službeno/opaženo stanje operacija** i **predikcija našeg modela**.

Za RWY18 odvojiti:

- `rwy18_weather_usable`: procjena prema vjetru i zadanim pravilima.
- `rwy18_used`: je li opaženo polijetanje u definiranom intervalu.
- `rwy18_operational_status`: potvrđeno otvorena/zatvorena/ograničena.

Prvo se može izračunati bez letova. Drugo zahtijeva prometne podatke. Treće zahtijeva pouzdan operativni izvor. Nula polijetanja nije negativna oznaka za prvo ili treće. Ako nema stvarnih oznaka, jasno izvijestiti da model još nije validiran prema stvarnim operacijama; treniranje na oznakama dobivenim istim pravilima ne dokazuje poboljšanje nad baselineom.

Vjerojatnosti ne izmišljati iz udaljenosti od praga. Dobiti ih iz modela ili ensemble članova, pa provjeriti kalibraciju na odvojenim datumima. Udio ensemble članova koji zadovoljavaju kriterij jest početna procjena, ne automatski kalibrirana vjerojatnost. „80%” treba imati provjerljivo statističko značenje.

Testirati kronološki, uz razdvajanje treninga, kalibracije i testa te sprečavanje preklapanja budućih ciljnih intervala preko granica. Za svaki trenutak t koristiti samo ulaze čiji je `available_at <= t`. Kasniji TAF AMD/COR, reanaliza ili naknadno ispravljeni zapisi ne smiju neprimjetno ući kao tada poznati podaci.

| Rezultat za izvještaj | Zašto treba |
|---|---|
| Accuracy i balanced accuracy / F1 po smjeru | Dominantni smjer može prikriti slabu detekciju rjeđe klase |
| Brier score ili log loss i provjera kalibracije | Kvaliteta vjerojatnosti, ne samo kategorije |
| Precision/recall promjena i pogreška vremena promjene | Operateru su promjene često najvažniji događaji |
| RWY18 recall neupotrebljivosti i broj lažnih upozorenja | Odvojiti propuštene nepovoljne uvjete od prečestih upozorenja |
| Broj slučajeva, broj promjena i udio pokrivenosti | Pokazuje koliko je evaluacija reprezentativna |
| Iste metrike za 1, 6 i 24 h | Izričit zahtjev PDF-a |
| Usporedba s fizikalnim pravilima i zadržavanjem trenutnog stanja | Potrebna da se pokaže doprinos modela |

Točan output za žiri (imena stupaca, testni dani, način označavanja sata i značenje RWY18 cilja) nije naveden u priloženoj stranici. Pri spajanju s njihovim skupom to treba uskladiti; ne pretpostavljati da jedan sat sadrži samo jedan smjer ako je tijekom njega došlo do promjene.

## Što bih izostavio iz prve verzije

UV indeks, osjet temperature, kvaliteta zraka, vlaga tla, sunčevo zračenje, višemjesečni klimatski prosjeci, podaci o putnicima, gateovima, prtljazi i financijama nisu prioritet za ovaj zadatak. Radar, satelitske slike, detalji svih letova i više paralelnih komercijalnih vremenskih API-ja povećavaju posao prije nego što je riješen ključan problem stvarnih oznaka.

Ako je vrijeme ograničeno: **DWD vjetar + udari, METAR, ICON arhivirani ciklusi, opaženi OD i status/korištenje 18, izvedene komponente, 48 satnih predikcija, vrijeme promjene i kvaliteta podataka** čine minimalan smislen skup.
