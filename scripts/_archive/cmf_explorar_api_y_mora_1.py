"""
cmf_explorar_api_y_mora.py
===========================
Dos tareas en un solo script:

TAREA 1 — Explorar API CMF: prueba ~30 códigos contables relevantes para
medios de pago y genera un inventario de qué funciona y qué no.

TAREA 2 — Descargar Mora Cartera Consumo: baja los últimos 24 meses de
"Cartera Vencida" y "Morosidad >=90 días" del portal CMF (XLSX mensuales).

Rutas:
  Script  : C:\Dropbox\CMF_API\CMF_Reportes_Excel\
  Output  : C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Output\

Dependencias:
  pip install requests pandas openpyxl
"""

import os
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

# ─── TAREA 1: Explorar API CMF ───────────────────────────────────────────────

# Códigos CNC Bancos 2022 relevantes para medios de pago
# Fuente: articles49972_doc_pdf.xlsx (Códigos para Información Contable Bancos)

CODES_TO_TEST = {
    # ── BALANCE (MB1) — Stock de colocaciones ──
    "140000000": "TOTAL COLOCACIONES (costo amortizado)",
    "145000000": "Colocaciones comerciales",
    "145000100": "Préstamos comerciales",
    "145000200": "Créditos de comercio exterior",
    "145000300": "Deudores en cuentas corrientes (comercial)",
    "145000400": "Operaciones de factoraje",
    "145000500": "Operaciones de leasing comercial",
    "146000000": "Colocaciones para vivienda",
    "148000000": "Colocaciones de consumo",
    "148000100": "Créditos de consumo en cuotas",
    "148000200": "Deudores en cuentas corrientes (consumo)",
    "148000300": "Deudores por tarjetas de crédito ★★★",
    "148000400": "Operaciones de leasing de consumo",

    # ── BALANCE — Provisiones sobre colocaciones ──
    "149000000": "Provisiones sobre colocaciones (total negativo)",
    "149100000": "Provisiones comerciales",
    "149200000": "Provisiones consumo",
    "149300000": "Provisiones vivienda",

    # ── COMPLEMENTARIO (MC1) — Mora y deterioro ──
    # Estos probablemente darán error 80
    "811000000": "Cartera deteriorada total",
    "811400000": "Cartera deteriorada consumo",
    "811400300": "Cartera deteriorada TC consumo",
    "850000000": "Cartera con morosidad total",
    "857000000": "Cartera morosidad >=90d total",
    "857200000": "Mora >=90d comerciales",
    "857200800": "Mora >=90d TC comercial",
    "857300000": "Mora >=90d personas (consumo+vivienda)",
    "857400000": "Mora >=90d consumo",
    "857400300": "Mora >=90d TC consumo ★★★",

    # ── RESULTADOS (MR1) — Ingresos y gastos por tarjetas ──
    "420000000": "Ingresos por comisiones total",
    "420001400": "Comisiones TC recibidas (ingresos)",
    "420001500": "Comisiones TD recibidas (ingresos)",
    "455000000": "Gastos por comisiones total",
    "455001400": "Comisiones TC pagadas (gastos)",
    "455001500": "Comisiones TD pagadas (gastos)",
}


def test_api_code(code, year=2025, month=12):
    """Prueba un código contable en la API CMF y retorna resultado."""
    url = f"{CMF_API_BASE}/balances/{year}/{month:02d}/cuentas/{code}"
    params = {"apikey": CMF_API_KEY, "formato": "JSON"}

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        txt = json.dumps(data)

        # Detectar error 80 (código no disponible)
        if '"Codigo"' in txt and '"80"' in txt:
            return {"status": "ERROR_80", "detail": "Código no disponible vía API"}

        # Detectar datos válidos
        if "MontoTotal" in txt or "Descripcion" in txt:
            # Contar instituciones con datos
            n_inst = txt.count("CodigoInstitucion")
            # Extraer un ejemplo
            sample = txt[:300]
            return {"status": "OK", "n_instituciones": n_inst, "sample": sample}

        return {"status": "UNKNOWN", "detail": txt[:200]}

    except requests.exceptions.HTTPError as e:
        return {"status": "HTTP_ERROR", "detail": str(e)}
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)}


