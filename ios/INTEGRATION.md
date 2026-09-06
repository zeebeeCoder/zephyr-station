# iOS integration handoff

This file is the self-contained handoff for building, signing, testing, and releasing the Zephyr iOS application from a Mac. It contains configuration identifiers only—never API keys, Apple credentials, provisioning profiles, WireGuard keys, or certificate private keys.

## Current status

- The private API is live at `https://omarchy.tail4e6e78.ts.net`.
- `GET /up` and database-backed `GET /ready` are healthy with normal public certificate trust.
- `WeatherService` uses `https://omarchy.tail4e6e78.ts.net/v1` with no HTTP, AWS, or certificate-bypass fallback.
- Widget and history requests use the fixed device ID `mstation`.
- Safari has proved the intended network boundary:
  - household LAN: available through private DNS;
  - off-LAN 5G with UDM WireGuard: available;
  - off-LAN 5G without WireGuard: hostname does not resolve.
- The app change has not been built or released from this Linux host because Xcode, Swift, and XcodeGen are unavailable here.
- The local database did not yet contain a real `mstation` reading when this handoff was written. Complete the firmware cutover before final UI acceptance, or expect `/v1/widget` to return 404.
- AWS/Supabase remain available for rollback. The app has no runtime fallback to them.

Tracking: private consumer cutover is Gate 5 in PKM task `2026-08-31-T0005`. Firmware hardening is PKM task `2026-09-04-T0001`.

## Runtime configuration

| Setting | Current value | Source |
|---|---|---|
| API base | `https://omarchy.tail4e6e78.ts.net/v1` | `ZephyrStation/WeatherService.swift` |
| Device ID | `mstation` | `ZephyrStation/WeatherService.swift` |
| iOS minimum | iOS 17.0 | `project.yml` |
| Swift | 5.9 | `project.yml` |
| App bundle ID | `com.zephyr.station` | `project.yml` |
| Widget bundle ID | `com.zephyr.station.widget` | `project.yml` |
| Apple team | `K2HQH74UUP` | `project.yml` |
| Signing | Automatic | `project.yml` |
| Marketing version | `1.0` | both target `Info.plist` files |
| Current build | `3` | both target `Info.plist` files |

The team identifier and bundle identifiers are configuration, not credentials. Confirm that the Apple account used on the Mac belongs to that team and can manage both identifiers.

## Credentials and secrets

### Not required by the app

The iOS client only reads `/v1/widget` and `/v1/history`. Those endpoints rely on the private LAN/WireGuard boundary and do not require an API key. **Never embed the ESP ingestion key in the application, widget, source tree, Info.plist, build settings, or TestFlight metadata.**

The API certificate is publicly trusted. Do not bundle a private CA, disable hostname validation, pin the short-lived leaf certificate, or add an App Transport Security exception.

### Required outside Git

- An Apple Developer/App Store Connect account with access to team `K2HQH74UUP`.
- Local Apple signing keys and automatically managed provisioning profiles for the app and widget extension.
- App Store Connect permission to create/upload an internal TestFlight build.
- The household WireGuard profile installed on each off-LAN test device. Its private key remains in the WireGuard/iOS configuration, not this application.

For automated App Store uploads later, keep any App Store Connect API issuer/key ID and `.p8` key in the CI secret manager. No such automation or credential is currently part of this repository.

## API contract used by iOS

### Latest reading

```http
GET /v1/widget?device_id=mstation
```

Expected status: `200`. The decoder requires:

- `device_id`
- `recorded_at`
- `readings.temperature_c`
- `readings.humidity_pct`
- `readings.pressure_hpa`
- `meta.battery_v`
- `meta.rssi`
- `station_status`

PM values, wind, gas, and system current may be null. Extra API fields such as `data_age_seconds` are safely ignored.

### History

```http
GET /v1/history?device_id=mstation&metric=temperature_c&range=24h
```

Supported metrics:

- `temperature_c`
- `humidity_pct`
- `pressure_hpa`
- `pm25`, `pm10`, `pm1`
- `wind_speed_ms`
- `gas_density`
- `battery_v`

Supported ranges: `24h`, `7d`, and `30d`.

