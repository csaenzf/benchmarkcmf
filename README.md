# BenchmarkCMF — Competitive Intelligence Dashboard

Dashboard interactivo de inteligencia competitiva para Banco de Chile en tarjetas de crédito y débito, contra los 5 principales bancos del mercado chileno. Data pública CMF.

- Dominio: benchmarkcmf.cl
- Deploy: Cloudflare Pages + Cloudflare Access (OTP)
- Período actual: Diciembre 2025

## Estructura

```
BenchmarkCMF/
├── scripts/                        # Pipelines ETL y generadores
│   ├── cmf_tarjetas_consolidar.py  # Consolida 3 Excel CMF → fact table normalizada
│   ├── cmf_mora_tarjetas.py        # Scrape + API CMF → indicadores de mora
│   ├── cmf_explorar_api_y_mora.py  # Exploración cartera/morosidad por banco
│   ├── generar_dashboard.py        # Genera dashboard/index.html standalone
│   └── _archive/                   # Versiones anteriores
│
├── data/
│   ├── manual/                     # Inputs CMF descargados manualmente (xlsx)
│   ├── raw/                        # Descargas automatizadas (Playwright/API)
│   ├── processed/                  # Outputs consolidados
│   │   └── mora_cartera_mensual/   # Series históricas cartera vencida / mora 90d
│   ├── mora/                       # Data exploratoria BEST-CMF
│   └── context/                    # Documentación de referencia CMF (circulares, manuales)
│
├── dashboard/
│   ├── index.html                  # Dashboard standalone (React + Chart.js CDN)
│   └── _archive/                   # Versiones anteriores
│
├── website/                        # Landing + assets (logos, portada, video)
│
├── docs/                           # Documentación del proyecto
│
├── CLAUDE.md                       # Instrucciones para Claude
├── .gitignore
└── README.md
```

## Pipeline de actualización

1. Descargar los 3 reportes CMF manualmente → `data/manual/`
   - `CMF_InformeTrjCreditoBancarias.xlsx`
   - `CMF_InformeTrjCreditoNoBancarias.xlsx`
   - `CMF_InformeTrjDeditoATM.xlsx`
2. Consolidar:
   ```bash
   cd scripts
   python cmf_tarjetas_consolidar.py
   # Output: data/processed/CMF_Tarjetas_Consolidado.xlsx
   ```
3. (Opcional) Actualizar mora:
   ```bash
   python cmf_mora_tarjetas.py
   # Output: data/processed/mora_tarjetas_consolidado.xlsx
   ```
4. Regenerar dashboard:
   ```bash
   python generar_dashboard.py
   # Output: dashboard/index.html
   ```
5. Deploy a Cloudflare Pages (drag&drop de `dashboard/` o `git push`).

## Dependencias

```bash
pip install pandas openpyxl requests beautifulsoup4 playwright
playwright install chromium
```

## Bancos analizados

| Banco | Color |
|-------|-------|
| Banco de Chile | `#0033A0` |
| Santander | `#EC0000` |
| BCI | `#FF6900` |
| BancoEstado | `#00843D` |
| Itaú | `#003DA5` |
| Scotiabank | `#B4272A` |

## Data source

CMF Chile — API pública + reportes manuales del portal BEST-CMF. Ver `data/context/` para las circulares y manuales técnicos CMF relevantes.
