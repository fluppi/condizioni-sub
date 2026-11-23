"""Scarica da Copernicus Marine i profili di temperatura (0-100 m) per i siti di mare
e li salva in data/temperatura.json, letto dalla web app.
Credenziali dalle variabili d'ambiente (GitHub Secrets):
COPERNICUSMARINE_SERVICE_USERNAME / COPERNICUSMARINE_SERVICE_PASSWORD
"""
import datetime as dt
import json
import os

import copernicusmarine as cm
import numpy as np

# Nome identico a quello usato nella pagina, lat, lon
SPOTS = [
    ("Cavalaire-sur-Mer", 43.170, 6.535),
    ("Lavagna", 44.296, 9.335),
    ("Santa Margherita Ligure", 44.328, 9.218),
]
DATASET = "cmems_mod_med_phy-tem_anfc_4.2km_P1D-m"   # Mediterraneo, temperatura giornaliera 3D
DEPTHS = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
MAX_DEPTH = 120                                      # metri scaricati dal modello
BOX = 0.12                                           # gradi attorno al sito (~13 km) per trovare un punto di mare profondo

user = os.environ["COPERNICUSMARINE_SERVICE_USERNAME"]
pw = os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"]
today = dt.date.today()
start = (today - dt.timedelta(days=1)).isoformat() + "T00:00:00"
end = (today + dt.timedelta(days=9)).isoformat() + "T23:59:59"

out = {
    "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
    "source": "Copernicus Marine MEDSEA_ANALYSISFORECAST_PHY_006_013",
    "spots": {},
}

for name, lat, lon in SPOTS:
    try:
        ds = cm.open_dataset(
            dataset_id=DATASET, username=user, password=pw, variables=["thetao"],
            minimum_longitude=lon - BOX, maximum_longitude=lon + BOX,
            minimum_latitude=lat - BOX, maximum_latitude=lat + BOX,
            minimum_depth=0, maximum_depth=MAX_DEPTH,
            start_datetime=start, end_datetime=end,
        )
        t = ds["thetao"].transpose("time", "depth", "latitude", "longitude").load()
    except Exception as e:  # un sito che fallisce non blocca gli altri
        print(f"{name}: errore {e}")
        continue

    z = t["depth"].values
    first = t.isel(time=0).values            # (depth, lat, lon)
    cells = []
    for i, la in enumerate(t["latitude"].values):
        for j, lo in enumerate(t["longitude"].values):
            col = first[:, i, j]
            valid = np.where(~np.isnan(col))[0]
            if not len(valid):
                continue                     # cella di terra
            max_d = float(z[valid[-1]])
            dist = (la - lat) ** 2 + ((lo - lon) * np.cos(np.radians(lat))) ** 2
            cells.append((dist, max_d, i, j, float(la), float(lo)))
    if not cells:
        print(f"{name}: nessun punto di mare nel riquadro")
        continue
    # il punto più vicino con almeno 100 m d'acqua; se non c'è, il più profondo (a parità, il più vicino)
    deep = [c for c in cells if c[1] >= 100]
    best = min(deep) if deep else min(cells, key=lambda c: (-c[1], c[0]))
    _, max_d, i, j, la, lo = best

    days = []
    for k, tm in enumerate(t["time"].values):
        col = t.isel(time=k).values[:, i, j]
        ok = ~np.isnan(col)
        zz, cc = z[ok], col[ok]
        if len(zz) < 2:
            continue
        prof = [[d, round(float(np.interp(d, zz, cc)), 2) if d <= zz[-1] else None] for d in DEPTHS]
        thermo = None
        g = np.diff(cc) / np.diff(zz)        # °C per metro (negativo = si raffredda scendendo)
        m = int(np.argmin(g))
        if g[m] < -0.1:
            thermo = round(float((zz[m] + zz[m + 1]) / 2))
        days.append({
            "date": str(np.datetime_as_string(tm, unit="D")),
            "profile": prof,
            "thermocline": thermo,
        })
    # fondale del punto modello: None se più profondo dell’intervallo scaricato
    out["spots"][name] = {"lat": la, "lon": lo, "maxDepth": round(max_d) if max_d < z[-1] else None, "days": days}
    print(f"{name}: {len(days)} giorni, punto {la:.3f},{lo:.3f}, fondale modello ~{max_d:.0f} m")