The decoder expects `device_id`, `metric`, `range`, `unit`, and `points`, where each point contains timestamp `t` and numeric value `v`.

## Mac bootstrap

1. Install a current Xcode release that supports the project’s iOS 17 deployment target and Swift 5.9 or later.
2. Install Xcode command-line tools and accept the Xcode license.
3. Install XcodeGen, for example:

   ```bash
   brew install xcodegen
   ```

4. Fetch the reviewed repository state:

   ```bash
   git clone git@github.com:zeebeeCoder/zephyr-station.git
   cd zephyr-station
   git switch main
   git pull --ff-only
   ```

5. Confirm tools:

   ```bash
   xcodebuild -version
   xcodegen --version
   ```

6. Generate the project:

   ```bash
   cd ios
   xcodegen generate
   open ZephyrStation.xcodeproj
   ```

The generated `ios/*.xcodeproj` and DerivedData are intentionally ignored. `ios/project.yml` is the source of truth.

## API preflight from the Mac

Run these from the same network path that the device will use:

```bash
curl --fail --show-error https://omarchy.tail4e6e78.ts.net/up
curl --fail --show-error https://omarchy.tail4e6e78.ts.net/ready
curl --include \
  'https://omarchy.tail4e6e78.ts.net/v1/widget?device_id=mstation'
```

Do not use `--insecure` or a raw-IP URL. A remote Mac needs the household WireGuard route or its separately approved private Tailscale administration path. Before the first `mstation` reading, expect the widget request to show HTTP 404: that proves the API is reachable but the station data is not present. After firmware ingestion begins, repeat it with `curl --fail-with-body` and require HTTP 200.

## Build and signing

In Xcode:

1. Open **Settings → Accounts** and sign in with the authorized Apple Developer account.
2. Select the `ZephyrStation` project and confirm team `K2HQH74UUP` for both targets.
3. Confirm Xcode can automatically manage signing for:
   - `com.zephyr.station`
   - `com.zephyr.station.widget`
4. Resolve any identifier/profile conflict in the Apple Developer portal rather than changing bundle IDs casually.
5. Select an iPhone simulator and build once.
6. Select a registered physical iPhone and build/install a Debug build.

A command-line simulator compile can be run after generation:

```bash
xcodebuild \
  -project ZephyrStation.xcodeproj \
  -scheme ZephyrStation \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO \
  build
```

Before every TestFlight upload, increment `CFBundleVersion` consistently in both:

- `ZephyrStation/Info.plist`
- `ZephyrWidget/Info.plist`

Keep app and extension marketing/build versions aligned.

## Physical-device acceptance matrix

Use a real `mstation` reading and record device model, iOS version, app commit, and build number.

| Path | Expected result |
|---|---|
| Home Wi-Fi, WireGuard off | Live and History load with trusted TLS |
| 5G, Wi-Fi off, WireGuard on | Live and History load with trusted TLS |
| 5G, Wi-Fi and WireGuard off | Hostname/API load fails |
| Enable WireGuard after failure | Pull-to-refresh recovers without reinstall |

Disable Tailscale on the phone while proving the WireGuard cases. Force-close/reopen the app between negative and recovery tests so a retained network connection cannot obscure the result.

## Application-surface checklist

1. **Live screen**
   - Cold-launch and pull-to-refresh.
   - Compare temperature, humidity, pressure, PM, wind, battery, RSSI, station status, and timestamp with the API response.
   - Confirm stale/offline status is represented correctly.
2. **History**
   - Load temperature, PM2.5, and wind charts.
   - Exercise day and week; optionally month when enough data exists.
   - Confirm empty history is distinct from network/decoding failure.
3. **Home/lock-screen widgets**
   - Add each relevant widget, background/terminate the app, lock the phone, and wait for a refresh.
   - Compare against real station values. The current provider silently substitutes synthetic placeholder values when fetching fails, so a plausible-looking widget is not sufficient proof.
4. **Siri and Shortcuts**
   - Run “Get Zephyr Reading” and at least one explicit metric.
   - Confirm spoken values match the API.
5. **Live Activity**
   - Start it from the app and observe at least one 45-second update.
   - Background and lock the phone. Treat continued polling as best-effort: iOS may suspend the process because this implementation does not use remote ActivityKit pushes.
