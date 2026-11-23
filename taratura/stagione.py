"""Media stagionale della visibilita' dei sub sul Garda e prova: aiuta mescolarla alla stima da satellite?"""
import datetime as dt, json, statistics as st
NAMES = {"Q6": "Riva", "155": "Torbole", "Q5": "Salo", "Q8": "Manerba", "Q7": "Torri"}
ts = json.load(open("ts_all.json"))
D = lambda s: dt.date.fromisoformat(s[:10])
def nearest(rows, day, maxd):
    best = None
    for d, v in rows:
        k = abs((d - day).days)
        if k <= maxd and (best is None or k < best[0]): best = (k, v)
    return best
allm = []
for stn, name in NAMES.items():
    js = json.load(open(f"st_{stn}.json"))
    pt = [(D(r["t"]), r["v"]) for r in ts[stn] if 0.3 < r["v"] < 40 and (r["n"] or 0) >= 3]
    for depth, rows in js["visibility"].items():
        byday = {}
        for r in rows: byday.setdefault(r["time"][:10], []).append(float(r["value"]))
        for day, vals in byday.items():
            s = nearest(pt, D(day), 5)
            allm.append({"st": name, "day": D(day), "vis": st.mean(vals), "S": s[1] if s else None})
print("misure:", len(allm))
tot = st.median([r["vis"] for r in allm])
print("mediana generale %.1f m" % tot)
print("per mese (n, mediana, rapporto con la mediana generale):")
mm = {}
for m in range(1, 13):
    g = [r["vis"] for r in allm if r["day"].month == m]
    if g: mm[m] = st.median(g); print(f"  {m:>2}: n={len(g):>2} {mm[m]:>5.1f} m  x{mm[m]/tot:.2f}")
print("per sito: mediana e rapporto con la mediana generale, dopo aver tolto la stagione")
for n in NAMES.values():
    g = [r["vis"] / mm[r["day"].month] for r in allm if r["st"] == n]
    print(f"  {n:<8} n={len(g):>2} x{st.median(g):.2f}  mediana {st.median([r['vis'] for r in allm if r['st']==n]):.1f}")
# curva per tutti i mesi: interpolazione lineare tra i mesi con misure (ciclica)
known = sorted(mm)
def clim(month, table):
    ks = sorted(table)
    if month in table: return table[month]
    prev = max([k for k in ks if k < month], default=ks[-1] - 12); nxt = min([k for k in ks if k > month], default=ks[0] + 12)
    a = table[prev if prev > 0 else prev + 12]; b = table[nxt if nxt <= 12 else nxt - 12]
    return a + (b - a) * (month - prev) / (nxt - prev)
print("curva mensile (m):", [round(clim(m, mm), 1) for m in range(1, 13)])
print("fattori sul valore tipico:", [round(clim(m, mm) / tot, 2) for m in range(1, 13)])
# prova: stima da satellite min(0,9 S, 14) mescolata con la stagione calcolata SENZA l'anno della misura
P = [r for r in allm if r["S"]]
def season_wo(r):
    t = {}
    for m in range(1, 13):
        g = [x["vis"] for x in allm if x["day"].month == m and x["day"].year != r["day"].year]
        if g: t[m] = st.median(g)
    return clim(r["day"].month, t)
for r in P: r["sea"] = season_wo(r); r["sat"] = min(0.9 * r["S"], 14)
def ev(f):
    e = [f(r) - r["vis"] for r in P]
    return "mediano %.2f medio %.2f bias %+.2f" % (st.median([abs(x) for x in e]), st.mean([abs(x) for x in e]), st.mean(e))
for w in (0, 0.2, 0.3, 0.4, 0.5, 0.7, 1):
    print(f"  peso stagione {w:.1f}: ", ev(lambda r, w=w: (1 - w) * r["sat"] + w * r["sea"]))
print("  freno: satellite limitato a stagione x0,6..x1,6:", ev(lambda r: max(0.6 * r["sea"], min(1.6 * r["sea"], r["sat"]))))
print("  freno: satellite limitato a stagione x0,7..x1,4:", ev(lambda r: max(0.7 * r["sea"], min(1.4 * r["sea"], r["sat"]))))