def explorar_api():
    """Prueba todos los códigos y genera inventario."""
    print("\n" + "=" * 80)
    print("TAREA 1: EXPLORACIÓN DE API CMF — CÓDIGOS CONTABLES")
    print("=" * 80)

    results = []
    for code, desc in CODES_TO_TEST.items():
        print(f"  Testing {code} — {desc}...", end=" ", flush=True)
        result = test_api_code(code)
        result["code"] = code
        result["description"] = desc
        results.append(result)

        if result["status"] == "OK":
            print(f"✅ OK ({result.get('n_instituciones', '?')} instituciones)")
        elif result["status"] == "ERROR_80":
            print(f"❌ Error 80 (no disponible)")
        else:
            print(f"⚠️ {result['status']}: {result.get('detail', '')[:80]}")

        time.sleep(0.5)  # Respetar cuota API

    # Guardar inventario
    df = pd.DataFrame(results)
    output_file = OUTPUT_DIR / "api_cmf_codigos_inventario.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n  Inventario guardado en: {output_file}")

    # Resumen
    ok = [r for r in results if r["status"] == "OK"]
    err80 = [r for r in results if r["status"] == "ERROR_80"]
    print(f"\n  RESUMEN: {len(ok)} disponibles, {len(err80)} error 80, {len(results) - len(ok) - len(err80)} otros")
    print(f"  Disponibles:")
    for r in ok:
        print(f"    ✅ {r['code']} — {r['description']}")
    print(f"  No disponibles (error 80):")
    for r in err80:
        print(f"    ❌ {r['code']} — {r['description']}")

    return results


# ─── TAREA 1b: Extraer datos completos de códigos disponibles ─────────────────

def extraer_serie_api(code, desc, year_start=2022, year_end=2026):
    """Extrae la serie completa de un código para todas las instituciones."""
    all_data = []

    for year in range(year_start, year_end + 1):
        for month in range(1, 13):
            if year == 2026 and month > 2:  # No pedir meses futuros
                break

            url = f"{CMF_API_BASE}/balances/{year}/{month:02d}/cuentas/{code}"
            params = {"apikey": CMF_API_KEY, "formato": "JSON"}

            try:
                r = requests.get(url, params=params, timeout=20)
                data = r.json()
                txt = json.dumps(data)

                if '"Codigo"' in txt and '"80"' in txt:
                    continue

                # Parsear la respuesta (estructura varía según endpoint)
                # Buscar lista de instituciones
                if isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    item["_year"] = year
                                    item["_month"] = month
                                    item["_code"] = code
                                    item["_desc"] = desc
                                    all_data.append(item)
                            break
                        elif isinstance(val, dict):
                            for key2, val2 in val.items():
                                if isinstance(val2, list):
                                    for item in val2:
                                        if isinstance(item, dict):
                                            item["_year"] = year
                                            item["_month"] = month
                                            item["_code"] = code
                                            item["_desc"] = desc
                                            all_data.append(item)
                                    break

                print(f"    {year}-{month:02d}: {len([d for d in all_data if d.get('_year')==year and d.get('_month')==month])} registros")

            except Exception as e:
                print(f"    {year}-{month:02d}: ERROR — {e}")

            time.sleep(0.3)

    return all_data


def extraer_codigos_disponibles(api_results):
    """Para cada código que dio OK, extrae la serie completa."""
    ok_codes = [r for r in api_results if r["status"] == "OK"]

    if not ok_codes:
        print("  No hay códigos disponibles para extraer.")
        return

    print(f"\n{'=' * 80}")
    print(f"TAREA 1b: EXTRACCIÓN DE SERIES COMPLETAS ({len(ok_codes)} códigos)")
    print("=" * 80)

    for r in ok_codes:
        code = r["code"]
        desc = r["description"]
        print(f"\n  Extrayendo {code} — {desc}...")

        data = extraer_serie_api(code, desc)

        if data:
            df = pd.DataFrame(data)
            fname = f"api_cmf_{code}_{desc[:30].replace(' ', '_').replace('/', '_')}.xlsx"
            fpath = OUTPUT_DIR / fname
            df.to_excel(fpath, index=False)
            print(f"  → {len(df)} filas guardadas en {fpath}")
        else:
            print(f"  → Sin datos")


