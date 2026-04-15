# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Two Python ETL tools for CMF Chile (Comisión para el Mercado Financiero) card data:

1. **Consolidator** (`cmf_tarjetas_consolidar_3.py`) — consolidates three CMF Excel reports on credit/debit cards into a single normalized fact table.
2. **Mora** (`cmf_mora_tarjetas_1.py`) — extracts credit/debit card delinquency (mora) and credit risk indicators for the full Chilean market (banking + non-banking).

## Running

```bash
# Consolidator
pip install pandas openpyxl
python cmf_tarjetas_consolidar_3.py
# Input: Data/   Output: Data/CMF_Tarjetas_Consolidado.xlsx

# Mora
pip install requests pandas openpyxl playwright beautifulsoup4
playwright install chromium
python cmf_mora_tarjetas_1.py [YYYY-MM]   # default desde=2022-01
# Input: CMF_Data/   Output: CMF_Output/mora_tarjetas_consolidado.xlsx
```

## File Versions

### Consolidator
| File | Version | Notes |
|------|---------|-------|
| `cmf_tarjetas_consolidar_0.py` | v1.0 | Original |
| `cmf_tarjetas_consolidar_1.py` / `_2.py` | v2.0 | Adds commercial name mapping |
| `cmf_tarjetas_consolidar_3.py` | v3.0 | **Current** — adds group consolidation for M&A, total validation, `Apertura` column |

Always work on `cmf_tarjetas_consolidar_3.py`.

### Mora
| File | Notes |
|------|-------|
| `cmf_mora_tarjetas.py` | v1.0 Original |
| `cmf_mora_tarjetas_1.py` | **Current** |

Always work on `cmf_mora_tarjetas_1.py`.

## Architecture — Consolidator (`cmf_tarjetas_consolidar_3.py`)

**Data flow:** 3 source Excel files → `read_cmf_sheet()` / `read_agg_titadic()` → melt (wide→long) → post-process → validate totals → output.

### Key Functions

- **`read_cmf_sheet(path, sheet, ...)`** — Parses standard CMF sheet layout: title row 0, unit row 1, BEST link row 2, headers row 3, data from row 4+. Melts entity columns into rows.
- **`read_agg_titadic(path, sheet, ...)`** — Reads aggregated sheets with Titular/Adicional/Total columns (no entity breakdown).
- **`safe_read(func, ...)`** — Error wrapper; skips failed sheets and continues.
- **`post_process(df)`** — Normalizes KPI names, extracts `Apertura`, parses `Emisor_Formal`/`Marca` from entity strings (pattern: `" - Tarjeta "`), maps to commercial/group names.
- **`validate_and_fill_totals(df)`** — For each dimension combination: creates `Total = Titular + Adicional` where missing; validates existing totals within tolerance 0.1. Skips percentage KPIs listed in `KPI_SKIP_TOTAL`.

### Output Schema (15 columns)

`Fecha`, `Emisor_Comercial`, `Grupo_Comercial`, `Emisor_Formal`, `Marca`, `Tipo_Institucion`, `Producto`, `Titular_Adicional`, `Apertura`, `Nombre_KPI`, `Unidad`, `Valor_KPI`, `Archivo_Fuente`, `Hoja_Fuente`, `KPI_Original`

### Key Dictionaries (top of file)

- **`NOMBRE_COMERCIAL`** — Maps formal legal entity names → commercial brand names (~50 Chilean institutions).
- **`GRUPO_COMERCIAL`** — Consolidates historical entities post-merger (e.g., Corpbanca → Itaú, BICE → Security).
- **`KPI_NORMALIZE`** — Maps raw CMF KPI names → `(normalized_name, apertura_level)`. Apertura values: `Agregado`, `Emisor`, `Marca`, `Emisor y Marca`, `Tipo Transaccion`.
- **`KPI_SKIP_TOTAL`** — KPIs that are percentages/indices; excluded from Titular+Adicional summation.

### Source Files

