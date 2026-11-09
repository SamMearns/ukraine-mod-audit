#!/usr/bin/env python3
"""Rebuild the Ukraine MOD Claims Audit page.

Fetches the live sources (Ukrainian General Staff series, Open-Meteo weather,
DeepState comparison flows), recomputes every chart's data, and writes the page
to docs/index.html for GitHub Pages. Hand-maintained inputs live in data/static/.

Usage: .venv/bin/python build.py [--offline]
"""
import calendar
import datetime as dt
import json
import pathlib
import shutil
import ssl
import sys
import urllib.request

import certifi

import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent
RAW, STATIC, OUT = ROOT / "data" / "raw", ROOT / "data" / "static", ROOT / "docs"

PERSONNEL_URL = "https://raw.githubusercontent.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset/main/data/russia_losses_personnel.json"
DEEPSTATE_URL = "https://visua.no/data/deepstate-gross-flows.csv"
TOWNS = {"pokrovsk": (48.28, 37.18), "bakhmut": (48.60, 38.00), "kupiansk": (49.71, 37.62),
         "orikhiv": (47.57, 35.79), "kherson": (46.64, 32.62)}


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "ukraine-mod-audit/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=ssl.create_default_context(cafile=certifi.where())) as r:
        path.write_bytes(r.read())


def fetch_all():
    RAW.mkdir(parents=True, exist_ok=True)
    fetch(PERSONNEL_URL, RAW / "personnel.json")
    fetch(DEEPSTATE_URL, RAW / "deepstate.csv")
    end = (dt.date.today() - dt.timedelta(days=3)).isoformat()
    for name, (lat, lon) in TOWNS.items():
        fetch(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
              f"&start_date=2022-02-24&end_date={end}&daily=temperature_2m_mean,precipitation_sum,"
              f"snowfall_sum,cloud_cover_mean,wind_speed_10m_max&timezone=Europe%2FKyiv", RAW / f"wx_{name}.json")


def season(m):
    return {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
            6: "Summer", 7: "Summer", 8: "Summer"}.get(m, "Autumn")


def load_daily():
    s = pd.DataFrame(json.load(open(RAW / "personnel.json")))[["date", "personnel"]]
    s["date"] = pd.to_datetime(s["date"])
    s = s.set_index("date").asfreq("D")
    s["personnel"] = s["personnel"].interpolate()
    s["daily"] = s["personnel"].diff()
    s = s.iloc[1:]
    wx = []
    for name in TOWNS:
        w = pd.DataFrame(json.load(open(RAW / f"wx_{name}.json"))["daily"])
        w["time"] = pd.to_datetime(w["time"])
        wx.append(w.set_index("time"))
    return s.join(sum(wx) / len(wx), how="left")


def weather_bins(a):
    def bins(col, edges, labels):
        c = pd.cut(a[col], edges, labels=labels, right=False)
        g = a.groupby(c, observed=False).rel.agg(["mean", "std", "count"])
        g["ci"] = 1.96 * g["std"] / np.sqrt(g["count"])
        return [[str(i), round(r["mean"] * 100 - 100, 1), round(r.ci * 100, 1), int(r["count"])] for i, r in g.iterrows()]
    w = {
        "precip": bins("precipitation_sum", [0, 0.5, 2, 5, 10, 100], ["Dry (<0.5 mm)", "0.5–2 mm", "2–5 mm", "5–10 mm", "10 mm+"]),
        "snow": bins("snowfall_sum", [0, 0.01, 1, 3, 100], ["No snow", "<1 cm", "1–3 cm", "3 cm+"]),
        "temp": bins("temperature_2m_mean", [-40, -5, 0, 10, 20, 40], ["Below −5°C", "−5 to 0°C", "0–10°C", "10–20°C", "20°C+"]),
        "wind": bins("wind_speed_10m_max", [0, 15, 20, 25, 30, 100], ["<15 km/h", "15–20", "20–25", "25–30", "30 km/h+"]),
    }
    rho = {}
    for col, k in [("precipitation_sum", "precip"), ("snowfall_sum", "snow"), ("temperature_2m_mean", "temp"),
                   ("wind_speed_10m_max", "wind"), ("cloud_cover_mean", "cloud")]:
        x = a[[col, "rel"]].dropna()
        r, p = stats.spearmanr(x[col], x["rel"])
        rho[k] = [round(float(r), 3), float(f"{p:.2g}")]
    w["rho"] = rho
    return w


