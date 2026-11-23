"""Confronto tra visibilità misurata dai sub (Project Baseline) e Secchi da satellite (Alplakes, Sentinel-3)."""
import datetime as dt, json, statistics as st, sys

NAMES = {"Q6": "Riva", "155": "Torbole", "Q5": "Salò", "Q8": "Manerba", "Q7": "Torri"}
ts = json.load(open("ts_all.json"))
lake = [x for x in json.load(open("s3_zsd.json")) if x.get("p") and x["vp"] / x["p"] > 0.2 and 0.3 < x["mean"] < 40]
lake = [(dt.date(int(x["dt"][:4]), int(x["dt"][4:6]), int(x["dt"][6:8])), x["mean"]) for x in lake]
D = lambda s: dt.date.fromisoformat(s[:10])

def nearest(rows, day, maxd):
    """valore più vicino al giorno entro maxd giorni; a parità preferisce quello prima."""
    best = None
    for d, v in rows:
        k = abs((d - day).days)
        if k <= maxd and (best is None or k < best[0]):
            best = (k, v, d)
    return best

pairs = []
for stn, name in NAMES.items():
    vis = json.load(open(f"st_{stn}.json"))["visibility"]
    temp = json.load(open(f"st_{stn}.json")).get("temperature") or {}
    pt = [(D(r["t"]), r["v"]) for r in ts[stn] if 0.3 < r["v"] < 40 and (r["n"] or 0) >= 3]
    for depth, rows in vis.items():
        trows = {r["time"]: float(r["value"]) for r in temp.get(depth, [])}
        byday = {}
        for r in rows:
            byday.setdefault(D(r["time"]), []).append(float(r["value"]))
        for day, vals in sorted(byday.items()):
            v = st.mean(vals)
            p = nearest(pt, day, 5)
            l = nearest(lake, day, 5)
            pairs.append({"st": name, "day": day, "depth": int(depth), "vis": v,
                          "pt": p[1] if p else None, "ptAge": p[0] if p else None,
                          "lake": l[1] if l else None, "lakeAge": l[0] if l else None})

def q(a, f):
    a = sorted(a); i = f * (len(a) - 1); lo = int(i); hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (i - lo)

def summary(label, rows, key):
    rs = [r["vis"] / r[key] for r in rows if r[key]]
    if len(rs) < 3:
        print(f"{label:<28} n={len(rs)}"); return
    print(f"{label:<28} n={len(rs):>3}  mediana {st.median(rs):.2f}  q25 {q(rs,.25):.2f}  q75 {q(rs,.75):.2f}  min {min(rs):.2f}  max {max(rs):.2f}")

print("misure totali", len(pairs), "| con Secchi puntuale", sum(1 for r in pairs if r["pt"]), "| con Secchi lago", sum(1 for r in pairs if r["lake"]))
print("\n-- visibilità / Secchi puntuale (±5 giorni)")
summary("tutte", pairs, "pt")
for n in NAMES.values(): summary(n, [r for r in pairs if r["st"] == n], "pt")
season = lambda d: "inverno (dic-mar)" if d.month in (12, 1, 2, 3) else "primavera (apr-giu)" if d.month in (4, 5, 6) else "estate-autunno (lug-nov)"
for s in ("inverno (dic-mar)", "primavera (apr-giu)", "estate-autunno (lug-nov)"): summary(s, [r for r in pairs if season(r["day"]) == s], "pt")
summary("solo misura entro 2 giorni", [r for r in pairs if r["ptAge"] is not None and r["ptAge"] <= 2], "pt")
print("\n-- visibilità / Secchi medio del lago (±5 giorni)")
summary("tutte", pairs, "lake")
for s in ("inverno (dic-mar)", "primavera (apr-giu)", "estate-autunno (lug-nov)"): summary(s, [r for r in pairs if season(r["day"]) == s], "lake")

# correlazione e retta per l'origine
def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    sx = sum((a - mx) ** 2 for a in x) ** .5; sy = sum((b - my) ** 2 for b in y) ** .5
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
for key in ("pt", "lake"):
    xs = [r[key] for r in pairs if r[key]]; ys = [r["vis"] for r in pairs if r[key]]
    k = sum(a * b for a, b in zip(xs, ys)) / sum(a * a for a in xs)
    for kk in (0.75, round(st.median([b / a for a, b in zip(xs, ys)]), 2), 1.0):
        err = [abs(kk * a - b) for a, b in zip(xs, ys)]
        print(f"{key}: k={kk:.2f} errore assoluto mediano {st.median(err):.1f} m, medio {st.mean(err):.1f} m")
    print(f"{key}: correlazione {corr(xs, ys):.2f}, retta per l'origine k={k:.2f}, Secchi medio {st.mean(xs):.1f}, vis media {st.mean(ys):.1f}")
    # stima attuale con tetto min(30, 1.6*base)
print("\n-- visibilità vista per stagione (m): mediana, q25-q75")
for s in ("inverno (dic-mar)", "primavera (apr-giu)", "estate-autunno (lug-nov)"):
    v = [r["vis"] for r in pairs if season(r["day"]) == s]
    print(f"{s:<26} n={len(v):>3} mediana {st.median(v):.1f}  {q(v,.25):.1f}-{q(v,.75):.1f}")
for n in NAMES.values():
    v = [r["vis"] for r in pairs if r["st"] == n]
    print(f"{n:<10} n={len(v):>3} mediana {st.median(v):.1f}  {q(v,.25):.1f}-{q(v,.75):.1f}  profondità {sorted(set(r['depth'] for r in pairs if r['st']==n))}")
