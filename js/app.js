import { kakobuyLink } from "./links.js";

// ===== Config =====
const KAKOBUY_AFFCODE = "fqb6s"; // si tenés código de afiliado de KakoBuy, ponelo acá
const PAGE_SIZE = 40;
const CATEGORIES = ["Todo", "Ropa", "Zapatillas"];
const QUICK = ["campera inflable", "buzo con capucha", "remera", "zapatillas", "jean", "camiseta fútbol", "corteiz", "supreme", "nike tech"];
const SOURCE_LABEL = { taobao: "Taobao", weidian: "Weidian", "1688": "1688", yupoo: "Yupoo", otro: "Otro" };

// Sinónimos: cualquier palabra del grupo encuentra a las demás (español rioplatense, España, inglés)
// Cada grupo es específico: "campera inflable" solo trae inflables, "campera" trae todas las camperas.
const SYNONYMS = [
  ["campera", "camperas", "chaqueta", "jacket", "chamarra", "casaca"],
  ["inflable", "inflables", "puffer", "plumas", "pluma", "plumon", "plumifero", "acolchada", "acolchado", "nuptse"],
  ["rompeviento", "rompevientos", "windbreaker", "windrunner", "impermeable"],
  ["bomber", "varsity", "universitaria"],
  ["abrigo", "tapado", "coat", "trench", "parka"],
  ["chaleco", "vest", "gilet"],
  ["buzo", "buzos", "sudadera", "sweatshirt", "poleron", "crewneck"],
  ["capucha", "hoodie", "canguro", "hoodies"],
  ["cierre", "zip", "zipper", "cremallera"],
  ["sweater", "sueter", "sweter", "pullover", "tejido", "knit", "cardigan"],
  ["remera", "remeras", "playera", "tshirt", "tee", "polera"],
  ["camiseta", "camisetas", "jersey", "futbol", "fútbol", "titular", "suplente"],
  ["chomba", "chombas", "polo"],
  ["musculosa", "musculosas", "tank", "sisa"],
  ["pantalon", "pantalones", "pants", "trousers"],
  ["jean", "jeans", "denim", "vaquero", "vaqueros"],
  ["jogging", "joggings", "jogger", "joggers", "sweatpants", "babucha"],
  ["short", "shorts", "bermuda", "bermudas", "pantaloneta"],
  ["zapatillas", "zapatilla", "sneakers", "tenis", "shoes", "calzado", "deportivas"],
  ["botines", "botin", "cleats", "taperoles", "chimpunes"],
  ["ojotas", "ojota", "chanclas", "chinelas", "slides", "sandalias", "sandalia"],
  ["pantuflas", "pantufla", "zuecos", "zueco", "clogs"],
  ["botas", "bota", "boots", "borcegos", "borcego"],
  ["gorra", "cap", "gorro", "beanie", "hat", "sombrero"],
  ["mochila", "backpack", "bolso", "bag", "rinonera", "cartera"],
  ["medias", "calcetines", "socks"],
  ["anteojos", "lentes", "gafas", "sunglasses"],
  ["cinturon", "cinto", "belt"],
  ["camisa", "camisas", "shirt"],
  ["conjunto", "conjuntos", "tracksuit", "chandal", "set"],
  ["manga", "sleeve"], ["larga", "long"],
  ["negro", "negra", "black"], ["blanco", "blanca", "white"], ["rojo", "roja", "red"],
  ["azul", "blue", "navy"], ["gris", "grey", "gray"], ["verde", "green"], ["marron", "brown"],
  ["beige", "crema", "cream"], ["rosa", "pink"], ["amarillo", "yellow"], ["violeta", "purple"],
  ["corteiz", "crtz"], ["stussy", "stüssy"], ["trapstar", "trap star"],
];

// ===== Estado =====
const state = { all: [], rate: 0.14, cat: "Todo", shown: PAGE_SIZE, results: [] };
const $ = (id) => document.getElementById(id);

const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
const SYN_MAP = new Map();
for (const group of SYNONYMS) { const g = group.map(norm); for (const w of g) SYN_MAP.set(w, g); }
const expand = (w) => SYN_MAP.get(w) || [w];

function searchText(p) {
  return norm([p.title, p.brand, p.type, p.color, p.category, (p.tags || []).join(" "), SOURCE_LABEL[p.source]].join(" "));
}

// Puntaje: cada palabra buscada tiene que aparecer (o un sinónimo, o un prefijo de 3+ letras)
function score(p, terms) {
  if (!terms.length) return 1;
  const words = p._words, title = p._title;
  let total = 0;
  for (const t of terms) {
    let best = 0;
    for (const v of expand(t)) {
      if (words.includes(v)) best = Math.max(best, title.includes(v) ? 3 : 2);
      else if (v.length >= 3 && words.some((w) => w.startsWith(v))) best = Math.max(best, 1.5);
      else if (v.length >= 4 && p._text.includes(v)) best = Math.max(best, 1);
    }
    if (!best) return 0;
    total += best;
  }
  return total;
}