def battles(daily):
    b = pd.read_csv(STATIC / "battles.csv", parse_dates=["peak_start", "peak_end"])
    ref = daily["2022-06-01":].values
    out = []
    for _, r in b.iterrows():
        w = daily[r.peak_start:r.peak_end]
        pre = daily[r.peak_start - pd.Timedelta(days=42):r.peak_start - pd.Timedelta(days=1)]
        post = daily[r.peak_end + pd.Timedelta(days=1):r.peak_end + pd.Timedelta(days=14)]
        if not len(w) or not len(pre):
            continue
        out.append(dict(id=r.id, name=r["name"], side=r.side, kind=r.kind, ps=r.peak_start.strftime("%Y-%m-%d"),
                        pe=r.peak_end.strftime("%Y-%m-%d"), days=len(w), win=round(w.mean()), pre=round(pre.mean()),
                        chg=round((w.mean() / pre.mean() - 1) * 100, 1), post=round(post.mean()) if len(post) else None, url=r.url))
    bands = {}
    for L in sorted({o["days"] for o in out}):
        v = np.array([ref[i:i + L].mean() / ref[i - 42:i].mean() - 1 for i in range(42, len(ref) - L)]) * 100
        bands[L] = [round(float(np.percentile(v, 10)), 1), round(float(np.percentile(v, 90)), 1)]
        for o in out:
            if o["days"] == L:
                o["pct"] = round(float((v < o["chg"]).mean() * 100))
    return out, bands


