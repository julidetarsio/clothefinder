#!/usr/bin/env python3
"""Limpia el catálogo: unifica nombres de marca, deja solo marcas reconocidas y rehace los títulos.

Uso: python3 tools/curate.py          (muestra qué haría)
     python3 tools/curate.py --apply  (guarda los cambios en data/products.json)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from titles import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "products.json"

# Marcas que se quedan en el buscador (nombre como se muestra)
KEEP = [
    "Supreme", "Corteiz", "Nike", "Jordan", "Adidas", "Stussy", "Bape", "Trapstar", "Essentials", "Fear of God",
    "Chrome Hearts", "Ralph Lauren", "Lacoste", "Stone Island", "Moncler", "The North Face", "Carhartt",
    "Palm Angels", "Off-White", "Balenciaga", "Gucci", "Louis Vuitton", "Prada", "Dior", "Burberry", "Amiri",
    "Gallery Dept", "Denim Tears", "Sp5der", "Hellstar", "Syna World", "Represent", "Rhude", "Vetements",
    "Acne Studios", "Maison Margiela", "Arc'teryx", "Canada Goose", "New Balance", "Asics", "Yeezy", "Timberland",
    "UGG", "Converse", "Vans", "Rick Owens", "Alexander McQueen", "Golden Goose", "Givenchy", "Valentino",
    "Versace", "Celine", "Loewe", "Fendi", "Chanel", "Saint Laurent", "Hermes", "Miu Miu", "Thom Browne",
    "Hoka", "On", "Salomon", "Puma", "Onitsuka Tiger", "Birkenstock", "Tommy Hilfiger", "Calvin Klein",
    "Armani", "Kenzo", "Ami Paris", "Casablanca", "Broken Planet", "Eric Emanuel", "Aime Leon Dore", "Kith",
    "Enfants Riches Deprimes", "Travis Scott", "Comme des Garcons", "Palace", "Vlone", "Purple Brand",
    "C.P. Company", "Cole Buxton", "Drew House", "Lululemon", "Maison Mihara Yasuhiro", "Evisu", "Patagonia",
    "Levi's", "Fred Perry", "Diesel", "Anti Social Social Club", "Billionaire Boys Club", "Kapital",
    "Saint Michael", "Readymade", "Vivienne Westwood", "Parajumpers", "Moose Knuckles", "Montbell",
    "Crocs", "Saucony", "Mizuno", "Umbro", "Under Armour", "Columbia", "Oakley", "Valley", "Mixed Emotions",
    "Satoshi Nakamoto", "Who Decides War", "Patta", "ERL", "Loro Piana", "Zara", "Dr. Martens", "Brunello Cucinelli",
    # fútbol: clubes y selecciones tienen mucha salida
    "FC Barcelona", "Real Madrid", "AC Milan", "Argentina", "Francia", "Rosario Central", "Tottenham", "Ajax",
    "Santos FC", "NBA",
]

ALIASES = {
    "polo ralph lauren": "Ralph Lauren", "polo": "Ralph Lauren", "adidas": "Adidas", "air jordan": "Jordan",
    "north face": "The North Face", "tnf": "The North Face", "a bathing ape": "Bape", "bape": "Bape",
    "fear of god essentials": "Essentials", "fog essentials": "Essentials", "amiri": "Amiri",
    "gallery dept.": "Gallery Dept", "cdg": "Comme des Garcons", "comme des garcons play": "Comme des Garcons",
    "sp5der": "Sp5der", "spider": "Sp5der", "ami": "Ami Paris", "ami paris": "Ami Paris", "on running": "On",
    "vlone": "Vlone", "evisu": "Evisu", "ysl": "Saint Laurent", "ugg": "UGG", "christian dior": "Dior",
    "mm6 maison margiela": "Maison Margiela", "carhartt wip": "Carhartt", "arcteryx": "Arc'teryx",
    "erd": "Enfants Riches Deprimes", "emporio armani": "Armani", "calvin klein jeans": "Calvin Klein",
    "kanye west": "Yeezy", "cr7": "", "stüssy": "Stussy", "syna": "Syna World", "synaworld": "Syna World",
    "travis scott x mcdonald's": "Travis Scott", "denim tears x readymade": "Denim Tears",
    "nike x off-white": "Nike", "adidas x gucci": "Gucci", "bape x stussy": "Bape", "cdg x stussy": "Stussy",
    "comme des garcons play x converse": "Converse", "miu miu, new balance": "New Balance",
}
KEEP_L = {b.lower(): b for b in KEEP}
# Para detectar la marca en el nombre cuando no viene cargada (más largas primero)
DETECT = sorted(set(list(KEEP_L) + list(ALIASES)) - {"polo", "spider", "on", "ami", "syna"}, key=len, reverse=True)


def norm_brand(b):
    k = (b or "").strip().lower()
    if not k:
        return ""
    if k in ALIASES:
        return ALIASES[k]
    return KEEP_L.get(k, b.strip())


def detect(text):
    t = " " + re.sub(r"[^a-z0-9'.&+ -]", " ", text.lower()) + " "
    for k in DETECT:
        if len(k) >= 3 and re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", t):
            b = norm_brand(k)
            if b:
                return b
    return ""


def main(apply):
    data = json.loads(DATA.read_text("utf-8"))
    lf = {r["id"]: r for r in json.loads((ROOT / "data" / "raw" / "latamfinds.json").read_text("utf-8"))}
    kept, dropped = [], {}
    for p in data["products"]:
        brand = norm_brand(p.get("brand", ""))
        src = lf.get(p["id"][3:]) if p["id"].startswith("wd-") else None
        if not brand or brand.lower() not in KEEP_L:
            brand = detect(" ".join([p.get("brand", ""), p.get("title", ""), (src or {}).get("name", "")])) or brand
        if brand.lower() not in KEEP_L:
            dropped[brand or "(sin marca)"] = dropped.get(brand or "(sin marca)", 0) + 1
            continue
        p["brand"] = brand
        if src:
            title, category, ptype, color = build(src["cat"], brand, src["name"])
            p.update(title=title, category=category, type=ptype, color=color or p.get("color", ""))
        else:
            p["title"] = p["title"].replace("Campera puffer", "Campera inflable")
            if p.get("type") == "Campera puffer":
                p["type"] = "Campera inflable"
        kept.append(p)
    print(f"Quedan {len(kept)} de {len(data['products'])} productos. Se sacan {len(data['products']) - len(kept)}:")
    print(", ".join(f"{b} ({n})" for b, n in sorted(dropped.items(), key=lambda x: -x[1])))
    if apply:
        data["products"] = kept
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
        print("Guardado.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
