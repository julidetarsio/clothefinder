#!/usr/bin/env python3
"""Para cada fila de data/raw/yupoo_rows.txt (tienda|weidian:ID o ys:CODIGO|titulo del album):
resuelve los links cortos de Weidian (k.youshop10.com) y consulta Weidian (foto, precio, título).
Guarda data/raw/yupoo_weidian.json -> {item_id: {store, album_title, weidian: {...}}}
"""
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_weidian import weidian  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = RAW / "yupoo_weidian.json"


def resolve(code):
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "--max-redirs", "8", "-m", "20",
                          "-w", "%{url_effective}", "https://k.youshop10.com/" + code],
                         capture_output=True, timeout=40).stdout.decode()
    m = re.search(r"itemI[dD]=(\d+)", out)
    return m.group(1) if m else None


def main():
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
    rows = []
    for line in (RAW / "yupoo_rows.txt").read_text("utf-8").splitlines():
        p = line.split("|", 2)
        if len(p) == 3:
            rows.append(p)

    def job(r):
        store, key, title = r
        iid = key.split(":", 1)[1] if key.startswith("weidian:") else resolve(key.split(":", 1)[1])
        if not iid or iid in data:
            return None
        time.sleep(0.3)
        return iid, {"store": store, "album_title": title, "weidian": weidian(iid)}

    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(job, rows):
            if res:
                data[res[0]] = res[1]
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(rows)}", flush=True)
    # se guarda solo lo necesario (no todo el detalle de Weidian)
    slim = {}
    for iid, v in data.items():
        w = v.get("weidian") or {}
        if "itemMainPic" in w or "pic" in w:
            slim[iid] = v
            continue
        slim[iid] = {"store": v["store"], "album_title": v["album_title"], "weidian": {
            k: w.get(k) for k in ("itemMainPic", "itemTitle", "itemDiscountLowPrice", "itemDiscountHighPrice",
                                  "itemOriginalLowPrice", "itemOriginalHighPrice", "offlineItem")} if w else None}
    OUT.write_text(json.dumps(slim, ensure_ascii=False), "utf-8")
    ok = sum(1 for v in slim.values() if v.get("weidian") and v["weidian"].get("itemMainPic") and not v["weidian"].get("offlineItem"))
    print(f"Listo: {len(slim)} productos, {ok} a la venta con foto y precio")


if __name__ == "__main__":
    main()