Three CMF Excel files in `Data/`:
- `CMF_InformeTrjCreditoBancarias.xlsx` — Banking credit cards → `Producto="Credito"`, `Tipo_Institucion="Financiera"`
- `CMF_InformeTrjCreditoNoBancarias.xlsx` — Non-bank credit cards → `Producto="Credito"`, `Tipo_Institucion="No Financiera"`
- `CMF_InformeTrjDeditoATM.xlsx` — Debit/ATM cards → `Producto="Debito"`/`"ATM"`

---

## Architecture — Mora (`cmf_mora_tarjetas_1.py`)

**Data flow:** Two parallel pipelines → consolidate → Excel output with 3 sheets.

- **Pipeline A (No Bancarias):** Playwright scrapes BEST-CMF portal → extracts non-bank card mora data per entity (CMR Falabella, Ripley, Cencosud, Walmart/CMC, Tricard, Unicard, etc.).
- **Pipeline B (Bancarias):** CMF API (`api.cmfchile.cl`) fetches monthly series using CNC 2022 Chapter C-3 codes.

### Key Functions

- **`scrape_no_bancarias()`** — Playwright headless Chromium → navigates BEST-CMF → extracts largest table → saves raw to `CMF_Data/`. Returns normalized DataFrame.
- **`_normalizar_no_bancarias(df)`** — Fuzzy column rename → computes `indice_mora_pct` if missing.
- **`fetch_serie_banco(codigo, desde, hasta)`** — Single API call for one CNC code; returns DataFrame.
- **`bancarias_via_api(desde)`** — Fetches all `CODIGOS_TC` series, merges on period/bank, computes derived indicators.
- **`consolidar(df_nb, df_b)`** — `pd.concat` of both segments.
- **`guardar_excel(...)`** — Writes 3-sheet Excel: `No_Bancarias`, `Bancarias`, `Mercado_Total`.

### CNC Codes (`CODIGOS_TC`)

| Key | Código | Description |
|-----|--------|-------------|
| `tc_stock_total` | 148000300 | Stock TC consumo — denominador (MB1) |
| `tc_mora_90d_consumo` | 857400300 | Mora ≥90 días TC consumo (MC1) |
| `tc_mora_90d_comercial` | 857200800 | Mora ≥90 días TC comercial (MC1) |
| `tc_deteriorada_consumo` | 811400300 | Cartera deteriorada TC consumo (MC1) |
| `tc_deteriorada_comercial` | 811200800 | Cartera deteriorada TC comercial (MC1) |
| `tc_devengo_susp_consumo` | 812400300 | Devengo suspendido TC consumo (MC1) |
| `tc_castigos_consumo` | 813400300 | Castigos TC consumo (MC1) |
| `tc_recuperaciones_consumo` | 814400300 | Recuperaciones TC consumo (MC1) |

### Derived Indicators

- `indice_mora_90d_pct` = `tc_mora_90d_consumo / tc_stock_total × 100`
- `indice_deteriorada_pct` = `tc_deteriorada_consumo / tc_stock_total × 100`
- `mora_proxy_1_89d_MM` = `tc_deteriorada_consumo − tc_mora_90d_consumo` (proxy; may include renegotiated loans)
- `indice_castigos_pct` = `tc_castigos_consumo / tc_stock_total × 100`

### Output (`CMF_Output/mora_tarjetas_consolidado.xlsx`)

| Sheet | Content |
|-------|---------|
| `No_Bancarias` | Non-bank mora per entity: `periodo`, `entidad`, `n_tarjetas_total`, `n_tarjetas_mora`, `monto_deuda_total_MM`, `monto_mora_MM`, `indice_mora_pct`, `segmento` |
| `Bancarias` | All risk indicators per bank/period (wide format) |
| `Mercado_Total` | Concat of both segments |

### Directories

- `CMF_Data/` — Raw downloads and log (`mora_tarjetas.log`)
- `CMF_Output/` — Final output Excel
