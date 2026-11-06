#!/usr/bin/env python3
"""Arma productos a partir de los álbumes de Yupoo (data/raw/yupoo_rows.txt + data/raw/yupoo_weidian.json).

- Marca: del título del álbum / Weidian (incluye abreviaturas de los vendedores: SUP, BLCG, 1V, Mon...).
- Tipo de prenda y color: reglas en inglés y chino.
- Títulos corregidos a mano (mirando las fotos): data/raw/yupoo_titulos.txt  ->  id|titulo|marca|categoria|tipo|color  ('-' = descartar)
Solo entran marcas de la lista de tools/curate.py.

Uso: python3 tools/import_yupoo.py           (muestra resumen y los que no se pudieron identificar)
     python3 tools/import_yupoo.py --apply   (agrega a data/products.json)
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from curate import KEEP_L, detect, norm_brand  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data" / "products.json"

ABBR = [  # (regex sobre el texto, marca)
    (r"1/v", "Louis Vuitton"), (r"d/io", "Dior"), (r"f/f|f/d", "Fendi"), (r"c-h-a|\bcha\b", "Chanel"),
    (r"\bm/?c\b", "Moncler"), (r"p/a", "Prada"), (r"g/v", "Givenchy"), (r"\berl\b", "ERL"),
    (r"\bsup\b|supreme|sup大佛|\bsup\s", "Supreme"), (r"\bblcg\b|巴黎世家", "Balenciaga"), (r"\b1v\b|\blv\b|路易", "Louis Vuitton"),
    (r"\bmon\b|moncler|蒙口", "Moncler"), (r"\bcg\b|canada goose|加拿大鹅", "Canada Goose"), (r"\brl\b|ralph", "Ralph Lauren"),
    (r"\bloe\b|loew", "Loewe"), (r"\bce\b|celine", "Celine"), (r"\bysl\b", "Saint Laurent"), (r"\bsi\b|stone island|石头岛", "Stone Island"),
    (r"\bch\b|chrome|克罗心", "Chrome Hearts"), (r"\bbbr\b|burberry|巴宝莉", "Burberry"), (r"\bpra\b|prada|普拉达", "Prada"),
    (r"d1or|dior|迪奥", "Dior"), (r"\bacne", "Acne Studios"), (r"\blp\b|loro piana", "Loro Piana"), (r"\bbc\b|cucinelli", "Brunello Cucinelli"), (r"miu ?miu", "Miu Miu"), (r"\bmm6\b|margiela|ma1s0n", "Maison Margiela"),
    (r"\bts\b|travis", "Travis Scott"), (r"\bess\b|\bfog\b|essent1als|essentials|fear of god", "Essentials"),
    (r"\bstu\b|stussy|stüssy", "Stussy"), (r"valley", "Valley"), (r"enfants r1ches|enfants riches|\berd\b", "Enfants Riches Deprimes"),
    (r"gallery dept", "Gallery Dept"), (r"vetements", "Vetements"), (r"\bam1\b|\bami\b", "Ami Paris"), (r"sa1nt m1chael|saint michael", "Saint Michael"),
    (r"sat0sh1|satoshi", "Satoshi Nakamoto"), (r"trapstar", "Trapstar"), (r"\bsyna|synaworld|\bsy\b", "Syna World"),
    (r"corteiz|\bcrtz\b", "Corteiz"), (r"chrome hearts", "Chrome Hearts"), (r"aime leon", "Aime Leon Dore"), (r"bape|bathing ape", "Bape"),
    (r"\bnk\b|nike|nocta", "Nike"), (r"comme des|\bcdg\b", "Comme des Garcons"), (r"burberry", "Burberry"), (r"zoo ?york", ""),
    (r"\bnba\b", "NBA"), (r"巴萨|barcelona", "FC Barcelona"), (r"\bmexum\b", ""),
]
TYPES = [  # (regex, tipo, categoría)
    (r"马丁靴|\bboots?\b|靴", "Botas", "Zapatillas"), (r"sneaker|运动鞋|板鞋|鞋", "Zapatillas", "Zapatillas"),
    (r"羽绒|puffer|down jacket|padded|棉服", "Campera inflable", "Ropa"), (r"马甲|\bvest\b|gilet", "Chaleco", "Ropa"),
    (r"风衣|windbreak|冲锋衣|shell", "Campera rompeviento", "Ropa"), (r"牛仔夹克|denim jacket|trucker", "Campera de jean", "Ropa"),
    (r"皮衣|leather jacket|lambskin", "Campera de cuero", "Ropa"), (r"bomber|棒球服|varsity", "Campera bomber", "Ropa"),
    (r"大衣|\bcoat\b", "Abrigo", "Ropa"), (r"套装|tracksuit|\bset\b|suit\b", "Conjunto", "Ropa"),
    (r"1/4 zip|quarter.?zip|半拉链", "Buzo medio cierre", "Ropa"),
    (r"拉链.{0,4}(卫衣|帽衫)|zip.?(up)? ?hood|zipper|zip hoodie|拉链", "Buzo con cierre", "Ropa"),
    (r"帽衫|连帽|hoodie|hoody|\bhood\b", "Buzo con capucha", "Ropa"),
    (r"开衫|cardigan", "Cárdigan", "Ropa"), (r"毛衣|针织|knit|sweater|jumper|mohair", "Sweater", "Ropa"),
    (r"圆领卫衣|卫衣|crew ?sweat|sweatshirt|crewneck|圆领$", "Buzo", "Ropa"),
    (r"夹克|外套|jacket|jacker", "Campera", "Ropa"), (r"球衣|jersey", "Camiseta", "Ropa"),
    (r"翻领|polo", "Chomba", "Ropa"), (r"衬衫|\bshirt\b(?!.*t-?shirt)|button", "Camisa", "Ropa"),
    (r"长袖|long ?s(lee)?ve?|l-?shirt|lshirt|\bls tee", "Remera manga larga", "Ropa"),
    (r"短袖|t-?shirt|\btee\b|sshirt|short sleeve", "Remera", "Ropa"),
    (r"牛仔裤|jeans?\b|denim|selvedge|bootcut", "Jean", "Ropa"), (r"工装裤|cargo", "Pantalón cargo", "Ropa"),
    (r"卫裤|束口|jogger|sweatpants|sweats\b", "Jogging", "Ropa"), (r"短裤|shorts?\b|jorts|swim", "Short", "Ropa"),
    (r"长裤|裤|pants|trousers", "Pantalón", "Ropa"),
]
COLORS = [(r"黑|black", "Negro"), (r"白|white", "Blanco"), (r"灰|gr[ae]y", "Gris"), (r"藏青|深蓝|navy", "Azul marino"),
          (r"蓝|blue", "Azul"), (r"红|\bred\b|burgundy|酒红", "Rojo"), (r"绿|green|olive", "Verde"), (r"粉|pink", "Rosa"),
          (r"紫|purple", "Violeta"), (r"黄|yellow", "Amarillo"), (r"棕|咖|brown", "Marrón"), (r"米|杏|beige|cream|apricot", "Beige"),
          (r"橘|orange", "Naranja"), (r"camo|迷彩|豹纹|leopard", "Camuflado")]
FEM = {"Remera", "Remera manga larga", "Campera", "Campera inflable", "Campera rompeviento", "Campera de jean", "Campera de cuero",
       "Campera bomber", "Camisa", "Chomba", "Camiseta", "Botas", "Zapatillas"}
FEM_COLOR = {"Negro": "negra", "Blanco": "blanca", "Rojo": "roja", "Amarillo": "amarilla", "Camuflado": "camuflada"}
CLEAN = re.compile(r"[一-鿿]+|[¥￥]\s*\d+|\d{3,}[-−]\w+|\b(cny|price|p:|on ?sales?|in stock|batch|best|new|drop|\d{2}(ss|fw|sp|su|as)|ss\d{2}|fw\d{2}|20\d\d)\b|[\[\]【】（）()|：:]", re.I)


def classify(text, album=""):
    low = text.lower()
    brand = ""
    for rx, b in ABBR:
        if re.search(rx, low):
            brand = b
            break
    if not brand:
        brand = detect(text)
    ptype, cat = "", "Ropa"
    for rx, t, c in TYPES:
        if re.search(rx, low):
            ptype, cat = t, c
            break
    color = next((c for rx, c in COLORS if re.search(rx, album.lower())), "") or next((c for rx, c in COLORS if re.search(rx, low)), "")
    return brand, ptype, cat, color


def title_for(brand, ptype, color, album):
    model = CLEAN.sub(" ", album)
    for w in [brand, "sup", "supreme", "ess", "fog", "blcg", "1v", "mon", "bbr", "d1or", "dior", "rl", "si", "ch", "nk", "sy", "syna", "synaworld", "pra", "loe", "bc", "mc", "m/c", "1/v", "d/io", "cg", "ce", "acne", "sshirt", "lshirt", "and", "sleeve", "short", "slv", "the"]:
        if w:
            model = re.sub(rf"(?<![a-z]){re.escape(w)}(?![a-z])", " ", model, flags=re.I)
    model = re.sub(r"\b(hoodie|hoody|tee|t-?shirt|jacket|sweater|shorts?|pants|jeans|set|tracksuit|zip|up|sweat|jogger|long ?sleeves?|polo|knit|vest|coat|cardigan|black|white|gr[ae]y|blue|navy|red|green|pink|purple|yellow|brown|beige|orange)\b", " ", model, flags=re.I)
    model = " ".join(w for w in re.sub(r"[-–/&+*]+", " ", model).split() if len(w) > 1)[:40].strip()
    col = ""
    if color:
        col = FEM_COLOR.get(color, color.lower()) if ptype in FEM else color.lower()
    return re.sub(r"\s+", " ", " ".join(x for x in [ptype, brand, model.title() if model.isupper() else model, col] if x)).strip()


def main(apply):
    info = json.loads((RAW / "yupoo_weidian.json").read_text("utf-8"))
    rows = {}
    for line in (RAW / "yupoo_rows.txt").read_text("utf-8").splitlines():
        p = line.split("|", 2)
        if len(p) == 3:
            rows.setdefault(p[1], p)
    manual = {}
    mf = RAW / "yupoo_titulos.txt"
    if mf.exists():
        for line in mf.read_text("utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                p = line.split("|")
                manual[p[0]] = None if p[1] == "-" else p[1:6]
    data = json.loads(DATA.read_text("utf-8"))
    have = {p["url"] for p in data["products"]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new, unknown, dropped = [], [], 0
    for iid, v in info.items():
        w = v.get("weidian") or {}
        if not w.get("itemMainPic") or w.get("offlineItem"):
            continue
        url = f"https://weidian.com/item.html?itemID={iid}"
        if url in have:
            continue
        text = f"{v['album_title']} {w.get('itemTitle', '')}"
        if iid in manual:
            if manual[iid] is None:
                dropped += 1
                continue
            title, brand, cat, ptype, color = manual[iid]
        else:
            brand, ptype, cat, color = classify(text, v["album_title"])
            if not brand or not ptype:
                unknown.append((iid, v["store"], text[:70]))
                continue
            if brand.lower() not in KEEP_L:
                dropped += 1
                continue
            title = title_for(brand, ptype, color, v["album_title"])
        low = (w.get("itemDiscountLowPrice") or w.get("itemOriginalLowPrice") or 0) / 100
        high = (w.get("itemDiscountHighPrice") or w.get("itemOriginalHighPrice") or 0) / 100
        if low <= 0:
            continue
        new.append({
            "id": "yp-" + iid, "title": title, "brand": brand, "category": cat, "type": ptype, "color": color,
            "tags": [v["album_title"], v["store"]], "image": w["itemMainPic"].split("?")[0] + "?w=480&h=480&cp=1",
            "qc": [], "source": "weidian", "url": url, "price_cny": round(low, 2),
            "price_cny_max": round(high, 2) if high > low else None, "price_checked": now, "added": now[:10],
        })
        have.add(url)
    print(f"Nuevos: {len(new)} | descartados (marca no reconocida): {dropped} | sin identificar: {len(unknown)}")
    for n in new[:15]:
        print("  +", n["title"])
    (RAW / "yupoo_sin_identificar.json").write_text(json.dumps(unknown, ensure_ascii=False), "utf-8")
    if apply:
        data["products"].extend(new)
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
        print("Guardado. Total:", len(data["products"]))


if __name__ == "__main__":
    main("--apply" in sys.argv)
