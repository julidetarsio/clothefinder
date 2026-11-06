#!/usr/bin/env python3
"""Importa productos sacados de foros de Discord (QC / hauls) a data/products.json.

Entradas:
  data/raw/discord_<canal>.json   -> {thread_id: {title, text, links: ["weidian:123", "short:ikako.vip/abc", ...]}}
  data/raw/discord_<canal>_titulos.json -> {thread_id: {title, brand, category, type, color} | null}
      (títulos puestos mirando las fotos; null = no es ropa/zapatillas o no sirve)

Uso: python3 tools/import_discord.py qc
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_weidian import weidian  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "products.json"
USD_TO_CNY = 1 / 0.14


def resolve_short(path):
    """ikako.vip/abc -> link de kakobuy -> link original"""
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "--max-redirs", "6", "-m", "20",
                          "-w", "%{url_effective}", "https://" + path], capture_output=True, timeout=40).stdout.decode()
    m = re.search(r"[?&]url=([^&]+)", out)
    if not m:
        return None
    from urllib.parse import unquote
    raw = unquote(m.group(1))
    if (w := re.search(r"weidian\.com.*itemI[dD]=(\d+)", raw)):
        return "weidian:" + w.group(1)
    if (t := re.search(r"(?:taobao|tmall)\.com.*[?&]id=(\d+)", raw)):
        return "taobao:" + t.group(1)
    if (a := re.search(r"1688\.com/offer/(\d+)", raw)):
        return "1688:" + a.group(1)
    return None


def to_url(key):
    plat, iid = key.split(":", 1)
    return plat, {
        "weidian": f"https://weidian.com/item.html?itemID={iid}",
        "taobao": f"https://item.taobao.com/item.htm?id={iid}",
        "1688": f"https://detail.1688.com/offer/{iid}.html",
    }[plat]


def price_from_text(s):
    s = s.replace(",", ".")
    m = re.search(r"[¥￥]\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:yuan|yuanes|cny|rmb|元|¥)", s, re.I)
    if m:
        return float(m.group(1) or m.group(2))
    m = re.search(r"(?:us)?\$\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:usd|dolares|dólares|dls|\$)", s, re.I)
    if m:
        return round(float(m.group(1) or m.group(2)) * USD_TO_CNY, 2)
    return None


def main(canal):
    raw = json.loads((ROOT / "data" / "raw" / f"discord_{canal}.json").read_text("utf-8"))
    titles = json.loads((ROOT / "data" / "raw" / f"discord_{canal}_titulos.json").read_text("utf-8"))
    data = json.loads(DATA.read_text("utf-8"))
    by_url = {p["url"]: p for p in data["products"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = skipped = 0
    for tid, info in raw.items():
        meta = titles.get(tid)
        if not meta:
            continue
        keys = []
        for k in info.get("links", []):
            if k.startswith("short:"):
                k = resolve_short(k[6:]) or ""
            if k.split(":")[0] in ("weidian", "taobao", "1688"):
                keys.append(k)
        keys = [k for k in keys if not k.endswith(":0")]
        if not keys:
            skipped += 1
            continue
        plat, url = to_url(keys[0])
        image, price, pmax = "", None, None
        if plat == "weidian":
            res = weidian(keys[0].split(":")[1])
            if not res or res.get("offlineItem"):
                skipped += 1
                continue
            image = (res.get("itemMainPic") or "").split("?")[0]
            image = image + "?w=480&h=480&cp=1" if image else ""
            low = (res.get("itemDiscountLowPrice") or res.get("itemOriginalLowPrice") or 0) / 100
            high = (res.get("itemDiscountHighPrice") or res.get("itemOriginalHighPrice") or 0) / 100
            price, pmax = low or None, (high if high > low else None)
        if not price:
            price = price_from_text(f"{info.get('title', '')} {info.get('text', '')}")
        if not price:
            skipped += 1
            continue
        qc = [f"img/qc/{tid}/{f}" for f in info.get("imgs", [])]
        if url in by_url:  # ya estaba (ej. vino de LatamFinds): sumarle las fotos QC
            old = by_url[url]
            old["qc"] = list(dict.fromkeys(old.get("qc", []) + qc))
            continue
        p = {
            "id": f"dc-{canal}-{tid}",
            "title": meta["title"], "brand": meta.get("brand", ""), "category": meta["category"],
            "type": meta.get("type", ""), "color": meta.get("color", ""),
            "tags": [info.get("title", ""), "qc discord"],
            "image": image, "qc": qc, "source": plat, "url": url,
            "price_cny": round(price, 2), "price_cny_max": pmax,
            "price_checked": now, "added": now[:10],
        }
        data["products"].append(p)
        by_url[url] = p
        added += 1
    data["updated"] = now
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"Discord {canal}: {added} agregados, {skipped} sin link/precio. Total: {len(data['products'])}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qc")
