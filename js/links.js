// Utilidades de links: detecta plataforma, limpia links de agentes y genera link de KakoBuy.
// Se usa tanto en el navegador (app.js) como en los scripts de Node.

export function detectSource(url) {
  const u = String(url || "").toLowerCase();
  if (u.includes("yupoo.com")) return "yupoo";
  if (u.includes("1688.com")) return "1688";
  if (u.includes("weidian.com")) return "weidian";
  if (u.includes("taobao.com") || u.includes("tmall.com")) return "taobao";
  return "otro";
}

// Convierte links de agentes (kakobuy, cssbuy, etc.) al link original del proveedor.
export function toRawLink(input) {
  let url;
  try { url = new URL(String(input).trim()); } catch { return String(input).trim(); }
  const host = url.hostname;

  // Agentes que llevan el link original en ?url=
  const embedded = url.searchParams.get("url");
  if (embedded && /^https?:/i.test(decodeURIComponent(embedded))) {
    return toRawLink(decodeURIComponent(embedded));
  }

  // CSSBuy: cssbuy.com/item-<id>.html (taobao), item-1688-<id>, item-micro-<id> (weidian)
  if (host.includes("cssbuy.com")) {
    let m = url.pathname.match(/item-1688-(\d+)/);
    if (m) return `https://detail.1688.com/offer/${m[1]}.html`;
    m = url.pathname.match(/item-micro-(\d+)/);
    if (m) return `https://weidian.com/item.html?itemID=${m[1]}`;
    m = url.pathname.match(/item-(\d+)/);
    if (m) return `https://item.taobao.com/item.htm?id=${m[1]}`;
  }

  // Formato ?id=...&shop_type=taobao|ali_1688|weidian (cnfans, mulebuy, acbuy...)
  const id = url.searchParams.get("id");
  const type = (url.searchParams.get("shop_type") || url.searchParams.get("platform") || "").toLowerCase();
  if (id && type && !/taobao\.com|1688\.com|weidian\.com/.test(host)) {
    if (type.includes("1688") || type.includes("ali")) return `https://detail.1688.com/offer/${id}.html`;
    if (type.includes("weidian") || type.includes("wd")) return `https://weidian.com/item.html?itemID=${id}`;
    return `https://item.taobao.com/item.htm?id=${id}`;
  }

  // Limpia parámetros de seguimiento en links originales
  if (host.includes("taobao.com") || host.includes("tmall.com")) {
    const tid = url.searchParams.get("id");
    if (tid) return `https://item.taobao.com/item.htm?id=${tid}`;
  }
  if (host.includes("weidian.com")) {
    const wid = url.searchParams.get("itemID") || url.searchParams.get("itemId");
    if (wid) return `https://weidian.com/item.html?itemID=${wid}`;
  }
  if (host.includes("1688.com")) {
    const m = url.pathname.match(/offer\/(\d+)/);
    if (m) return `https://detail.1688.com/offer/${m[1]}.html`;
  }
  return url.toString();
}

export function kakobuyLink(rawUrl, affcode = "") {
  const base = `https://www.kakobuy.com/item/details?url=${encodeURIComponent(rawUrl)}`;
  return affcode ? `${base}&affcode=${encodeURIComponent(affcode)}` : base;
}
