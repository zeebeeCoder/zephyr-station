# Przegląd koordynatora: enclosure draft A — 27.10.2026

Zakres: przeczytano w całości README.md, fusion-spec.md (761 linii), print-and-test.md (164), pcb-interface.md (25). Przegląd tekstu, spójności i interfejsów; bez modelu CAD, symulacji, slicera, sprawdzania wszystkich źródeł research ani prób fizycznych. Nie jest to odbiór konstrukcji ani zgoda na druk, zakupy lub commit.

## Wynik

Draft nadaje się do dalszego parametrycznego opracowania, z blokadami na finalny eksport/druk. Nie ma powodu wstrzymywać aktualizacji dokumentacji do czasu otrzymania wszystkich pomiarów. Koncepcje 1A–5A pozostają przyjęte; wymiary PCB i szczegóły konstrukcyjne nie uzyskują przez ten przegląd zatwierdzenia.

## Do kolejnej rewizji dokumentacyjnej

1. Zaktualizować stan odpowiedzi pcb-design w README, fusion-spec §2/8/11 i pcb-interface. Odpowiedź już nadeszła: 100×80 to punkt wyjścia, nie potwierdzenie layoutu; kabel 1,5–2 m ma warunkowe obliczenia (100 kHz, ≤250 pF/linia, pull-up 3,3 kΩ, TVS ≤5 pF), nie kwalifikację konkretnego breakoutu. D8 w dokumentach F1 pozostaje bez zmiany. Rozdzielić „odpowiedź otrzymana” od „sprawdzone w sprzęcie/zaakceptowane w F1”.
2. Wprowadzić uwagi antenowe jako jawne parametry/alternatywy i tabelę statusów, bez zatwierdzania obrysu: overhang 6–7 mm, pozycja modułu ok.60/64 mm, konflikt metalu oraz co dokładnie oznacza zapas +20 mm (możliwość powiększenia, nie bezwarunkowo większy BOX). Obecne wartości 64/0 i historyczne 66 nie mogą wyglądać jak uzgodnione przez obu projektantów. Wymagany CAD keep-out, nie tylko odległość 2D.
3. Doprecyzować globalną regułę hole_add: ins3_D i ins4_D już zawierają dodatek; clr_M3/clr_M4 i otwory PCB są wartościami docelowymi czy przed dodatkiem? Jednoznaczna tabela średnica modelowana / kupon, bez podwójnej kompensacji.
4. Reguły orientacji ROOF i płaskiego adaptera wymagają potwierdzenia w CAD/slicerze: dach ma nachylenie 10°, a adapter podpórki z tyłu Ø14×2. Samo „top/back face down” nie dokumentuje rzeczywistego kontaktu z płytą ani braku podpór. Nie stwierdzam nieprintowalności, żądam wskazania płaszczyzny ułożenia i ewentualnych podpór/mostów. Checklisty jako niezaliczone, aż istnieje model.
5. RF test rozdzielić na LoRa 868 MHz (odbiór/RSSI/SNR na właściwej bramce) i Wi-Fi/OTA (AP/odbiornik Wi-Fi). Obecne „ESP32 RSSI at the gateway” jest niejednoznaczne. OTA/flash i testy sprzętowe nadal podlegają istniejącym zgodom; instrukcja testu nie jest zgodą jego wykonania.
6. Dla cradle BME zachować oba warianty jako robocze. M2 i wymiary z obrazka nie są potwierdzone; nie wygenerować finalnego uchwytu z placeholderów. PMS: porty, płytka i plug clearance nadal bramka osobnego komponentu.

## Warunki przed drukiem/modelowaniem finalnym

- CAD interference check wszystkich części, narzędzi i wiązek, także wkładek/śrub oraz baterii/retainer bosses; sam bbox pack+foam nie potwierdza braku kolizji z lokalnymi bossami.
- Symulacja/obliczenie sztywności pokrywy i kupon; siła uszczelki i tolerancje wykonania pozostają warunkowe.
- P2S profile/obszar wyłączony/brimy/kompensacja i rzeczywisty filament/dysza do sprawdzenia, bez uniwersalizacji wtórnych danych.
- Uzgodnienie PCB/F3, rzeczywiste pomiary sensorów/portów/wtyczek, kabli/dławików, pigtaila i mocowania.
- Zagadnienia termiczne pakietu i próby terenowe nie zamykają się przez sam log pierwszego lata; nie traktować modelu ≤41°C ani threshold38°C jako dowiedzionej ochrony ogniw.

Nie zmieniano plików projektu, nie uruchamiano CAD ani testów, nic nie commitowano.
