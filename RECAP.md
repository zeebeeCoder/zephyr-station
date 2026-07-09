# RECAP: Zephyr — hiperlokalna stacja pogodowa (ESP32 + iOS + AI chat)

> Plik do wklejenia/przeczytania na starcie nowej sesji, zeby nie tlumaczyc
> wszystkiego od poczatku. Repo: `/Users/zeebs/code/miko/zephyr-station`
> (git: zeebeeCoder/zephyr-station, submodul w Mikobric/miko-arduino).

## Cel projektu
Wlasna stacja pogodowa na ESP32 z czujnikami srodowiskowymi. Dane leca przez
LoRa do domu, laduja w bazie i sa dostepne przez:
- **apke iOS "Zephyr"** (odczyty na zywo, wykresy historii, widget, Live Activity, Siri),
- **webowy chat AI** (pytania w naturalnym jezyku, SQL tool calls).

## Architektura (4 warstwy)
```
ESP32 + czujniki --LoRa--> Master node (ESP32, "dumb pipe")
  --HTTPS--> AWS (API Gateway + Lambda, Pulumi)
  --> Supabase PostgreSQL
  --> Next.js na Vercel (Vercel AI SDK) + apka iOS
```
- **Stacja zewnetrzna**: ESP32 + LoRa, solar/bateria, buforuje odczyty gdy brak ACK.
- **Master node**: ESP32 ~50 linii, LoRa -> HTTPS -> ACK, zasilany z sieci, bezstanowy.
- **Backend**: API Gateway + Lambda (`backend/functions`), infra w Pulumi.
- **Frontend**: Next.js + Vercel AI SDK, SQL przez `postgres.js` (`frontend/`).

Zasady: jedna baza (Supabase PG, bez InfluxDB/S3), koszt <$5/mies.,
latencja <10 s, odpornosc po stronie nadawcy (stacja buforuje).

## Struktura repo
```
zephyr-station/
├── firmware/         # station (czujniki+LoRa) i gateway (master node)
├── backend/functions # Lambdy: ingest, /v1/widget, /v1/history
├── infrastructure/   # Pulumi
├── frontend/         # Next.js chat AI (pnpm)
├── ios/              # apka iOS "Zephyr" (XcodeGen: project.yml!)
└── docs/             # prd-tech-design.md, esp32-integration-guide.md, specs/
```

## API (publiczne, read-only, bez logowania)
- `https://yvsssrfmu6.execute-api.eu-central-1.amazonaws.com/v1/widget?device_id=mstation`
- `.../v1/history?device_id=mstation&metric=...&range=...`

## Apka iOS (`ios/`)
- **XcodeGen** — zrodlem prawdy jest `ios/project.yml`; po zmianie regenerowac
  (`xcodegen`), ale UWAGA: recznie dopisane klucze w Info.plist moga nie byc
  w project.yml — sprawdzac spojnosc obu.
- Targety: `ZephyrStation` (app, iOS 17+/macOS 14+) + `ZephyrWidgetExtension`.
- Bundle ID: `com.zephyr.station` (+ `.widget`). Team: `K2HQH74UUP`.
- Funkcje: odczyty live, wykresy historii (`HistoryChartView`), widget,
  Live Activity (`LiveActivityManager`), skroty Siri (`ZephyrIntents`).
- Nazwa wyswietlana: **Zephyr** (bylo "Atlas" — zmienione 2026-07-09 w plist,
  project.yml i tytule skrotu Siri).
- `ITSAppUsesNonExemptEncryption=false` w plistach -> brak pytania o export
  compliance przy uploadzie.

## TestFlight / App Store Connect (stan na 2026-07-09)
- Nowe konto Apple Developer kupione; apka **ZephyrStation** w App Store Connect.
- **Internal testing**: grupa z uzytkownikiem "Me" — dziala.
- **External testing**: grupa **family** (1 tester). Build `1.0 (2)` wyslany
  do Beta App Review — status "Waiting for Review" (pierwszy review: do ~48 h;
  kolejne buildy tej samej wersji 1.0 dolaczaja BEZ ponownego review).
- **Test Information** wypelnione: opis beta, feedback email, kontakt
  (Mikolaj Siwiec, +48 502963127, miko.siwiec@gmail.com), Review Notes
  (wyjasnienie: dane z fizycznej stacji przez publiczne API, bez logowania).
  Sign-in required: NIE. Marketing/Privacy URL: puste (opcjonalne dla TF).
- Build `1.0 (3)` z nazwa "Zephyr" wgrany 2026-07-09 (CFBundleVersion=3
  w obu plistach). Po review dodac go tez do grupy family.
- Build w TestFlight wygasa po 90 dniach.

## Stan gita (2026-07-09)
- `zephyr-station` main: `5e0bf11` "fix(ios): rename app display name from
  Atlas to Zephyr, bump build to 3" — wypchniete.
- Submodul w `miko` zaktualizowany (`14cfdd2` i wczesniejsze), wypchniete.
- Commity zawsze jako **Miko**, bez atrybucji Claude.

## STATUS / nastepny krok
- Czekamy na wynik Beta App Review (mail od Apple).
- Po zatwierdzeniu: tester z "family" dostanie zaproszenie mailem
  (sprawdzic spam; potrzebna apka TestFlight na iPhone). Opcjonalnie wlaczyc
  Public Link w ustawieniach grupy.
- Dodac build `1.0 (3)` do grupy family (bez nowego review).
- Dalej: publikacja w App Store bedzie wymagac Privacy Policy URL
  (apka nie zbiera danych -> wystarczy prosta strona).

## Czego NIE robic / na co uwazac
- Nie edytowac `ZephyrStation.xcodeproj` recznie — projekt generuje XcodeGen
  z `project.yml`.
- Numer buildu = `CFBundleVersion` w OBU plistach (app + widget) — musza byc rowne.
- Nowa WERSJA (np. 1.1) w external testingu znow przechodzi Beta App Review;
  nowy BUILD tej samej wersji — nie.
- API jest publiczne i read-only — w apce nie ma i nie potrzeba logowania.
