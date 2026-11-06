#!/usr/bin/env python3
"""Importa una lista de productos de Weidian a data/products.json.

Entrada: data/raw/latamfinds.json  -> [{cat, platform, id, brand, name}]
Para cada producto consulta Weidian (foto principal, precio actual, si sigue a la venta),
arma el título en español y lo guarda. Los productos que ya no están a la venta se descartan.

Uso: python3 tools/import_weidian.py data/raw/latamfinds.json
"""
import json
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from titles import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "products.json"
CACHE = ROOT / "data" / "raw" / "weidian_cache.json"


def weidian(item_id):
    param = urllib.parse.quote(json.dumps({"itemId": item_id}))
    url = "https://thor.weidian.com/detail/getItemSkuInfo/1.0?param=" + param
    for attempt in range(3):
        try:
            out = subprocess.run(["curl", "-s", "-m", "20", url], capture_output=True, timeout=30).stdout
            j = json.loads(out.decode("utf-8", "ignore"))
            return j.get("result")
        except Exception:
            time.sleep(2 + attempt * 3)
    return None


def main(src):
    rows = json.loads(Path(src).read_text("utf-8"))
    cache = json.loads(CACHE.read_text("utf-8")) if CACHE.exists() else {}
    todo = [r["id"] for r in rows if r["id"] not in cache]
    print(f"{len(rows)} productos, {len(todo)} por consultar en Weidian", flush=True)

    def job(iid):
        time.sleep(0.25)
        return iid, weidian(iid)

    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for iid, res in ex.map(job, todo):
            cache[iid] = res
            done += 1
            if done % 100 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
                print(f"  {done}/{len(todo)}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")

    data = json.loads(DATA.read_text("utf-8"))
    existing = {p["id"]: p for p in data["products"] if not p.get("demo")}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = now[:10]
    added = skipped = 0
    for r in rows:
        res = cache.get(r["id"])
        if not res or res.get("offlineItem") or not res.get("itemMainPic"):
            skipped += 1
            continue
        low = (res.get("itemDiscountLowPrice") or res.get("itemOriginalLowPrice") or 0) / 100
        high = (res.get("itemDiscountHighPrice") or res.get("itemOriginalHighPrice") or 0) / 100
        if low <= 0:
            skipped += 1
            continue
        title, category, ptype, color = build(r["cat"], r["brand"], r["name"])
        pid = "wd-" + r["id"]
        prev = existing.get(pid, {})
        existing[pid] = {
            "id": pid,
            "title": title,
            "brand": r["brand"],
            "category": category,
            "type": ptype,
            "color": color,
            "tags": [r["name"]],
            "image": res["itemMainPic"].split("?")[0] + "?w=480&h=480&cp=1",
            "qc": prev.get("qc", []),
            "source": "weidian",
            "url": f"https://weidian.com/item.html?itemID={r['id']}",
            "price_cny": round(low, 2),
            "price_cny_max": round(high, 2) if high > low else None,
            "price_checked": now,
            "added": prev.get("added", today),
        }
        added += 1
    data["products"] = list(existing.values())
    data["updated"] = now
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"Listo: {added} productos cargados, {skipped} descartados (sin stock o sin datos). Total: {len(data['products'])}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "raw" / "latamfinds.json")
