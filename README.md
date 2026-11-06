# clothefinder (Taobao · Weidian · 1688 · Yupoo)

Web estática: no necesita servidor propio. Se publica gratis en Vercel, Netlify o GitHub Pages.

## Archivos
- `index.html`, `css/styles.css`, `js/app.js` — la web (búsqueda con sinónimos, filtros, QC, botón KakoBuy).
- `js/links.js` — convierte links de agentes al link original y arma el link de KakoBuy.
- `data/products.json` — todos los productos. Los que tienen `"demo": true` son ejemplos y se borran al cargar los reales.
- `tools/update_prices.py` — revisa los precios en cada proveedor.
- `.github/workflows/precios.yml` — corre el script de precios todos los días y guarda los cambios.

## Ver en tu compu
```bash
python3 -m http.server 5173
```
Después abrí http://localhost:5173

## Formato de un producto
```json
{
  "id": "wd-7234",
  "title": "Campera Corteiz negra con capucha",
  "brand": "Corteiz",
  "category": "Ropa",          // Ropa | Zapatillas | Accesorios
  "type": "Campera",
  "color": "Negro",
  "tags": ["windbreaker"],
  "image": "https://...jpg",
  "qc": ["https://...qc1.jpg", "https://...qc2.jpg"],
  "source": "weidian",         // taobao | weidian | 1688 | yupoo
  "url": "https://weidian.com/item.html?itemID=7234",
  "price_cny": 189,
  "price_checked": "2026-11-06T00:00:00Z",
  "added": "2026-11-06"
}
```

## Precios
- El dólar se calcula en vivo con el tipo de cambio del día (open.er-api.com).
- El precio en ¥ lo actualiza `tools/update_prices.py`: Weidian y Yupoo funcionan bien; Taobao y 1688 suelen bloquear bots, así que en esos casos se mantiene el último precio conocido y la tarjeta muestra cuándo se verificó por última vez.
