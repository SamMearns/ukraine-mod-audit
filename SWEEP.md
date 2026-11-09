# Monthly sweep checklist

Run on the 1st of each month. Goal: bring every dataset up to the end of the previous month, re-check every finding, publish.

## Sourcing rules (non-negotiable)

- The Ukrainian General Staff series and Ukrainian officials' statements are the **subject under test**. Every other input must come from outside Ukraine.
- Do not use Ukrainian government, General Staff, DeepState or Ukrainian outlets (Kyiv Independent, Kyiv Post, Ukrainska Pravda, Ukrinform, UNN, NV, Euromaidan, Militarnyi) as data sources. DeepState stays as a comparison only.
- If a Ukrainian figure is unavoidable, show it next to a non-Ukrainian figure.
- **Exclude** purported Russian data whose provenance runs through Ukrainian intelligence (e.g. HUR-released "Kremlin" documents).
- **Exclude** The Economist's casualty model in all forms.
- **Hold** the leaked Rosstat register (rosstat-leaks.com) until the raw data is available to verify; do not add its figures from summaries.
- Every new figure needs a URL where it was seen. Never estimate a missing month.

## 1. Automatic data

```bash
.venv/bin/python build.py
```

Fetches the General Staff series, Open-Meteo weather and DeepState flows, and rebuilds `docs/`.

## 2. Hand-maintained data (`data/static/`)

| File | Add |
|---|---|
| `isw.csv` | Last month's Russian net gain from AFP's monthly ISW analysis (France 24, Moscow Times, Euronews, Al Jazeera, Barron's). Note gross/net. |
| `camps.json` | New dated estimates of Russian losses: Mediazona/BBC named count, Mediazona/Meduza probate releases, CSIS, UK/US/NATO, IISS, Russian official or budget figures. Fields: camp, source, date, fig, counted (cas/dead), what, url, floor, via_ua. |
| `oryx.csv` | Append Oryx's Russian totals (tanks, the armoured-combat-vehicles line, self-propelled + towed artillery + rocket launchers) from https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html for the 1st of the month. |
| `lostarmour_monthly.csv` | Re-collect the last six months from lostarmour.info (armour, mraps, auto, artd, mdst lists filtered by date; read the 'Всего' total), since recent months fill in late. Also update `oryx_ua.json` from Oryx's Ukrainian losses page. |
| `armour_notes.json` | Update the Armour vs Manpower rises-and-dips cards and standout findings if last month moved a series by 40% or more, or new non-Ukrainian research appears. Update the claimed-vs-verified yearly table in `template.html`. |
| `battles.csv` | Battles or truces whose peak phase ended last month (dates from ISW, wires, Meduza). |
| `statements.json` | New Ukrainian officials' figures for a battle or period; new Ministry of Defence drone-series months. |
| `eras.json` | Only if outside sources report a clear change in the weapon mix. |

Also check for new Russian recruitment figures (Medvedev, Kluge, iStories, CSIS) and Putin statements on force size; update the recruitment chart data in `template.html` if they change.

## 3. Re-check the findings

Rebuild, then compare each test against its written verdict in `template.html`. Update any number quoted in the text, and rewrite a verdict or move a key judgement on the probability yardstick only if the evidence has shifted. If text changed, set `#reviewed` in the footer to today's date.

## 4. Publish

```bash
.venv/bin/python build.py --offline
git add -A && git commit -m "Monthly sweep: data to <date>" && git push
```

Then republish `docs/artifact.html` (with `img/strike-frame-1.jpg` and `img/strike-frame-2.jpg`) to the Claude artifact https://claude.ai/artifact/F3TZfp2Z7zRK2W5F3PsmTv so the organisation link stays in sync.

## 5. Changelog

Append a short entry to `CHANGELOG.md`: data window, files changed, findings that moved.
