"""Storico delle misure: una riga per sito, giorno e tipo di misura in data/storico.csv.
Il file giornaliero tiene solo gli ultimi 10 giorni; qui le misure restano, per tarare le stime
confrontandole con le immersioni del diario. Una misura già presente viene aggiornata, non ripetuta.

tipo       valore                              extra
secchi     profondità di Secchi (m)            kd=<KD490> oppure sat=<satellite>
tur        torbidità sottocosta (FNU, mediana) p90=<90° percentile>
secchi_lago media di Secchi sull'intero lago   p10=..;p90=..;cover=..
t5         temperatura a 5 m (°C)              solo per il giorno della corsa
termoclino quota del termoclino (m)            solo per il giorno della corsa
"""
import csv
import datetime as dt
import os

FIELDS = ["data", "sito", "tipo", "valore", "n", "extra"]


def rows_from(out, today=None):
    today = today or dt.date.today().isoformat()
    rows = []
    for name, sp in (out.get("spots") or {}).items():
        for r in sp.get("secchi") or []:
            extra = f"kd={r['kd']}" if r.get("kd") is not None else f"sat={r.get('sat', '')}"
            rows.append([r["date"], name, "secchi", r["v"], r.get("n", ""), extra])
        for r in sp.get("turb") or []:
            rows.append([r["date"], name, "tur", r["tur"], r.get("n", ""), f"p90={r.get('p90', '')}"])
        for d in sp.get("days") or []:
            if d.get("date") != today:
                continue                      # i giorni successivi sono previsione
            t5 = next((t for z, t in d.get("profile") or [] if z == 5), None)
            if t5 is not None:
                rows.append([today, name, "t5", t5, "", ""])
            if d.get("thermocline") is not None:
                rows.append([today, name, "termoclino", d["thermocline"], "", ""])
    lake = (((out.get("lake") or {}).get("secchi") or {}).get("sentinel3") or {}).get("lake") or []
    for r in lake:
        extra = ";".join(f"{k}={r[k]}" for k in ("p10", "p90", "cover") if r.get(k) is not None)
        rows.append([r["date"], "Lago di Garda", "secchi_lago", r["mean"], "", extra])
    return rows


def update(out, path="data/storico.csv", today=None):
    """Aggiunge o aggiorna le misure di `out` nel file; restituisce (righe totali, righe nuove)."""
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                old[(r["data"], r["sito"], r["tipo"])] = [r.get(k, "") for k in FIELDS]
    before = len(old)
    for r in rows_from(out, today):
        old[(r[0], r[1], r[2])] = [str(x) for x in r]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for key in sorted(old):
            w.writerow(old[key])
    return len(old), len(old) - before
