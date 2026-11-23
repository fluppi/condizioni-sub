"""Dati del Lago di Garda da Alplakes (Eawag, CC BY 4.0), richiamato da temperatura.py:
- profili di temperatura dal modello 3D Delft3D-FLOW (previsione a 5 giorni);
- trasparenza dell'acqua (profondità di Secchi) dalle immagini satellitari Sentinel-3 / Sentinel-2.
Ogni passo è protetto: se una chiamata fallisce si salta e l'errore finisce in "lakeDebug".
"""
import datetime as dt
import json
import re
import urllib.request

import numpy as np

API = "https://alplakes-api.eawag.ch"
S3 = "https://eawagrs.s3.eu-central-1.amazonaws.com/alplakes/metadata"
LAKE = "garda"
# Nome del sito (identico alla pagina) e punto al largo usato per profilo e satellite
SPOTS = [
    ("Riva del Garda", 45.855, 10.852),
    ("Salò", 45.600, 10.555),
    ("Assenza", 45.700, 10.740),
    ("Tempesta", 45.835, 10.852),
    ("Campione del Garda", 45.757, 10.770),
]
DEPTHS = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
SECCHI_FALLBACK = {"sentinel3": "Zsd_lee", "sentinel2": "Z490"}   # usati se l'elenco dei parametri non è leggibile


def get(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "condizioni-sub (GitHub Actions)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def profile_from(p):
    """Risposta /simulations/profile -> (profilo alle quote standard, termoclino, fondale del punto)."""
    z = p["depth"]["data"]
    t = p["variables"]["temperature"]["data"]
    pairs = sorted((float(a), float(b)) for a, b in zip(z, t) if a is not None and b is not None)
    if len(pairs) < 2:
        return None
    zz = np.array([a for a, _ in pairs])
    cc = np.array([b for _, b in pairs])
    prof = [[d, round(float(np.interp(d, zz, cc)), 2) if d <= zz[-1] else None] for d in DEPTHS]
    thermo = None
    g = np.diff(cc) / np.maximum(np.diff(zz), 1e-6)     # °C per metro
    m = int(np.argmin(g))
    if g[m] < -0.1:
        thermo = round(float((zz[m] + zz[m + 1]) / 2))
    max_d = float(zz[-1])
    return prof, thermo, (round(max_d) if max_d < 100 else None)


def collect():
    out = {"spots": {}, "lake": {}, "debug": {"errors": []}}
    dbg = out["debug"]
    today = dt.datetime.now(dt.timezone.utc).date()

    def safe(label, url, timeout=90):
        try:
            return get(url, timeout)
        except Exception as e:  # noqa: BLE001 - vogliamo proseguire comunque
            dbg["errors"].append(f"{label}: {type(e).__name__}: {str(e)[:160]}")
            return None

    # ---- 1) Profili di temperatura dal modello 3D
    meta = safe("metadati modello 3D", f"{API}/simulations/metadata/delft3d-flow/{LAKE}", 40)
    if isinstance(meta, dict):
        dbg["model3d"] = {k: meta.get(k) for k in ("start_date", "end_date")}
    for name, lat, lon in SPOTS:
        days, max_depth = [], None
        for i in range(6):
            d = today + dt.timedelta(days=i)
            p = safe(f"profilo {name} {d}", f"{API}/simulations/profile/delft3d-flow/{LAKE}/{d:%Y%m%d}1200/{lat}/{lon}?variables=temperature", 60)
            if p is None:
                break                                   # oltre la fine della previsione
            try:
                res = profile_from(p)
            except Exception as e:  # noqa: BLE001
                dbg["errors"].append(f"profilo {name} {d}: formato inatteso ({str(e)[:100]})")
                dbg.setdefault("profileSample", json.dumps(p)[:600])
                break
            if res:
                prof, thermo, max_depth = res
                days.append({"date": d.isoformat(), "profile": prof, "thermocline": thermo})
        out["spots"][name] = {"lat": lat, "lon": lon, "maxDepth": max_depth, "days": days, "lake": True, "secchi": []}
        print(f"{name}: {len(days)} giorni di profilo dal modello Alplakes")

    # ---- 2) Trasparenza (Secchi) da satellite
    summary = safe("elenco prodotti satellitari", f"{S3}/summary.json", 40)
    lake_params = summary.get(LAKE, {}) if isinstance(summary, dict) else {}
    dbg["satParams"] = lake_params if lake_params else "non disponibile"
    start = today - dt.timedelta(days=14)
    out["lake"]["secchi"] = {}
    for sat in ("sentinel3", "sentinel2"):
        params = lake_params.get(sat, []) if isinstance(lake_params, dict) else []
        par = next((x for x in params if re.search(r"zsd|z490|secchi", x, re.I)), None) or SECCHI_FALLBACK[sat]
        entry = {"param": par, "lake": []}
        stats = safe(f"statistiche {sat}/{par}", f"{S3}/{sat}/{LAKE}/{par}.json", 40)
        if isinstance(stats, list):
            for s in stats:
                try:
                    day = dt.datetime.strptime(s["dt"][:8], "%Y%m%d").date()
                    cover = s["vp"] / s["p"] if s.get("p") else 0
                    if (today - day).days <= 30 and cover > 0.2 and 0.3 < s["mean"] < 40:
                        entry["lake"].append({"date": day.isoformat(), "mean": round(s["mean"], 1), "p10": round(s["p10"], 1),
                                              "p90": round(s["p90"], 1), "cover": round(cover, 2)})
                except Exception:  # noqa: BLE001
                    continue
            entry["lake"].sort(key=lambda x: x["date"], reverse=True)
        out["lake"]["secchi"][sat] = entry
        if sat != "sentinel3":
            continue                                    # serie puntuale solo da Sentinel-3 (passa quasi ogni giorno)
        for name, lat, lon in SPOTS:
            ts = safe(f"Secchi {name}", f"{API}/remotesensing/timeseries/{LAKE}/{sat}/{par}/{lat}/{lon}/{start:%Y%m%d}/{today:%Y%m%d}?window=2", 120)
            if not isinstance(ts, list):
                continue
            for e in ts:
                try:
                    v = e["value"]
                    val = v["median"] if isinstance(v, dict) else float(v)
                    if 0.3 < val < 40:
                        out["spots"][name]["secchi"].append({"date": str(e["time"])[:10], "v": round(val, 1),
                                                             "n": v.get("count") if isinstance(v, dict) else None, "sat": sat})
                except Exception:  # noqa: BLE001
                    dbg.setdefault("secchiSample", json.dumps(e)[:300])
            out["spots"][name]["secchi"].sort(key=lambda x: x["date"], reverse=True)
            print(f"{name}: {len(out['spots'][name]['secchi'])} misure Secchi da {sat}")

    # ---- 3) Extra, solo per capire cosa è disponibile
    insitu = safe("Secchi in situ", f"{API}/insitu/secchi/{LAKE}", 40)
    if isinstance(insitu, dict) and "time" in insitu:
        rows = list(zip(insitu["time"], insitu["variable"]["data"]))[-5:]
        out["lake"]["insitu"] = [{"date": str(a)[:10], "v": b} for a, b in rows]
    waves = safe("modelli di onda", f"{API}/simulations/2d/metadata", 40)
    if isinstance(waves, list):
        dbg["waves"] = [{"model": m.get("model"), "lakes": [x.get("name") for x in m.get("lakes", [])]} for m in waves]
    return out
