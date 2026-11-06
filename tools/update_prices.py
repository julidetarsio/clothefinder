#!/usr/bin/env python3
"""Revisa el precio actual de cada producto en su proveedor y actualiza data/products.json.

Uso:  python3 tools/update_prices.py
Lo corre GitHub Actions todos los días (.github/workflows/precios.yml).

- Weidian: API pública del producto (confiable).
- Yupoo: lee el precio del título del álbum (¥189, P189, 189元...).
- Taobao / 1688: bloquean bots casi siempre; se intenta y si falla se deja el precio anterior.
"""
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "products.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def get(url):
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")


def price_weidian(url):
    m = re.search(r"itemI[dD]=(\d+)", url)
    if not m:
        return None
    param = urllib.parse.quote(json.dumps({"itemId": m.group(1)}))
    out = subprocess.run(["curl", "-s", "-m", "20", "https://thor.weidian.com/detail/getItemSkuInfo/1.0?param=" + param],
                         capture_output=True, timeout=30).stdout
    res = json.loads(out.decode("utf-8", "ignore")).get("result") or {}
    if res.get("offlineItem"):
        return None
    low = res.get("itemDiscountLowPrice") or res.get("itemOriginalLowPrice")
    high = res.get("itemDiscountHighPrice") or res.get("itemOriginalHighPrice") or low
    return (round(int(low) / 100, 2), round(int(high) / 100, 2)) if low else None


PRICE_RE = re.compile(r"(?:[¥￥]|\bP|\bRMB\s*)\s*(\d{2,5}(?:\.\d+)?)|(\d{2,5})\s*(?:元|rmb|RMB)")


def price_yupoo(url):
    html = get(url)
    m = re.search(r"<title>(.*?)</title>", html, re.S) or re.search(r'class="showalbumheader__gallerytitle"[^>]*>(.*?)<', html, re.S)
    if not m:
        return None
    p = PRICE_RE.search(m.group(1))
    if not p:
        return None
    return float(p.group(1) or p.group(2))


def price_taobao(url):
    html = get(url)
    m = re.search(r'"(?:reservePrice|price)"\s*:\s*"?(\d+(?:\.\d+)?)', html)
    return float(m.group(1)) if m else None


def price_1688(url):
    html = get(url)
    m = re.search(r'"(?:price|priceDisplay)"\s*:\s*"?(\d+(?:\.\d+)?)', html)
    return float(m.group(1)) if m else None


FETCHERS = {"weidian": price_weidian, "yupoo": price_yupoo, "taobao": price_taobao, "1688": price_1688}


def main():
    data = json.loads(DATA.read_text("utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = ok = fail = 0
    for p in data["products"]:
        if p.get("demo"):
            continue
        fn = FETCHERS.get(p.get("source"))
        if not fn:
            continue
        try:
            new = fn(p["url"])
        except Exception as e:  # red, bloqueo, producto borrado...
            new = None
            print(f"  ✗ {p['id']}: {e.__class__.__name__}", file=sys.stderr)
        high = None
        if isinstance(new, tuple):
            new, high = new
        if new and new > 0:
            if high is not None:
                p["price_cny_max"] = high if high > new else None
            ok += 1
            p["price_checked"] = now
            if abs(new - float(p.get("price_cny", 0))) >= 0.01:
                print(f"  ¥{p.get('price_cny')} → ¥{new}  {p['title']}")
                p["price_cny"] = new
                changed += 1
        else:
            fail += 1
        time.sleep(0.5)  # no saturar a los proveedores
    data["updated"] = now
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Listo: {ok} verificados, {changed} cambiaron, {fail} sin respuesta.")


if __name__ == "__main__":
    main()