# ─── TAREA 2: Descargar Mora Cartera Consumo (XLSX mensuales) ─────────────────

# URLs de los reportes mensuales de mora
# Patrón: cada mes tiene un article ID diferente que hay que descubrir
# Estrategia: scrapear la página de listado para obtener los links

MORA_PAGES = {
    "cartera_vencida": "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28913.html",
    "morosidad_90d": "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28914.html",
}


def obtener_links_mora(url, tipo):
    """Obtiene los links de descarga XLSX desde la página de listado CMF."""
    import re

    print(f"\n  Obteniendo links de {tipo}...")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        html = r.text

        # Buscar links a XLSX (patrón: articles-XXXXX_recurso_1.xlsx)
        # Los links están en la página como enlaces a artículos
        article_ids = re.findall(r'w3-article-(\d+)\.html', html)

        # También buscar nombres de meses para mapear
        meses_encontrados = re.findall(r'>((?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+\d{4})<', html)

        print(f"    Encontrados {len(article_ids)} artículos y {len(meses_encontrados)} meses")

        links = []
        for i, aid in enumerate(article_ids):
            xlsx_url = f"https://www.cmfchile.cl/portal/estadisticas/617/articles-{aid}_recurso_1.xlsx"
            mes = meses_encontrados[i] if i < len(meses_encontrados) else f"unknown_{i}"
            links.append({"article_id": aid, "url": xlsx_url, "periodo": mes, "tipo": tipo})

        return links

    except Exception as e:
        print(f"    ERROR: {e}")
        return []


def descargar_mora_mensual(max_meses=24):
    """Descarga los últimos N meses de reportes de mora."""
    print(f"\n{'=' * 80}")
    print(f"TAREA 2: DESCARGA DE MORA CARTERA CONSUMO (últimos {max_meses} meses)")
    print("=" * 80)

    for tipo, url in MORA_PAGES.items():
        links = obtener_links_mora(url, tipo)

        if not links:
            print(f"  No se encontraron links para {tipo}")
            continue

        # Tomar los últimos max_meses
        links = links[:max_meses]
        print(f"\n  Descargando {len(links)} archivos de {tipo}...")

        for link in links:
            fname = f"{tipo}_{link['periodo'].replace(' ', '_')}_{link['article_id']}.xlsx"
            fpath = MORA_DIR / fname

            if fpath.exists():
                print(f"    ⏭️ Ya existe: {fname}")
                continue

            try:
                r = requests.get(link["url"], timeout=30)
                r.raise_for_status()
                fpath.write_bytes(r.content)
                size_kb = len(r.content) / 1024
                print(f"    ✅ {fname} ({size_kb:.0f} KB)")
            except Exception as e:
                print(f"    ❌ {fname}: {e}")

            time.sleep(1)  # No saturar el servidor

    print(f"\n  Archivos guardados en: {MORA_DIR}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("CMF — Exploración API + Descarga Mora")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Output: {OUTPUT_DIR}")

    # TAREA 1: Explorar API
    api_results = explorar_api()

    # TAREA 1b: Extraer series completas de códigos disponibles
    # Descomentar la siguiente línea para extraer (usa muchas peticiones API):
    # extraer_codigos_disponibles(api_results)

    # TAREA 2: Descargar mora mensual
    descargar_mora_mensual(max_meses=24)

    print("\n" + "=" * 80)
    print("COMPLETADO")
    print("=" * 80)
    print(f"\nArchivos generados:")
    print(f"  1. {OUTPUT_DIR / 'api_cmf_codigos_inventario.xlsx'}")
    print(f"  2. {MORA_DIR}/ (XLSX mensuales de mora)")
    print(f"\nSIGUIENTE PASO:")
    print(f"  Si la exploración muestra códigos ✅, descomentar extraer_codigos_disponibles()")
    print(f"  en el main para extraer las series completas.")