# Mare: trasparenza dell'acqua da satellite (coefficiente KD490 di Copernicus, 1 km o 300 m).
# Da KD490 si ricava una profondità di Secchi stimata: Zsd ≈ 0,87 / KD490.
sea_dbg = {"errors": []}
KD_DATASETS = ["cmems_obs-oc_med_bgc-transp_nrt_l3-multi-1km_P1D", "cmems_obs-oc_med_bgc-transp_nrt_l3-olci-300m_P1D"]
kd_start = (today - dt.timedelta(days=10)).isoformat() + "T00:00:00"
kd_end = today.isoformat() + "T23:59:59"
for name, lat, lon in SPOTS:
    rows, used = [], None
    for ds_id in KD_DATASETS:
        try:
            ds = cm.open_dataset(
                dataset_id=ds_id, username=user, password=pw, variables=["KD490"],
                minimum_longitude=lon - 0.05, maximum_longitude=lon + 0.05,
                minimum_latitude=lat - 0.05, maximum_latitude=lat + 0.05,
                start_datetime=kd_start, end_datetime=kd_end,
            )
            kd = ds["KD490"].load()
            for k, tm in enumerate(kd["time"].values):
                v = np.asarray(kd.isel(time=k).values, dtype=float).ravel()
                v = v[np.isfinite(v)]
                v = v[(v > 0.01) & (v < 2)]
                if v.size >= 3:                          # almeno 3 pixel d'acqua validi attorno al sito
                    med = float(np.median(v))
                    rows.append({"date": str(np.datetime_as_string(tm, unit="D")), "v": round(0.87 / med, 1),
                                 "kd": round(med, 4), "n": int(v.size), "sat": "copernicus", "est": True})
            if rows:
                used = ds_id
                break
        except Exception as e:  # noqa: BLE001
            sea_dbg["errors"].append(f"KD490 {name} ({ds_id.split('_')[-2]}): {type(e).__name__}: {str(e)[:140]}")
    rows.sort(key=lambda r: r["date"], reverse=True)
    out["spots"].setdefault(name, {"lat": lat, "lon": lon, "maxDepth": None, "days": []})["secchi"] = rows
    sea_dbg.setdefault("kd", {})[name] = {"dataset": used, "misure": len(rows), "ultima": rows[0] if rows else None}
    print(f"{name}: {len(rows)} misure di trasparenza da satellite")

# Torbidità sottocosta ad alta risoluzione (Sentinel-2, pixel da 100 m): vede i pennacchi dei fiumi
# e l'acqua sporca vicino a riva che il dato a 1 km non distingue. Passa ogni 2-5 giorni, cielo permettendo.
HR_DATASET = "cmems_obs_oc_med_bgc_tur-spm-chl_nrt_l3-hr-mosaic_P1D-m"
for name, lat, lon in SPOTS:
    rows = []
    try:
        ds = cm.open_dataset(
            dataset_id=HR_DATASET, username=user, password=pw, variables=["TUR"],
            minimum_longitude=lon - 0.02, maximum_longitude=lon + 0.02,
            minimum_latitude=lat - 0.02, maximum_latitude=lat + 0.02,
            start_datetime=kd_start, end_datetime=kd_end,
        )
        tur = ds["TUR"].load()
        for k, tm in enumerate(tur["time"].values):
            v = np.asarray(tur.isel(time=k).values, dtype=float).ravel()
            v = v[np.isfinite(v)]
            v = v[(v >= 0) & (v < 200)]
            if v.size >= 20:                             # almeno 20 pixel d'acqua validi (0,2 km²)
                rows.append({"date": str(np.datetime_as_string(tm, unit="D")), "tur": round(float(np.median(v)), 2),
                             "p90": round(float(np.percentile(v, 90)), 2), "n": int(v.size)})
    except Exception as e:  # noqa: BLE001
        sea_dbg["errors"].append(f"torbidità {name}: {type(e).__name__}: {str(e)[:140]}")
    rows.sort(key=lambda r: r["date"], reverse=True)
    out["spots"].setdefault(name, {"lat": lat, "lon": lon, "maxDepth": None, "days": []})["turb"] = rows
    sea_dbg.setdefault("tur", {})[name] = {"misure": len(rows), "ultima": rows[0] if rows else None}
    print(f"{name}: {len(rows)} misure di torbidità sottocosta")
out["seaDebug"] = sea_dbg

# Lago di Garda: profili e trasparenza da Alplakes (non blocca mai l'aggiornamento del mare)
try:
    import lago
    extra = lago.collect()
    out["spots"].update(extra.get("spots", {}))
    out["lake"] = extra.get("lake", {})
    out["lakeDebug"] = extra.get("debug", {})
except Exception as e:  # noqa: BLE001
    out["lakeDebug"] = {"errors": [f"lago.py: {type(e).__name__}: {e}"]}

if not out["spots"]:
    raise SystemExit("Nessun dato scaricato: controlla le credenziali Copernicus")

os.makedirs("data", exist_ok=True)
with open("data/temperatura.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
