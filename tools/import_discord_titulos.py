#!/usr/bin/env python3
"""Importa productos de un foro de Discord a partir de:
  data/raw/<canal>.tsv          -> thread_id \\t titulo del post \\t links (weidian:ID,taobao:ID,short:...)
  data/raw/<canal>_titulos.txt  -> thread_id|titulo|marca|categoria|tipo|color   ('-' = descartar)
Solo carga productos con link de Weidian (foto y precio reales), de marcas de tools/curate.py.

Uso: python3 tools/import_discord_titulos.py argenbuy_qc [--apply]
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from curate import KEEP_L, norm_brand  # noqa: E402
from import_discord import price_from_text, resolve_short  # noqa: E402
from import_weidian import weidian  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "products.json"


def main(canal, apply):
    links, post = {}, {}
    for line in (RAW / f"{canal}.tsv").read_text("utf-8").splitlines():
        p = line.split("\t")
        if len(p) >= 3:
            links[p[0]] = [x for x in p[2].split(",") if x]
            post[p[0]] = p[1]
    titles = {}
    for line in (RAW / f"{canal}_titulos.txt").read_text("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            p = line.split("|")
            titles[p[0]] = None if p[1] == "-" else p[1:6]
    pf = RAW / f"{canal}_precios.json"   # precios encontrados a mano en las respuestas (¥)
    manual_price = json.loads(pf.read_text("utf-8")) if pf.exists() else {}
    data = json.loads(DATA.read_text("utf-8"))
    by_url = {p["url"]: p for p in data["products"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = dup = skip = 0
    for tid, meta in titles.items():
        if not meta:
            continue
        title, brand, cat, ptype, color = (meta + [""] * 5)[:5]
        brand = norm_brand(brand)
        if brand.lower() not in KEEP_L:
            skip += 1
            continue
        wid, other = None, None
        for k in links.get(tid, []):
            if k.startswith("short:"):
                k = resolve_short(k[6:]) or ""
            if k.startswith("weidian:"):
                wid = k.split(":")[1]
                break
            if k.split(":")[0] in ("taobao", "1688") and not other:
                other = k
        if not wid:
            # Taobao / 1688: precio de la publicación (fijo) y foto QC como portada
            qc_dir = ROOT / "img" / "qc" / f"ab{tid}"
            price = manual_price.get(tid) or price_from_text(post.get(tid, ""))
            qc = sorted(f"img/qc/ab{tid}/{f.name}" for f in qc_dir.glob("*.webp")) if qc_dir.exists() else []
            if not other:
                skip += 1
                continue
            plat, iid = other.split(":")
            url = f"https://item.taobao.com/item.htm?id={iid}" if plat == "taobao" else f"https://detail.1688.com/offer/{iid}.html"
            if url in by_url:
                dup += 1
                continue
            p = {"id": f"dc-{canal}-{tid}", "title": title, "brand": brand, "category": cat, "type": ptype, "color": color,
                 "tags": ["qc discord"], "image": "", "qc": qc, "source": plat, "url": url,
                 "price_cny": round(price, 2) if price else 0, "price_cny_max": None, "price_checked": now,
                 "price_fixed": True, "price_ask": not price, "added": now[:10]}
            data["products"].append(p)
            by_url[url] = p
            added += 1
            continue
        url = f"https://weidian.com/item.html?itemID={wid}"
        if url in by_url:
            dup += 1
            continue
        res = weidian(wid)
        if not res or res.get("offlineItem") or not res.get("itemMainPic"):
            skip += 1
            continue
        low = (res.get("itemDiscountLowPrice") or res.get("itemOriginalLowPrice") or 0) / 100
        high = (res.get("itemDiscountHighPrice") or res.get("itemOriginalHighPrice") or 0) / 100
        if low <= 0:
            skip += 1
            continue
        p = {"id": f"dc-{canal}-{tid}", "title": title, "brand": brand, "category": cat, "type": ptype, "color": color,
             "tags": ["qc discord"], "image": res["itemMainPic"].split("?")[0] + "?w=480&h=480&cp=1", "qc": [],
             "source": "weidian", "url": url, "price_cny": round(low, 2), "price_cny_max": round(high, 2) if high > low else None,
             "price_checked": now, "added": now[:10]}
        data["products"].append(p)
        by_url[url] = p
        added += 1
    print(f"{canal}: {added} nuevos, {dup} ya estaban, {skip} sin link de Weidian / sin precio / marca no reconocida")
    if apply:
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
        print("Guardado. Total:", len(data["products"]))


if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv)
