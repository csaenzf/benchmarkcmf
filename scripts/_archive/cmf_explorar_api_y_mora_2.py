"""
cmf_explorar_api_y_mora_2.py
=============================
TAREA 1: Extrae series completas de códigos contables vía API CMF
         (colocaciones consumo/comercial/TC/vivienda por banco)
TAREA 2: Descarga los últimos 24 meses de Cartera Vencida + Mora ≥90d
         (con headers de browser para evitar 403)

Rutas:
  Script : C:\Dropbox\CMF_API\CMF_Reportes_Excel\
  Output : C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Output\

Dependencias: pip install requests pandas openpyxl
"""

import time
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ─── Configuración ────────────────────────────────────────────────────────────

CMF_API_KEY = "9c85ee02885eed933641d8c5389fe410fe6024c6"
CMF_API_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

BASE_DIR = Path(r"C:\Dropbox\CMF_API\CMF_Reportes_Excel")
OUTPUT_DIR = BASE_DIR / "CMF_Output"
MORA_DIR = OUTPUT_DIR / "mora_cartera_mensual"

for d in [OUTPUT_DIR, MORA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Headers de browser para evitar 403 de la CMF
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Referer": "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28913.html",
}

# ═══════════════════════════════════════════════════════════════════════════════
# TAREA 1: EXTRAER SERIES COMPLETAS DE API CMF (COLOCACIONES POR BANCO)
# ═══════════════════════════════════════════════════════════════════════════════

# Códigos disponibles confirmados (solo MB1 — balance)
API_CODES = {
    "148000300": "Deudores_TC",
    "148000100": "Creditos_consumo_cuotas",
    "148000200": "Deudores_CC_consumo",
    "148000000": "Colocaciones_consumo_total",
    "145000000": "Colocaciones_comerciales",
    "146000000": "Colocaciones_vivienda",
    "140000000": "Total_colocaciones",
    "149000000": "Provisiones_total",
}

# Desde qué año extraer (la API tiene data desde ~2008 para periodo3)
YEAR_START = 2015
YEAR_END = 2026
MAX_MONTH_2026 = 2  # Último mes disponible en 2026


def extraer_serie_api(code, label):
    """Extrae serie mensual de un código contable para todas las instituciones."""
    all_rows = []
    errores = 0

    for year in range(YEAR_START, YEAR_END + 1):
        max_m = MAX_MONTH_2026 if year == YEAR_END else 12
        for month in range(1, max_m + 1):
            url = f"{CMF_API_BASE}/balances/{year}/{month:02d}/cuentas/{code}"
            params = {"apikey": CMF_API_KEY, "formato": "JSON"}

            try:
                r = requests.get(url, params=params, timeout=20)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()

                # Navegar la estructura JSON para encontrar las instituciones
                items = _extraer_items(data)

                for item in items:
                    row = {
                        "periodo": f"{year}-{month:02d}",
                        "year": year,
                        "month": month,
                        "codigo_cuenta": code,
                        "cuenta": label,
                    }
                    # Mapear campos comunes de la API
                    for k, v in item.items():
                        if k in ("CodigoInstitucion", "Descripcion", "MontoTotal",
                                 "MonedaChilenaNR", "MonedaReajustableIPC",
                                 "MonedaReajustableTC", "MonedaExtranjera"):
                            row[k] = v
                    all_rows.append(row)

                n = len(items)
                if n > 0:
                    print(f"    {year}-{month:02d}: {n} instituciones")

            except Exception as e:
                errores += 1
                if errores <= 3:
                    print(f"    {year}-{month:02d}: ERROR — {e}")

            time.sleep(0.3)  # Respetar cuota

    return all_rows


