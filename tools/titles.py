"""Arma títulos en español a partir de categoría, marca y nombre del modelo.

Ej: ("hoodies", "Supreme", "Box Logo Zip Hoodie Red") -> "Buzo con cierre Supreme Box Logo rojo"
"""
import re

CATEGORY = {
    "shoes": ("Zapatillas", "Zapatillas"),
    "tees": ("Remera", "Ropa"),
    "hoodies": ("Buzo", "Ropa"),
    "jackets": ("Campera", "Ropa"),
    "pants": ("Pantalón", "Ropa"),
    "shorts": ("Short", "Ropa"),
    "sets": ("Conjunto", "Ropa"),
    "shirts": ("Camisa", "Ropa"),
    "knitwear": ("Sweater", "Ropa"),
}

# Palabras del nombre que definen mejor el tipo de prenda (se buscan en orden)
TYPE_RULES = [
    (r"\bzip[- ]?up hoodie|\bzip hoodie|\bfull[- ]zip hoodie", "Buzo con cierre"),
    (r"\bhalf[- ]zip|\bquarter[- ]zip|1/4 zip", "Buzo medio cierre"),
    (r"\bhoodie|\bhooded sweatshirt", "Buzo con capucha"),
    (r"\bcrewneck|\bsweatshirt|\bcrew\b", "Buzo"),
    (r"\bpuffer|\bdown jacket|\bdown coat|\bpadded jacket", "Campera inflable"),
    (r"\bvest\b|\bgilet", "Chaleco"),
    (r"\bwindbreaker|\bwindrunner|\btrack jacket", "Campera rompeviento"),
    (r"\bdenim jacket|\bjean jacket|\btrucker", "Campera de jean"),
    (r"\bleather jacket", "Campera de cuero"),
    (r"\bvarsity|\bbomber", "Campera bomber"),
    (r"\bcoat\b|\btrench|\bovercoat", "Abrigo"),
    (r"\bjacket|\bshell\b|\banorak|\bparka", "Campera"),
    (r"\blong[- ]?sleeve|\bl/s\b", "Remera manga larga"),
    (r"\btank top|\bsinglet", "Musculosa"),
    (r"\bjersey", "Camiseta"),
    (r"\bt-?shirt|\btee\b", "Remera"),
    (r"\bpolo\b(?!\s+ralph)", "Chomba"),
    (r"\bjeans?\b|\bdenim pants", "Jean"),
    (r"\bcargo", "Pantalón cargo"),
    (r"\bjogger|\bsweatpants|\btrack ?pants", "Jogging"),
    (r"\bshorts?\b|\bswim ?trunks", "Short"),
    (r"\btracksuit", "Conjunto deportivo"),
    (r"\bcardigan", "Cárdigan"),
    (r"\bsweater|\bknit\b|\bjumper", "Sweater"),
    (r"\bshirt\b|\bflannel|\bbutton[- ]?(up|down)", "Camisa"),
    (r"\bslides?\b|\bflip[- ]?flops?|\bsandals?", "Ojotas"),
    (r"\bboots?\b", "Botas"),
    (r"\bslippers?\b|\bclogs?\b|\bmules?\b", "Pantuflas"),
    (r"\bloafers?\b", "Mocasines"),
    (r"\bcleats?\b|\bfootball boots?\b|\b(fg|tf|ag)\b", "Botines"),
]
# Tipos permitidos según la categoría de origen (evita "Buzo" en una remera, etc.)
ALLOWED = {
    "tees": {"Remera", "Remera manga larga", "Chomba", "Musculosa", "Camiseta"},
    "hoodies": {"Buzo", "Buzo con capucha", "Buzo con cierre", "Buzo medio cierre"},
    "jackets": {"Campera", "Campera inflable", "Chaleco", "Campera rompeviento", "Campera de jean", "Campera de cuero", "Campera bomber", "Abrigo"},
    "pants": {"Pantalón", "Jean", "Pantalón cargo", "Jogging"},
    "shorts": {"Short"},
    "sets": {"Conjunto", "Conjunto deportivo"},
    "shirts": {"Camisa", "Chomba", "Remera manga larga"},
    "knitwear": {"Sweater", "Cárdigan", "Buzo medio cierre", "Chaleco"},
    "shoes": {"Ojotas", "Botas", "Pantuflas", "Mocasines", "Botines"},
}
# Palabras de tipo que se sacan del modelo para no repetir
TYPE_WORDS = r"\b(zip[- ]?up|full[- ]zip|half[- ]zip|quarter[- ]zip|zip|hoodie|hooded|sweatshirt|crewneck|t-?shirt|tee|jacket|pants|jeans?|shorts?|sweater|knit|cardigan|shirt|long[- ]?sleeve|polo|vest|coat|tracksuit|jogger|sweatpants|sneakers?|shoes?|cargo|windbreaker|puffer|vest|down|crew-?neck|crew|bodysuit|jackets|hoodies|shirts|sweatshorts|sweatpants|basketball shoes|running shoes|hiking shoes|sneakers|shoes|slides|boots|trainers|short-sleeved?|long-sleeved?|-?sleeved?|offers a variety of classic|style|graphic|t-shirts|tees|polo shirts?|and vests|jackets and|clothing|apparel|vests|windbreakers|puffers|coats|sweaters|cardigans|joggers|trousers|sets|collection|series|new|men'?s|women'?s|unisex|classic-fit)\b"

