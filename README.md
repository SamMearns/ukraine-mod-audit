# Ukraine MOD Claims Audit

Ten statistical tests of the Russian-loss figure published daily by Ukraine's General Staff, using only data from outside Ukraine (ISW, Mediazona, Meduza, CSIS, Open-Meteo, Russian recruitment and budget data).

The live page is served by GitHub Pages from `docs/`.

## Build

```bash
python3 -m venv .venv && .venv/bin/pip install pandas numpy scipy certifi
.venv/bin/python build.py            # fetch live sources and rebuild
.venv/bin/python build.py --offline  # rebuild from data/raw only
```

## Layout

- `build.py`: fetches sources, computes every chart's data, writes `docs/index.html`
- `template.html`: page markup, styles and chart code; `/*__DATA__*/` is replaced at build time
- `data/raw/`: fetched sources, committed so each month's inputs are auditable
- `data/static/`: hand-maintained inputs (ISW territory, battles, statements, source estimates, firepower periods)
- `SWEEP.md`: the monthly update checklist and sourcing rules
- `CHANGELOG.md`: what changed each month