if len(sys.argv) > 1:
    for r in sorted(pairs, key=lambda r: r["day"]):
        if r["pt"] or r["lake"]:
            print(r["day"], f"{r['st']:<8}", f"vis {r['vis']:>5.1f}", f"pt {r['pt'] or 0:>5.1f} ({r['ptAge']})", f"lago {r['lake'] or 0:>5.1f} ({r['lakeAge']})")

# ---- confronto tra modelli (Secchi puntuale)
import math
P = [r for r in pairs if r["pt"]]
S = [r["pt"] for r in P]; V = [r["vis"] for r in P]
def score(name, f):
    e = [f(r) - r["vis"] for r in P]
    rel = [abs(f(r) - r["vis"]) / r["vis"] for r in P]
    inside = sum(1 for r in P if f(r) * 0.8 <= r["vis"] <= f(r) * 1.15) / len(P)
    print(f"{name:<44} err.ass. mediano {st.median([abs(x) for x in e]):.2f}  medio {st.mean([abs(x) for x in e]):.2f}  bias {st.mean(e):+.2f}  err.rel. mediano {st.median(rel):.0%}  dentro forchetta -20/+15%: {inside:.0%}")
n = len(S); mx, my = st.mean(S), st.mean(V)
b = sum((a - mx) * (c - my) for a, c in zip(S, V)) / sum((a - mx) ** 2 for a in S); a0 = my - b * mx
lx = [math.log(x) for x in S]; ly = [math.log(y) for y in V]; mlx, mly = st.mean(lx), st.mean(ly)
p = sum((a - mlx) * (c - mly) for a, c in zip(lx, ly)) / sum((a - mlx) ** 2 for a in lx); c0 = math.exp(mly - p * mlx)
print(f"\nretta: vis = {a0:.2f} + {b:.2f}·Secchi   potenza: vis = {c0:.2f}·Secchi^{p:.2f}")
winter = lambda r: r["day"].month in (12, 1, 2, 3)
score("attuale 0,75·S", lambda r: 0.75 * r["pt"])
score("attuale 0,75·S con tetto 16 m", lambda r: min(0.75 * r["pt"], 16))
score("0,84·S", lambda r: 0.84 * r["pt"])
score(f"retta {a0:.1f}+{b:.2f}·S", lambda r: a0 + b * r["pt"])
score(f"potenza {c0:.2f}·S^{p:.2f}", lambda r: c0 * r["pt"] ** p)
score("stagionale 0,61 inverno / 0,93 resto", lambda r: (0.61 if winter(r) else 0.93) * r["pt"])
for cap in (12, 13, 14, 15):
    score(f"0,90·S con tetto {cap} m", lambda r, cap=cap: min(0.90 * r["pt"], cap))
score("senza satellite: mediana stagionale", lambda r: 12.3 if winter(r) else 8.0 if r["day"].month in (4,5,6) else 7.0)
print("\nSecchi puntuale per stagione:", {s: round(st.median([r['pt'] for r in P if season(r['day'])==s]),1) for s in ("inverno (dic-mar)", "primavera (apr-giu)", "estate-autunno (lug-nov)")})
print("mesi delle misure:", sorted({r['day'].month for r in pairs}))

print("\n-- modello scelto: min(0,90·S, 14)")
M = lambda r: min(0.90 * r["pt"], 14)
rat = [r["vis"] / M(r) for r in P]
print("visto/stimato: q10 %.2f q17 %.2f q20 %.2f q25 %.2f mediana %.2f q75 %.2f q80 %.2f q83 %.2f q90 %.2f" % tuple(q(rat, f) for f in (.1, .17, .2, .25, .5, .75, .8, .83, .9)))
for lo, hi in ((0.8, 1.15), (0.75, 1.25), (0.7, 1.3), (0.75, 1.3)):
    print(f"forchetta {lo}-{hi}: dentro {sum(1 for x in rat if lo <= x <= hi)/len(rat):.0%}")
for n_ in NAMES.values():
    rows = [r for r in P if r["st"] == n_]
    e = [abs(M(r) - r["vis"]) for r in rows]; bias = st.mean([M(r) - r["vis"] for r in rows])
    w = [r["vis"] for r in pairs if r["st"] == n_ and winter(r)]
    print(f"{n_:<8} n={len(rows):>2} err.mediano {st.median(e):.2f} bias {bias:+.2f} | visto in inverno: mediana {st.median(w):.1f} max {max(w):.1f} | visto max assoluto {max(r['vis'] for r in pairs if r['st']==n_):.1f}")
sal = [r for r in P if r["st"] == "Salò"]
for cap in (11.2, 12, 14):
    print(f"Salò con tetto {cap}: err.mediano {st.median([abs(min(0.9*r['pt'],cap)-r['vis']) for r in sal]):.2f} bias {st.mean([min(0.9*r['pt'],cap)-r['vis'] for r in sal]):+.2f}")
# stabilità: metà anni pari / dispari
for lab, sel_ in (("anni pari", lambda r: r["day"].year % 2 == 0), ("anni dispari", lambda r: r["day"].year % 2 == 1)):
    rows = [r for r in P if sel_(r)]
    print(lab, len(rows), "0,75·S: %.2f" % st.median([abs(0.75*r['pt']-r['vis']) for r in rows]), "| min(0,9·S,14): %.2f" % st.median([abs(M(r)-r['vis']) for r in rows]), "| mediana visto/Secchi sotto 12 m: %.2f" % st.median([r['vis']/r['pt'] for r in rows if r['pt'] < 12]))