COLORS = [
    ("black", "negro"), ("white", "blanco"), ("red", "rojo"), ("blue", "azul"), ("navy", "azul marino"),
    ("grey", "gris"), ("gray", "gris"), ("green", "verde"), ("olive", "verde oliva"), ("brown", "marrón"),
    ("beige", "beige"), ("cream", "crema"), ("pink", "rosa"), ("yellow", "amarillo"), ("purple", "violeta"),
    ("orange", "naranja"), ("khaki", "caqui"), ("burgundy", "bordó"), ("silver", "plateado"), ("gold", "dorado"),
    ("tan", "camel"), ("camo", "camuflado"),
]
FEMININE = {"Botines"} | {"Remera", "Campera", "Camisa", "Chomba", "Musculosa", "Camiseta", "Ojotas", "Botas", "Zapatillas", "Pantuflas"}


def _fem(color, plural):
    base = {"negro": "negra", "blanco": "blanca", "rojo": "roja", "amarillo": "amarilla", "plateado": "plateada",
            "dorado": "dorada", "camuflado": "camuflada"}.get(color, color)
    if plural and base[-1] in "aeo":
        base += "s"
    return base


def build(cat, brand, name):
    name = (name or "").strip()
    brand = (brand or "").strip()
    default_type, category = CATEGORY.get(cat, ("Prenda", "Ropa"))
    low = name.lower()

    ptype = default_type
    allowed = ALLOWED.get(cat)
    for rx, t in TYPE_RULES:
        if re.search(rx, low) and (allowed is None or t in allowed):
            ptype = t
            break

    model = name
    if brand:
        model = re.sub(re.escape(brand), "", model, flags=re.I)
    hits = []
    for en, es in COLORS:
        m = re.search(rf"\b{en}\b", model, re.I)
        if m:
            hits.append((m.start(), es))
    found = []
    for _, es in sorted(hits):
        if es not in found:
            found.append(es)
    model = re.sub(r"\bwith\b", "con", model, flags=re.I)
    if cat == "shoes":
        model = re.sub(r"\b(basketball|running|hiking|skate|casual)?\s*(shoes?|sneakers?|trainers)\b", "", model, flags=re.I).strip(" -,")
        # en zapatillas el nombre del colorway se deja tal cual (es lo que la gente busca)
        title = " ".join(p for p in [ptype, brand, model] if p)
        return re.sub(r"\s+", " ", title).strip(), category, ptype, (found[0].capitalize() if found else "")
    for en, _ in COLORS:
        model = re.sub(rf"\b{en}\b", "", model, flags=re.I)
    model = re.sub(TYPE_WORDS, "", model, flags=re.I)
    model = re.sub(r"\(\s*\)|\s-\s|^\W+|\s+-\B", " ", model)
    model = re.sub(r"\s{2,}", " ", re.sub(r"[\s/,\-–]+$|^[\s/,\-–]+", "", model)).strip(" -/,")

    first = ptype.split()[0]
    fem = first in FEMININE
    plural = first.endswith("s")
    colors = [(_fem(c, plural) if fem else (c + "s" if plural and c[-1] in "o" else c)) for c in found[:2]]

    model = re.sub(r"(^|\s)(and|&|y|con|with|-|:)(\s+(and|&|y|con|with|-|:))*\s*$", "", " ".join(model.split()[:6])).strip(" -:,&")
    model = re.sub(r"^(and|&|con|-)\s+", "", model)
    parts = [ptype, brand, model, " y ".join(colors)]
    title = " ".join(p for p in parts if p)
    return re.sub(r"\s+", " ", title).strip(), category, ptype, (found[0].capitalize() if found else "")