def _extraer_items(data):
    """Busca recursivamente la lista de instituciones en el JSON de la API."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                return val
            if isinstance(val, dict):
                result = _extraer_items(val)
                if result:
                    return result
    return []


def tarea1_extraer_colocaciones():
    """Extrae todas las series de colocaciones vía API."""
    print("\n" + "=" * 80)
    print("TAREA 1: EXTRACCIÓN DE COLOCACIONES VÍA API CMF")
    print(f"  Período: {YEAR_START} a {YEAR_END}")
    print(f"  Códigos: {len(API_CODES)}")
    print("=" * 80)

    all_data = []

    for code, label in API_CODES.items():
        print(f"\n  ── {code} — {label} ──")
        rows = extraer_serie_api(code, label)
        all_data.extend(rows)
        print(f"  Total: {len(rows)} filas")

    if all_data:
        df = pd.DataFrame(all_data)
        output_file = OUTPUT_DIR / "api_cmf_colocaciones_por_banco.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\n  ✅ Guardado: {output_file}")
        print(f"  Total: {len(df)} filas, {df['cuenta'].nunique()} cuentas, "
              f"{df['periodo'].nunique()} períodos")

        # Resumen por cuenta
        print("\n  Resumen por cuenta:")
        for cuenta, grp in df.groupby("cuenta"):
            periodos = grp["periodo"].nunique()
            bancos = grp["Descripcion"].nunique() if "Descripcion" in grp.columns else "?"
            print(f"    {cuenta}: {periodos} meses × {bancos} bancos = {len(grp)} filas")
    else:
        print("\n  ❌ No se extrajeron datos")


# ═══════════════════════════════════════════════════════════════════════════════
# TAREA 2: DESCARGAR MORA CARTERA CONSUMO (XLSX MENSUALES)
# ═══════════════════════════════════════════════════════════════════════════════

# Article IDs extraídos del portal CMF el 2026-04-08 vía browser
MORA_ARTICLES = {
    "cartera_vencida": [
        ("109115", "2026-02"), ("103971", "2026-01"), ("103185", "2025-12"),
        ("102407", "2025-11"), ("101096", "2025-10"), ("100155", "2025-09"),
        ("99053", "2025-08"), ("98092", "2025-07"), ("97057", "2025-06"),
        ("96043", "2025-05"), ("94891", "2025-04"), ("93985", "2025-03"),
        ("92946", "2025-02"), ("92041", "2025-01"), ("90812", "2024-12"),
        ("89894", "2024-11"), ("88767", "2024-10"), ("87888", "2024-09"),
        ("86919", "2024-08"), ("85837", "2024-07"), ("84777", "2024-06"),
        ("83788", "2024-05"), ("82638", "2024-04"), ("81806", "2024-03"),
    ],
    "morosidad_90d": [
        ("109116", "2026-02"), ("103972", "2026-01"), ("103187", "2025-12"),
        ("102408", "2025-11"), ("101097", "2025-10"), ("100156", "2025-09"),
        ("99054", "2025-08"), ("98093", "2025-07"), ("97058", "2025-06"),
        ("96044", "2025-05"), ("94892", "2025-04"), ("93986", "2025-03"),
        ("92947", "2025-02"), ("92042", "2025-01"), ("90813", "2024-12"),
        ("89895", "2024-11"), ("88768", "2024-10"), ("87889", "2024-09"),
        ("86920", "2024-08"), ("85838", "2024-07"), ("84778", "2024-06"),
        ("83789", "2024-05"), ("82639", "2024-04"), ("81807", "2024-03"),
    ],
}


def tarea2_descargar_mora():
    """Descarga los XLSX mensuales de mora con headers de browser."""
    print(f"\n{'=' * 80}")
    print(f"TAREA 2: DESCARGA DE MORA CARTERA (24 meses × 2 reportes)")
    print("=" * 80)

    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    descargados = 0
    errores = 0

    for tipo, articles in MORA_ARTICLES.items():
        print(f"\n  ── {tipo} ({len(articles)} meses) ──")

        for article_id, periodo in articles:
            fname = f"{tipo}_{periodo}_{article_id}.xlsx"
            fpath = MORA_DIR / fname

            if fpath.exists():
                print(f"    ⏭️  {periodo} — ya existe")
                continue

            url = f"https://www.cmfchile.cl/portal/estadisticas/617/articles-{article_id}_recurso_1.xlsx"

            try:
                r = session.get(url, timeout=30)
                r.raise_for_status()

                if len(r.content) < 1000:
                    print(f"    ⚠️  {periodo} — archivo muy pequeño ({len(r.content)} bytes), posible error")
                    errores += 1
                    continue

                fpath.write_bytes(r.content)
                size_kb = len(r.content) / 1024
                print(f"    ✅  {periodo} — {size_kb:.0f} KB")
                descargados += 1

            except requests.exceptions.HTTPError as e:
                print(f"    ❌  {periodo} — HTTP {e.response.status_code}")
                errores += 1
            except Exception as e:
                print(f"    ❌  {periodo} — {e}")
                errores += 1

            time.sleep(1)

    print(f"\n  Resumen: {descargados} descargados, {errores} errores")
    print(f"  Guardados en: {MORA_DIR}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("CMF — Extracción API + Descarga Mora v2")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Output: {OUTPUT_DIR}")

    # TAREA 1: Extraer colocaciones por banco vía API
    # (usa ~1,000 peticiones API — cuidado con cuota de 10K/mes)
    tarea1_extraer_colocaciones()

    # TAREA 2: Descargar mora mensual con headers
    tarea2_descargar_mora()

    print("\n" + "=" * 80)
    print("COMPLETADO")
    print("=" * 80)
    print(f"\nArchivos generados:")
    print(f"  1. {OUTPUT_DIR / 'api_cmf_colocaciones_por_banco.xlsx'}")
    print(f"  2. {MORA_DIR}/ ({len(MORA_ARTICLES['cartera_vencida']) + len(MORA_ARTICLES['morosidad_90d'])} XLSX)")