6. **Failure/recovery**
   - With WireGuard unavailable off-LAN, confirm the app shows a clean load failure rather than legacy or placeholder data.
   - Re-enable WireGuard and verify foreground refresh recovery.

## Known integration issues to inspect before TestFlight

These are not credentials, but they should be reviewed on the Mac before release:

1. `WeatherService` currently does not inspect `HTTPURLResponse.statusCode` before decoding. A 4xx/5xx response becomes a generic decoding/load error.
2. History timestamps contain a UTC `Z`, but the formatter currently sets `TimeZone.current`. Parse backend timestamps as UTC with an ISO-8601 strategy that accepts fractional seconds, and add decoder fixtures before trusting chart times outside UTC; merely retaining the exact-three-fraction formatter remains brittle.
3. Widget fetch failure silently displays synthetic placeholder data. Add an explicit unavailable/stale state so network failure cannot look like a real reading.
4. The device ID and API URL are compile-time constants. That is acceptable for one household station, but any future station selection should use a reviewed configuration model rather than scattered literals.
5. Background widget refresh and Live Activity polling depend on iOS scheduling and WireGuard availability. Validate on the actual family devices; do not publish the API to work around VPN scheduling.
6. This repository currently has no iOS unit/UI test target or CI build. At minimum, add response-decoder fixtures and a generated-project build check on a macOS runner before routine releases.

## Internal TestFlight release

After physical Debug acceptance:

1. Increment both target build numbers.
2. Select **Any iOS Device (arm64)**.
3. Run **Product → Archive**.
4. In Organizer, validate the archive and confirm both app and widget are signed by the expected team.
5. Choose **Distribute App → App Store Connect → Upload**.
6. In App Store Connect, complete export-compliance prompts. The project declares `ITSAppUsesNonExemptEncryption=false` because it uses standard OS HTTPS rather than custom encryption; verify that remains accurate.
7. Release to internal testers first.
8. Repeat the complete network and surface matrix using the TestFlight build before broader family distribution.

Do not retire or destroy AWS/Supabase merely because the iOS build succeeds. Cutover requires real ESP ingestion, iOS acceptance, scheduled backups/certificate renewal, and the observation window recorded in T0005.

## Rollback

- Keep the previous installable AWS-pointing iOS build, or prepare a reviewed endpoint-revert build, during the observation period.
- Roll back the client build/endpoint if private DNS, VPN background behavior, decoding, or station ingestion is unusable.
- Do not add HTTP fallback, certificate bypass, embedded ingest credentials, public DNS, or WAN forwarding as a recovery shortcut.
- Preserve local PostgreSQL data and keep AWS/Supabase available until retirement receives separate approval.

## Source map

| Concern | File |
|---|---|
| Endpoint and query construction | `ZephyrStation/WeatherService.swift` |
| Widget response model | `ZephyrStation/WeatherData.swift` |
| History model, metrics, and ranges | `ZephyrStation/HistoryData.swift` |
| Foreground Live/settings/history integration | `ZephyrStation/ContentView.swift` |
| Chart loading and errors | `ZephyrStation/HistoryChartView.swift` |
| Widget timelines and placeholder behavior | `ZephyrWidget/ZephyrLockScreenWidget.swift` |
| Siri/Shortcuts | `ZephyrStation/ZephyrIntents.swift` |
| Live Activity polling | `ZephyrStation/LiveActivityManager.swift` |
| Targets, signing team, bundle IDs | `project.yml` |
| App/widget versions | target `Info.plist` files |

## Acceptance evidence template

Record this in T0005 without credentials:

```text
Commit:
Marketing/build version:
Xcode/XcodeGen versions:
Mac model/macOS:
iPhone model/iOS:
Signing team and bundle identifiers verified: yes/no
Simulator build: pass/fail
Physical Debug build: pass/fail
Archive validation/upload: pass/fail
LAN foreground/history: pass/fail
5G + WireGuard foreground/history: pass/fail
5G without VPN denied: pass/fail
Widget refresh with real values: pass/fail
Siri/Shortcut: pass/fail
Live Activity foreground/background: pass/fail
Failure then VPN recovery: pass/fail
Known limitations/rollback build:
```