def main():
    if "--offline" not in sys.argv:
        fetch_all()
    s = load_daily()
    asof = s.index[-1]
    daily = s.daily

    # Daily series and 30-day average
    r30 = daily.rolling(30, min_periods=1).mean()
    data = {"asof": asof.strftime("%Y-%m-%d"), "total": int(s.personnel.iloc[-1]),
            "daily": [[d.strftime("%Y-%m-%d"), int(v), round(r)] for d, v, r in zip(s.index, daily, r30)]}

    # Seasons
    s["season"] = s.index.month.map(season)
    s["sy"] = np.where(s.index.month == 12, s.index.year + 1, s.index.year)
    st = s.groupby(["sy", "season"]).daily.agg(["mean", "std", "count"])
    data["seasons"] = [[int(y), se, round(r["mean"]), round(r["std"] / r["mean"], 3), int(r["count"])] for (y, se), r in st.iterrows()]

    # Weather (2023 onward, each day against its centred 29-day median)
    a = s[s.index >= "2023-01-01"].copy()
    a["rel"] = a.daily / a.daily.rolling(29, center=True, min_periods=15).median()
    data["weather"] = weather_bins(a)

    # Monthly, joined with DeepState comparison flows
    m = daily.resample("MS").agg(["sum", "mean", "std"])
    m["cv"] = m["std"] / m["mean"]
    data["monthly_all"] = [[i.strftime("%Y-%m"), int(r["sum"]), round(r["mean"]), round(r.cv, 3)] for i, r in m.iterrows()]
    ds = pd.read_csv(RAW / "deepstate.csv")
    ds["month"] = pd.to_datetime(ds["month"])
    mm = m.join(ds.set_index("month"), how="inner")
    mm["precip"] = s.precipitation_sum.resample("MS").sum()
    mm["temp"] = s.temperature_2m_mean.resample("MS").mean()
    data["monthly"] = [[i.strftime("%Y-%m"), int(r["sum"]), round(r["mean"]), round(r.cv, 3), round(r.gained_km2, 1),
                        round(r.lost_km2, 1), round(r.precip, 1), round(r.temp, 1)] for i, r in mm.iterrows()]

    # Territory: ISW via AFP (hand-maintained), DeepState net for comparison
    isw = pd.read_csv(STATIC / "isw.csv")
    dsn = {i.strftime("%Y-%m"): r.gained_km2 + r.lost_km2 for i, r in ds.set_index("month").iterrows()}
    data["terr"] = [[r.month, int(r.isw), r.basis, round(dsn[r.month], 1)] for r in isw.itertuples() if r.month in dsn]

    # Battles and truces
    data["battles"], data["bands"] = battles(daily)

    # Officials' statements against General Staff sums
    def gs(x, y):
        return int(daily[x:y].sum())
    sm = json.load(open(STATIC / "statements.json"))
    data["statements"] = {
        "battle": [dict(o, gs=gs(o["a"], o["b"]), share=round(o["fig"] / gs(o["a"], o["b"]) * 100, 1)) for o in sm["battle"]],
        "periodic": [dict(o, gs=gs(o["a"], o["b"]), diff=round((o["fig"] / gs(o["a"], o["b"]) - 1) * 100, 1)) for o in sm["periodic"]],
        "drone": [dict(o, gs=gs(o["a"], o["b"]), share=round(o["drone"] / gs(o["a"], o["b"]) * 100, 1)) for o in sm["drone"]],
    }

    # Firepower periods
    eras = json.load(open(STATIC / "eras.json"))
    for e in eras:
        e["b"] = data["asof"] if e["b"] == "today" else e["b"]
        e["mean"] = round(daily[e["a"]:e["b"]].mean())
    data["eras"] = eras

    # Source cross-reference, with the MOD total on each estimate's date
    cum = s.personnel
    camps = json.load(open(STATIC / "camps.json"))
    for c in camps:
        c["ua"] = int(cum[:c["date"]].iloc[-1])
    data["camps"] = camps

    # 2026 monthly average over complete months, for the recruitment chart
    this_month = asof.strftime("%Y-%m")
    full26 = [r for r in data["monthly_all"] if r[0].startswith("2026") and r[0] != this_month]
    data["recruit26"] = {"avg": round(sum(r[1] for r in full26) / len(full26)), "label": f"Jan–{dt.date(2026, len(full26), 1):%b}"}

    # Figures quoted in the page text, filled into [data-fig] elements at load
    sg = lambda v: ("−" if v < 0 else "+") + f"{abs(v):.2f}"
    x = a[["precipitation_sum", "rel"]].dropna()
    nxt = a.assign(rn=a.rel.shift(-1))[["precipitation_sum", "rn"]].dropna()
    cur = daily[asof.strftime("%Y-%m")]
    days_in = calendar.monthrange(asof.year, asof.month)[1]
    data["figs"] = {
        "ndays": f"{len(daily):,}", "nround": f"{int((daily.astype(int) % 10 == 0).sum()):,}", "nwx": f"{len(x):,}",
        "rho_precip": sg(data["weather"]["rho"]["precip"][0]), "rho_snow": sg(data["weather"]["rho"]["snow"][0]),
        "rho_temp": sg(data["weather"]["rho"]["temp"][0]), "rho_cloud": sg(data["weather"]["rho"]["cloud"][0]),
        "rho_wind": sg(data["weather"]["rho"]["wind"][0]),
        "rho_next": ("−" if stats.spearmanr(nxt.iloc[:, 0], nxt.iloc[:, 1])[0] < 0 else "+") + f"{abs(stats.spearmanr(nxt.iloc[:, 0], nxt.iloc[:, 1])[0]):.3f}",
        "cur_month": asof.strftime("%B"), "cur_span": f"1–{asof.day} {asof:%B}", "cur_sum": f"{int(cur.sum()):,}",
        "cur_rate": f"{cur.mean():,.0f}", "cur_proj": f"{round(cur.mean() * days_in, -3):,.0f}",
        "total_m": f"{data['total'] / 1e6:.1f} million",
    }

    OUT.mkdir(exist_ok=True)
    html = (ROOT / "template.html").read_text().replace("/*__DATA__*/", json.dumps(data))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + html + "</body></html>")
    (OUT / "index.html").write_text(page)
    (OUT / "artifact.html").write_text(html)
    shutil.copytree(ROOT / "img", OUT / "img", dirs_exist_ok=True)
    (OUT / ".nojekyll").write_text("")
    print(f"Built docs/index.html — data to {data['asof']}, total {data['total']:,}")


if __name__ == "__main__":
    main()
