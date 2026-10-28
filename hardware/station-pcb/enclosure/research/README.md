# Enclosure research (26.10.2026)

Background only. Where these files disagree with `../fusion-spec.md`, the spec wins.

- `2026-10-26-brief.md`: the design brief written from four research tracks (materials, radiation shield, PMS7003 housing, box). Its §8 holds the numbered sources that `../fusion-spec.md` cites as [n].
- `2026-10-26-check.json`: an adversarial check of 25 numbers in the brief: 8 confirmed, 14 corrected, 2 unsupported, 1 refuted. Each entry has the statement, the verdict, the fix and the evidence.

What the brief got wrong or no longer holds (all fixed in the spec):
- Mounting: the brief has one V-saddle bracket per module. mobric chose the common foot instead (decision 1A, 27.10.2026).
- Siting: the brief keeps the BME680 Cat5e under 1 m, so the shield hangs under the box at 1.6 m and the box sits at 1.9 m. The number check showed that this puts the shield under the box's drip line. mobric chose a 1.5–2 m cable with the shield at least 0.5 m from the box (decision 2A).
- Panel shade: the brief counted on the panel shading the box. The number check showed that it doesn't at the brief's heights, so the spec no longer counts on it.
- Printer: the brief assumed a P1S. mobric's printer is a Bambu Lab P2S.
- The 14 corrected numbers are listed in `../fusion-spec.md` §10.
