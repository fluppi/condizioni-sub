"""Le misure dei sub (22–28 m) erano sopra o sotto il termoclino? E cambia il rapporto con il Secchi del satellite?"""
import datetime as dt, json, statistics as st, sys

NAMES = {"Q6": "Riva", "155": "Torbole", "Q5": "Salò", "Q8": "Manerba", "Q7": "Torri"}
ts = json.load(open("ts_all.json")); prof = json.load(open("profili.json"))
D = lambda s: dt.date.fromisoformat(s[:10])
def q(a, f):
    a = sorted(a); i = f * (len(a) - 1); lo = int(i); hi = min(lo + 1, len(a) - 1)
    return a[lo] + (a[hi] - a[lo]) * (i - lo)
def nearest(rows, day, maxd):
    best = None
    for d, v in rows:
        k = abs((d - day).days)
        if k <= maxd and (best is None or k < best[0]): best = (k, v)
    return best
def interp(p, z):
    for (a, ta), (b, tb) in zip(p, p[1:]):
        if a <= z <= b: return ta + (tb - ta) * (z - a) / (b - a)
    return None
def layers(p):
    """termoclino (quota del gradiente più forte, se > 0,1 °C/m) e fondo dello strato mescolato (T scesa di 1 °C dalla superficie)"""
    g = [((tb - ta) / (b - a), (a + b) / 2) for (a, ta), (b, tb) in zip(p, p[1:]) if b > a and b <= 100]
    gm = min(g)
    tc = gm[1] if gm[0] < -0.1 else None
    t0 = interp(p, 1.0)
    mld = next((z for z, t in p if t < t0 - 1.0), None)
    return tc, mld, gm[0]

rows = []
for stn, name in NAMES.items():
    js = json.load(open(f"st_{stn}.json"))
    pt = [(D(r["t"]), r["v"]) for r in ts[stn] if 0.3 < r["v"] < 40 and (r["n"] or 0) >= 3]
    for depth, vr in js["visibility"].items():
        tr = {r["time"]: float(r["value"]) for r in (js.get("temperature") or {}).get(depth, [])}
        byday = {}
        for r in vr: byday.setdefault(r["time"][:10], []).append((float(r["value"]), tr.get(r["time"])))
        for day, vals in sorted(byday.items()):
            p = prof.get(stn, {}).get(day)
            if not p: continue
            tc, mld, gmax = layers(p)
            zm = int(depth)
            s = nearest(pt, D(day), 5)
            tsub = [t for _, t in vals if t is not None]
            pos = "mescolato" if mld is None or mld > 60 and tc is None else ("sopra" if zm < (mld or 999) else "sotto")
            rows.append({"st": name, "day": day, "z": zm, "vis": st.mean(v for v, _ in vals), "S": s[1] if s else None,
                         "tc": tc, "mld": mld, "pos": pos, "Tmod": interp(p, zm), "Tsub": st.mean(tsub) if tsub else None, "T1": interp(p, 1.0)})

print("misure dal 2019 con profilo:", len(rows), "| con Secchi:", sum(1 for r in rows if r["S"]))
d = [r["Tmod"] - r["Tsub"] for r in rows if r["Tsub"] is not None]
print(f"modello - termometro dei sub alla quota: mediana {st.median(d):+.1f} °C, |err| mediano {st.median([abs(x) for x in d]):.1f} °C (n={len(d)})")
print("\nposizione della misura rispetto allo strato mescolato:")
for pos in ("mescolato", "sopra", "sotto"):
    g = [r for r in rows if r["pos"] == pos]
    if not g: continue
    v = [r["vis"] for r in g]; rs = [r["vis"] / r["S"] for r in g if r["S"]]; ss = [r["S"] for r in g if r["S"]]
    mesi = sorted({int(r["day"][5:7]) for r in g})
    print(f"  {pos:<10} n={len(g):>2}  vista mediana {st.median(v):>4.1f} m ({q(v,.25):.1f}-{q(v,.75):.1f})  Secchi mediano {st.median(ss) if ss else 0:>4.1f}"
          f"  vista/Secchi {st.median(rs) if rs else 0:.2f} (n={len(rs)})  mesi {mesi}")
print("\nper mese: fondo strato mescolato (m), termoclino (m), vista (m), Secchi (m), rapporto")
for m in range(1, 13):
    g = [r for r in rows if int(r["day"][5:7]) == m]
    if not g: continue
    ml = [r["mld"] for r in g if r["mld"]]; tcs = [r["tc"] for r in g if r["tc"]]; rs = [r["vis"] / r["S"] for r in g if r["S"]]
    print(f"  mese {m:>2} n={len(g):>2}  mescolato fino a {st.median(ml) if ml else float('nan'):>5.1f}  termoclino {st.median(tcs) if tcs else float('nan'):>5.1f}"
          f"  vista {st.median([r['vis'] for r in g]):>4.1f}  Secchi {st.median([r['S'] for r in g if r['S']]) if rs else float('nan'):>4.1f}  rapporto {st.median(rs) if rs else float('nan'):.2f}")
# quanto conta la differenza di temperatura tra superficie e quota del sub
print("\nvista/Secchi secondo il salto di temperatura tra 1 m e la quota del sub:")
for lo, hi in ((-1, 0.5), (0.5, 2), (2, 5), (5, 30)):
    g = [r for r in rows if r["S"] and lo <= r["T1"] - r["Tmod"] < hi]
    if g: print(f"  salto {lo:>4}..{hi:<4} °C n={len(g):>2}  rapporto {st.median([r['vis']/r['S'] for r in g]):.2f}  vista {st.median([r['vis'] for r in g]):.1f}  Secchi {st.median([r['S'] for r in g]):.1f}")
if len(sys.argv) > 1:
    for r in sorted(rows, key=lambda r: r["day"]):
        print(r["day"], f"{r['st']:<8} z{r['z']} vis {r['vis']:>5.1f} S {r['S'] or 0:>5.1f} mld {r['mld'] or 0:>5.1f} tc {r['tc'] or 0:>5.1f} {r['pos']:<9} T1 {r['T1']:.1f} Tz {r['Tmod']:.1f} Tsub {r['Tsub'] if r['Tsub'] is not None else float('nan'):.1f}")
json.dump(rows, open("strati.json", "w"))
