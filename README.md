# Madrid Housing Tracker

Seguidor de los precios públicos de vivienda en la **Comunidad de Madrid**
—compra y alquiler— combinado con datos de salario medio e IPC para
calcular cuánto **esfuerzo en años de ahorro** cuesta hoy comprar una
vivienda con un sueldo medio.

Genera un **dashboard HTML interactivo** autocontenido (`output/dashboard.html`)
con gráficos, una calculadora de asequibilidad ajustable y otra calculadora
personal en la que introduces tu sueldo, ahorros y vivienda objetivo para
ver en cuántos años podrías comprarla.

### 🔗 [Ver el dashboard online](https://PaulaCervilla.github.io/madrid-housing-tracker/)

> Se reconstruye automáticamente con cada `push` a `main`, manualmente
> desde la pestaña Actions, y el día 1 de cada mes vía cron para recoger
> nuevos datos del INE
> (ver [`.github/workflows/pages.yml`](.github/workflows/pages.yml)).

## Datos

Todo viene de fuentes públicas, sin API key:

| Serie | Fuente | Tabla INE |
|---|---|---|
| Índice de Precios de Vivienda (IPV, compra) | INE | `25171` |
| Índice de Precios de Alquiler (IPVA)        | INE | `59061` |
| Índice de Precios de Consumo (IPC)          | INE | `50902` |
| Salario medio anual bruto (EAES)            | INE | `28192` |

El pipeline intenta primero la API en vivo del INE y, si falla (red, 5xx,
cambio de esquema…), cae automáticamente a los CSVs cacheados en
[`data/seed/`](data/seed/) — así el dashboard siempre se reconstruye.
Para forzar el modo seed-only, exporta `USE_SEED_DATA=1` antes de lanzar
el pipeline.

Las cifras absolutas en €/m² se anclan a los valores medios públicos de
Madrid en 2015 (Mitma) y se proyectan hacia adelante con los índices del
INE — son **estimaciones de tendencia**, no tasaciones.

## Cómo ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Pipeline completo (descarga del INE + transforma + dashboard)
python -m src.pipeline

# Sin llamadas de red, usando los CSVs incluidos en data/seed/
$env:USE_SEED_DATA="1"; python -m src.pipeline

# Tests
pytest -q
```

Cuando termine, abre `output/dashboard.html` en el navegador.

## Estructura

```
madrid-housing-tracker/
├── config.py                       # endpoints, códigos de tabla, supuestos
├── src/
│   ├── pipeline.py                 # orquestador end-to-end (con fallback)
│   ├── extractors/
│   │   ├── http_client.py          # GET con reintentos
│   │   ├── ine.py                  # parser JSON-stat 2.0
│   │   └── seed.py                 # fallback a CSVs cacheados
│   ├── transformers/
│   │   ├── cleaner.py              # filtro región + serie general
│   │   └── affordability.py        # ratio precio/sueldo, años de ahorro
│   ├── loaders/
│   │   └── storage.py              # CSV + SQLite
│   └── visualizations/
│       └── dashboard.py            # HTML + Plotly + 2 calculadoras JS
├── data/
│   └── seed/                       # CSVs cacheados para fallback offline
├── output/                         # dashboard.html generado
├── tests/
└── .github/workflows/
    ├── ci.yml                      # tests en cada push / PR
    └── pages.yml                   # build + deploy a GitHub Pages
```

## Ratio de esfuerzo — qué calcula

Para cada año, el pipeline deriva:

- `price_per_m2` = anclaje 2015 (€/m²) × IPV / IPV(2015)
- `purchase_price` = `price_per_m2` × tamaño vivienda (80 m² por defecto)
- `price_to_income` = `purchase_price` / sueldo bruto anual
- `rent_burden` = alquiler anual / sueldo bruto anual
- `years_to_down_payment` = entrada (20%) / (sueldo neto × 20% ahorro)
- `years_to_full_purchase` = precio total / (sueldo neto × 20% ahorro)

Y el dashboard incluye dos calculadoras:

1. **Calculadora de esfuerzo** — sliders sobre los datos agregados de la
   Comunidad de Madrid (año, tamaño, % ahorro, % entrada).
2. **Tu situación personal** — inputs reales (sueldo, ahorrado, precio
   objetivo, alquiler actual) que devuelven en cuántos años podrías
   reunir la entrada y comprar la vivienda. Todo se calcula en el
   navegador, no se envía nada.