const usd = (cny) => cny * state.rate;
const fmtUsd = (n) => "US$ " + n.toFixed(n < 100 ? 2 : 0);

function timeAgo(iso) {
  if (!iso) return "";
  const d = (Date.now() - new Date(iso).getTime()) / 86400000;
  if (d < 1) return "hoy";
  if (d < 2) return "ayer";
  if (d < 30) return `hace ${Math.floor(d)} días`;
  return `hace ${Math.floor(d / 30)} meses`;
}

// ===== Render =====
function apply() {
  const terms = norm($("q").value).split(" ").filter(Boolean);
  const source = $("source").value, brand = $("brand").value, ptype = $("ptype").value, onlyQc = $("onlyQc").checked;
  const min = parseFloat($("pmin").value), max = parseFloat($("pmax").value);
  let list = [];
  for (const p of state.all) {
    if (state.cat !== "Todo" && p.category !== state.cat) continue;
    if (source && p.source !== source) continue;
    if (brand && p.brand !== brand) continue;
    if (ptype && p.type !== ptype) continue;
    if (onlyQc && !(p.qc && p.qc.length)) continue;
    const hasPrice = p.price_cny > 0;
    const u = hasPrice ? usd(p.price_cny) : NaN;
    if (!isNaN(min) && !(u >= min)) continue;
    if (!isNaN(max) && !(u <= max)) continue;
    const s = score(p, terms);
    if (s > 0) list.push([s, p]);
  }
  const sort = $("sort").value;
  const cmp = {
    rel: (a, b) => b[0] - a[0] || (b[1].added || "").localeCompare(a[1].added || ""),
    new: (a, b) => (b[1].added || "").localeCompare(a[1].added || ""),
    // los productos con "precio a consultar" van al final
    asc: (a, b) => (a[1].price_cny || Infinity) - (b[1].price_cny || Infinity),
    desc: (a, b) => (b[1].price_cny || -1) - (a[1].price_cny || -1),
  }[sort];
  list.sort(cmp);
  state.results = list.map((x) => x[1]);
  state.shown = PAGE_SIZE;
  render();
  syncUrl();
}

function render() {
  const grid = $("grid"), items = state.results.slice(0, state.shown);
  grid.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const p of items) frag.appendChild(card(p));
  grid.appendChild(frag);
  const n = state.results.length;
  $("count").textContent = `${n} ${n === 1 ? "producto" : "productos"}`;
  $("empty").hidden = n > 0;
  $("moreBtn").hidden = state.shown >= n;
}

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
}

function card(p) {
  const badgeCls = p.source === "1688" ? "c1688" : p.source;
  const cover = p.image || (p.qc && p.qc[0]) || "";
  const img = cover
    ? el("img", { src: cover, alt: p.title, loading: "lazy", referrerpolicy: "no-referrer" })
    : el("div", { class: "ph" }, p.category === "Zapatillas" ? "👟" : p.category === "Accesorios" ? "🧢" : "👕");
  if (cover) img.addEventListener("error", () => img.replaceWith(el("div", { class: "ph" }, "🖼️")));

  const thumb = el("div", { class: "thumb" }, img, el("span", { class: "badge " + badgeCls }, SOURCE_LABEL[p.source] || p.source));
  if (p.qc && p.qc.length) thumb.append(el("button", { class: "qc-pill", onclick: () => openQc(p) }, `QC · ${p.qc.length}`));
  if (p.demo) thumb.append(el("span", { class: "demo" }, "EJEMPLO"));

  const meta = [p.brand, p.color].filter(Boolean).join(" · ");
  const checked = !(p.price_cny > 0)
    ? "Mirá el precio real en el link del producto"
    : p.price_fixed
    ? `Precio publicado ${timeAgo(p.price_checked)} (puede variar)`
    : p.price_checked ? `Precio verificado ${timeAgo(p.price_checked)}` : "";

  return el("article", { class: "card" },
    thumb,
    el("div", { class: "body" },
      el("h3", { class: "title" }, p.title),
      meta ? el("div", { class: "meta" }, meta) : null,
      el("div", { class: "prices" },
        ...(p.price_cny > 0
          ? [el("span", { class: "usd" }, (p.price_cny_max ? "desde " : "") + fmtUsd(usd(p.price_cny))),
             el("span", { class: "cny" }, p.price_cny_max ? `¥${p.price_cny}–${p.price_cny_max}` : `¥${p.price_cny}`)]
          : [el("span", { class: "usd consultar" }, "Precio a consultar")])),
      checked ? el("div", { class: "meta" }, checked) : null,
      el("div", { class: "link-row" },
        el("code", { title: p.url }, p.url)),
      el("div", { class: "actions" },
        el("button", { class: "btn", onclick: () => copy(p.url) }, "Copiar link"),
        el("a", { class: "btn", href: p.url, target: "_blank", rel: "noopener noreferrer" }, "Ver original"),
        el("a", { class: "btn primary full", href: kakobuyLink(p.url, KAKOBUY_AFFCODE), target: "_blank", rel: "noopener noreferrer" }, "Comprar en KakoBuy ↗"))
    ));
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const t = el("textarea", {}, text); document.body.append(t); t.select(); document.execCommand("copy"); t.remove();
  }
  toast("Link copiado ✓");
}
let toastTimer;
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 1600);
}

