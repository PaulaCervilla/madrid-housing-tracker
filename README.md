# Madrid Housing Tracker

Seguidor de los precios públicos de vivienda en la **Comunidad de Madrid**
—compra y alquiler— combinado con datos de salario medio e IPC para
calcular cuánto **esfuerzo en años de ahorro** cuesta hoy comprar una
vivienda con un sueldo medio.

Genera un **dashboard HTML interactivo** autocontenido (`output/dashboard.html`)
con gráficos y una calculadora de asequibilidad ajustable.

### 🔗 [Ver el dashboard online](https://PaulaCervilla.github.io/madrid-housing-tracker/)

> El dashboard se reconstruye automáticamente con cada `push` a `main` y
> una vez al mes para recoger nuevos datos del INE
> (ver [`.github/workflows/pages.yml`](.github/workflows/pages.yml)).

## Datos

Todo viene de fuentes públicas, sin API key:

| Serie | Fuente | Tabla INE |
|---|---|---|
| Índice de Precios de Vivienda (IPV, compra) | INE | `25171` |
| Índice de Precios de Alquiler (IPVA)        | INE | `59061` |
| Índice de Precios de Consumo (IPC)          | INE | `50902` |
| Salario medio anual bruto (EAES)            | INE | `28192` |

Las cifras absolutas en €/m² se anclan a los valores medios públicos de
Madrid en 2015 (Mitma) y se proyectan hacia adelante con los índices del
INE — son **estimaciones de tendencia**, no tasaciones.

## Cómo ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Lanza el pipeline completo (descarga + transforma + dashboard)
python -m src.pipeline

# Tests
pytest -q
```

Cuando termine, abre `output/dashboard.html` en el navegador.

## Estructura

```
madrid-housing-tracker/
├── config.py                 # endpoints, códigos de tabla, supuestos
├── src/
│   ├── pipeline.py           # orquestador end-to-end
│   ├── extractors/
│   │   ├── http_client.py    # GET con reintentos
│   │   └── ine.py            # parser JSON-stat 2.0
│   ├── transformers/
│   │   ├── cleaner.py        # filtro región + serie general
│   │   └── affordability.py  # ratio precio/sueldo, años de ahorro
│   ├── loaders/
│   │   └── storage.py        # CSV + SQLite
│   └── visualizations/
│       └── dashboard.py      # HTML + Plotly + calculadora JS
├── data/                     # CSVs y SQLite generados
├── output/                   # dashboard.html generado
└── tests/
```

## Ratio de esfuerzo — qué calcula

Para cada año:

- `price_per_m2` = anclaje 2015 (€/m²) × IPV / IPV(2015)
- `purchase_price` = `price_per_m2` × tamaño vivienda (80 m² por defecto)
- `price_to_income` = `purchase_price` / sueldo bruto anual
- `years_to_down_payment` = `purchase_price` × 20% / (sueldo neto × 20%)
- `years_to_full_purchase` = `purchase_price` / (sueldo neto × 20%)

Los porcentajes (entrada, % de ahorro, tamaño de la vivienda y año) se
pueden cambiar en vivo desde la calculadora del dashboard.