// ===== QC =====
const qc = { list: [], i: 0 };
function openQc(p) {
  qc.list = p.qc; qc.i = 0; $("qcTitle").textContent = `QC · ${p.title}`; showQc(); $("qcDialog").showModal();
}
function showQc() {
  $("qcImg").src = qc.list[qc.i]; $("qcPos").textContent = `${qc.i + 1} / ${qc.list.length}`;
}
$("qcPrev").onclick = () => { qc.i = (qc.i - 1 + qc.list.length) % qc.list.length; showQc(); };
$("qcNext").onclick = () => { qc.i = (qc.i + 1) % qc.list.length; showQc(); };
$("qcClose").onclick = () => $("qcDialog").close();
$("qcDialog").addEventListener("click", (e) => { if (e.target.id === "qcDialog") $("qcDialog").close(); });
document.addEventListener("keydown", (e) => {
  if (!$("qcDialog").open) return;
  if (e.key === "ArrowLeft") $("qcPrev").click();
  if (e.key === "ArrowRight") $("qcNext").click();
});

// ===== URL (para compartir búsquedas) =====
function syncUrl() {
  const u = new URLSearchParams();
  if ($("q").value.trim()) u.set("q", $("q").value.trim());
  if (state.cat !== "Todo") u.set("cat", state.cat);
  history.replaceState(null, "", u.toString() ? "?" + u : location.pathname);
}

// ===== Init =====
async function loadRate(fallback) {
  state.rate = fallback;
  try {
    const r = await fetch("https://open.er-api.com/v6/latest/CNY");
    const j = await r.json();
    if (j && j.rates && j.rates.USD) state.rate = j.rates.USD;
  } catch { /* usa el valor de respaldo */ }
  $("rate").textContent = `¥1 = US$ ${state.rate.toFixed(3)}`;
}

async function init() {
  const data = await fetch("data/products.json", { cache: "no-cache" }).then((r) => r.json());
  // Solo productos con link y precio
  state.all = data.products.filter((p) => p.url && (p.price_cny > 0 || p.price_ask)).map((p) => {
    const text = searchText(p);
    return { ...p, _text: text, _words: text.split(" "), _title: norm(p.title).split(" ") };
  });

  // Categorías
  for (const c of CATEGORIES) {
    $("catSeg").append(el("button", { role: "tab", "aria-selected": String(c === state.cat), onclick: (e) => {
      state.cat = c;
      for (const b of $("catSeg").children) b.setAttribute("aria-selected", String(b === e.currentTarget));
      apply();
    } }, c));
  }
  // Marcas
  const brands = [...new Set(state.all.map((p) => p.brand).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  for (const b of brands) $("brand").append(el("option", { value: b }, b));
  // Tipos de prenda, agrupados por categoría
  const types = {};
  for (const p of state.all) if (p.type) (types[p.category] = types[p.category] || new Set()).add(p.type);
  for (const cat of Object.keys(types).sort()) {
    const g = el("optgroup", { label: cat });
    for (const t of [...types[cat]].sort((a, b) => a.localeCompare(b))) g.append(el("option", { value: t }, t));
    $("ptype").append(g);
  }
  // Búsquedas rápidas
  for (const q of QUICK) $("quick").append(el("button", { class: "chip", onclick: () => { $("q").value = q; apply(); } }, q));

  // Parámetros de URL
  const params = new URLSearchParams(location.search);
  if (params.get("q")) $("q").value = params.get("q");
  if (params.get("cat") && CATEGORIES.includes(params.get("cat"))) {
    state.cat = params.get("cat");
    for (const b of $("catSeg").children) b.setAttribute("aria-selected", String(b.textContent === state.cat));
  }

  let t;
  $("q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(apply, 120); });
  $("searchForm").addEventListener("submit", (e) => { e.preventDefault(); apply(); $("q").blur(); });
  for (const id of ["source", "brand", "ptype", "onlyQc", "sort"]) $(id).addEventListener("change", apply);
  for (const id of ["pmin", "pmax"]) $(id).addEventListener("input", apply);
  $("moreBtn").onclick = () => { state.shown += PAGE_SIZE; render(); };

  await loadRate(data.cny_to_usd_fallback || 0.14);
  apply();
}
init();
