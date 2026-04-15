"""
cmf_mora_tarjetas.py
====================
Extrae mora de tarjetas de crédito del mercado chileno completo:

  Pipeline A — No bancarias (retail):
      BEST-CMF → Reportes Integrados → Tarjetas no bancarias
      Incluye mora directamente por entidad (CMR Falabella, Ripley, CMC/Walmart,
      Cencosud, Tricard, Unicard, etc.)

  Pipeline B — Bancarias:
      CMF portal → "Reporte de Cartera Vencida del Sistema Bancario" (Excel mensual)
      Contiene colocaciones vencidas desagregadas por banco y tipo de cartera;
      se filtra la hoja/columna correspondiente a tarjetas de crédito de consumo.

Salida:
  mora_tarjetas_consolidado.xlsx   ← hoja "No_Bancarias" + hoja "Bancarias" + hoja "Mercado_Total"

Dependencias:
  pip install requests pandas openpyxl playwright
  playwright install chromium
"""

import re
import io
import time
import logging
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ─── Configuración ────────────────────────────────────────────────────────────

CMF_API_KEY = "9c85ee02885eed933641d8c5389fe410fe6024c6"
OUTPUT_FILE = Path("mora_tarjetas_consolidado.xlsx")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("mora_tarjetas")

# ─── PIPELINE A: No bancarias (BEST-CMF vía Playwright) ──────────────────────

BEST_URL = "https://www.best-cmf.cl/best-cmf/#!/reportesintegrados"

# Después de cargar BEST-CMF, los reportes de tarjetas no bancarias están en
# la sección "Reportes Integrados".  El script navega hasta el reporte
# "Tarjetas de Crédito No Bancarias" y descarga el Excel más reciente.
# Si BEST cambia su estructura Angular, ajustar los selectores.

def scrape_no_bancarias() -> pd.DataFrame:
    """
    Usa Playwright para navegar BEST-CMF, encontrar el reporte de
    tarjetas no bancarias y descargar el Excel con mora por entidad.
    Retorna un DataFrame con columnas:
        periodo, entidad, n_tarjetas_total, n_tarjetas_mora,
        monto_deuda_total_MM, monto_mora_MM, indice_mora_pct
    """
    log.info("=== Pipeline A: No bancarias → BEST-CMF ===")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        log.info("Cargando BEST-CMF...")
        page.goto(BEST_URL, timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=60_000)

        # Buscar el menú o enlace de "Tarjetas No Bancarias"
        # En la SPA Angular de BEST, los reportes están en el menú lateral.
        # Se busca el texto que contenga "Tarjetas" y "no bancarias" (case-insensitive).
        try:
            selector = "text=Tarjetas de Crédito No Bancarias"
            page.locator(selector).first.click(timeout=15_000)
            time.sleep(3)
            log.info("Navegó a reporte de tarjetas no bancarias.")
        except Exception:
            log.warning("No se encontró el enlace exacto; intentando búsqueda ampliada.")
            # Alternativa: listar todos los elementos de menú y buscar el más cercano
            links = page.locator("a, li, span").all_text_contents()
            matches = [l for l in links if "tarjeta" in l.lower() and "no bancari" in l.lower()]
            log.info(f"Opciones encontradas en menú: {matches[:10]}")

        # Esperar que cargue la tabla o el botón de descarga
        time.sleep(5)

        # Intentar clic en botón de descarga Excel
        try:
            page.locator("button:has-text('Excel'), a:has-text('Excel'), button:has-text('Descargar')").first.click(timeout=10_000)
            time.sleep(4)
            log.info("Clic en descarga Excel realizado.")
        except Exception as e:
            log.warning(f"No se encontró botón de descarga: {e}")

        # Si BEST no permite descarga directa, extraemos la tabla del DOM
        log.info("Extrayendo tabla del DOM...")
        html = page.content()
        browser.close()

    # Parsear la tabla HTML con pandas
    tables = pd.read_html(io.StringIO(html))
    if not tables:
        log.error("No se encontraron tablas en BEST-CMF. Verificar selectores.")
        return pd.DataFrame()

    # La tabla de mora suele ser la más grande; heurística: la que tiene más columnas
    df = max(tables, key=lambda t: t.shape[1])
    log.info(f"Tabla extraída: {df.shape[0]} filas × {df.shape[1]} columnas")
    log.info(f"Columnas: {list(df.columns)}")

    # Normalizar: detectar columnas de mora automáticamente
    df = _normalizar_no_bancarias(df)
    return df


def _normalizar_no_bancarias(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intenta mapear las columnas raw del reporte BEST a un esquema estándar.
    Ajustar los nombres según lo que realmente traiga el reporte.
    """
    df.columns = [str(c).strip().lower() for c in df.columns]

    rename_map = {}
    for col in df.columns:
        if "entidad" in col or "instituc" in col or "emisor" in col:
            rename_map[col] = "entidad"
        elif "período" in col or "periodo" in col or "mes" in col or "fecha" in col:
            rename_map[col] = "periodo"
        elif "mora" in col and ("n°" in col or "número" in col or "num" in col):
            rename_map[col] = "n_tarjetas_mora"
        elif "total" in col and ("n°" in col or "número" in col or "tarjeta" in col):
            rename_map[col] = "n_tarjetas_total"
        elif "mora" in col and ("monto" in col or "$" in col or "deuda" in col):
            rename_map[col] = "monto_mora_MM"
        elif "monto" in col and "total" in col:
            rename_map[col] = "monto_deuda_total_MM"

    df = df.rename(columns=rename_map)

    # Calcular índice de mora si no viene calculado
    if "indice_mora_pct" not in df.columns:
        if "monto_mora_MM" in df.columns and "monto_deuda_total_MM" in df.columns:
            df["indice_mora_pct"] = (
                pd.to_numeric(df["monto_mora_MM"], errors="coerce") /
                pd.to_numeric(df["monto_deuda_total_MM"], errors="coerce") * 100
            ).round(2)

    df["segmento"] = "No Bancaria"
    return df


# ─── PIPELINE B: Bancarias (Reporte de Cartera Vencida CMF) ──────────────────

CMF_STATS_BASE = "https://www.cmfchile.cl/portal/estadisticas/617"

# El "Reporte de Cartera Vencida del Sistema Bancario" se publica mensualmente.
# Se accede al listado de la página de estadísticas y se descarga el Excel más reciente.

def get_cartera_vencida_url() -> str | None:
    """
    Encuentra la URL del Excel más reciente del Reporte de Cartera Vencida.
    Estrategia: buscar en la página de prensa/estadísticas el enlace con ese nombre.
    """
    log.info("Buscando URL del Reporte de Cartera Vencida más reciente...")

    # Página principal de estadísticas de bancos
    search_urls = [
        "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28911.html",  # Reportes mensuales
        "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28914.html",  # Mora 90 días
    ]

    for url in search_urls:
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True).lower()
                if ("cartera vencida" in text or "cartera_vencida" in href.lower()) and (
                    href.endswith(".xls") or href.endswith(".xlsx")
                ):
                    full_url = href if href.startswith("http") else f"https://www.cmfchile.cl{href}"
                    log.info(f"Encontrado: {full_url}")
                    return full_url
        except Exception as e:
            log.warning(f"Error accediendo {url}: {e}")

    # Fallback: construir la URL del Excel del mes actual directamente
    # El patrón habitual de CMF es:
    # https://www.cmfchile.cl/portal/estadisticas/617/articles-XXXXXX_recurso_1.xlsx
    # Como no podemos inferir el ID, intentamos la API de series
    log.warning("No se encontró URL directa. Intentando descarga vía API CMF.")
    return None


def download_cartera_vencida_excel(url: str) -> pd.ExcelFile | None:
    """Descarga el Excel de Cartera Vencida y lo retorna como ExcelFile."""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return pd.ExcelFile(io.BytesIO(r.content))
    except Exception as e:
        log.error(f"Error descargando Excel: {e}")
        return None


def extraer_tarjetas_bancarias(xf: pd.ExcelFile) -> pd.DataFrame:
    """
    Procesa el Excel de Cartera Vencida y extrae los datos de tarjetas de crédito.

    Estructura típica del reporte CMF:
      - Varias hojas por tipo de cartera o vista del sistema
      - Columnas: banco, consumo_total_vigente, consumo_total_vencida,
                  consumo_tarjetas_vigente, consumo_tarjetas_vencida, etc.

    Si las columnas tienen otro nombre, se imprime el inventario para ajuste manual.
    """
    log.info(f"Hojas disponibles en el Excel: {xf.sheet_names}")

    # Buscar la hoja que contenga datos de consumo/tarjetas
    hoja_objetivo = None
    for sheet in xf.sheet_names:
        nombre = sheet.lower()
        if any(kw in nombre for kw in ["tarjeta", "consumo", "vencida", "sistema"]):
            hoja_objetivo = sheet
            break

    if not hoja_objetivo:
        hoja_objetivo = xf.sheet_names[0]
        log.warning(f"No se identificó hoja específica de tarjetas; usando '{hoja_objetivo}'")

    df = xf.parse(hoja_objetivo)
    log.info(f"Columnas en hoja '{hoja_objetivo}': {list(df.columns)}")

    # ── Detección automática de columnas relevantes ──────────────────────────
    cols_lower = {str(c).lower(): c for c in df.columns}

    def buscar_col(*keywords) -> str | None:
        for col_l, col_orig in cols_lower.items():
            if all(kw in col_l for kw in keywords):
                return col_orig
        return None

    col_banco      = buscar_col("banco") or buscar_col("instituc") or buscar_col("entidad")
    col_periodo    = buscar_col("período") or buscar_col("periodo") or buscar_col("mes") or buscar_col("fecha")
    col_tc_vencida = (
        buscar_col("tarjeta", "vencida") or
        buscar_col("tarjeta", "mora")    or
        buscar_col("consumo", "tarjeta", "vencida")
    )
    col_tc_vigente = (
        buscar_col("tarjeta", "vigente") or
        buscar_col("consumo", "tarjeta", "vigente")
    )

    log.info(f"Columnas mapeadas → banco={col_banco}, periodo={col_periodo}, "
             f"tc_vencida={col_tc_vencida}, tc_vigente={col_tc_vigente}")

    if not col_tc_vencida:
        log.error(
            "No se encontró columna de tarjetas de crédito vencidas. "
            "Revisa el inventario de columnas arriba e indica cuál usar."
        )
        # Retornar el DataFrame crudo para inspección manual
        df["segmento"] = "Bancaria"
        return df

    # ── Construir DataFrame normalizado ──────────────────────────────────────
    resultado = pd.DataFrame()

    if col_banco:
        resultado["entidad"] = df[col_banco]
    if col_periodo:
        resultado["periodo"] = df[col_periodo]

    resultado["monto_tc_vigente_MM"]  = pd.to_numeric(df.get(col_tc_vigente),  errors="coerce") if col_tc_vigente  else None
    resultado["monto_tc_vencida_MM"]  = pd.to_numeric(df[col_tc_vencida],      errors="coerce")

    if col_tc_vigente:
        resultado["indice_mora_pct"] = (
            resultado["monto_tc_vencida_MM"] /
            (resultado["monto_tc_vigente_MM"] + resultado["monto_tc_vencida_MM"]) * 100
        ).round(2)

    resultado["segmento"] = "Bancaria"
    return resultado.dropna(subset=["monto_tc_vencida_MM"])


# ─── PIPELINE B Fallback: API CMF con códigos contables ──────────────────────

# Códigos del CNC 2022 para tarjetas de crédito (Capítulo C-3).
# La estructura del plan de cuentas es:
#   13030.02.XX  → Colocaciones consumo TARJETAS vigentes (por banco)
#   13035.02.XX  → Colocaciones consumo TARJETAS vencidas (por banco)
# Nota: confirmar los códigos exactos descargando el CNC 2022 Capítulo C-3
# desde https://www.cmfchile.cl/portal/principal/613/w3-propertyvalue-29911.html

CODIGOS_TARJETAS = {
    "tc_vigentes": "13030020000",   # Ajustar si el código exacto difiere
    "tc_vencidas": "13035020000",   # Ídem
}

CMF_API_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos"


def fetch_serie_banco(codigo: str, desde: str = "2022-01", hasta: str = None) -> pd.DataFrame:
    """
    Descarga una serie estadística de la API CMF para todos los bancos.
    Parámetros:
        codigo : código contable del CNC (9 dígitos sin puntos)
        desde  : "YYYY-MM"
        hasta  : "YYYY-MM"  (por defecto: mes actual)
    """
    if hasta is None:
        hasta = datetime.now().strftime("%Y-%m")

    url = (
        f"{CMF_API_BASE}/bancos/series"
        f"?codigoSerie={codigo}&fechaDesde={desde}&fechaHasta={hasta}"
        f"&apikey={CMF_API_KEY}&formato=json"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        # La respuesta tiene estructura: {"Series": [{"Periodo": ..., "Valor": ...}, ...]}
        registros = data.get("Series", data.get("series", []))
        df = pd.DataFrame(registros)
        df.columns = [c.lower() for c in df.columns]
        df["codigo"] = codigo
        return df
    except Exception as e:
        log.warning(f"API CMF error para código {codigo}: {e}")
        return pd.DataFrame()


def bancarias_via_api(desde: str = "2022-01") -> pd.DataFrame:
    """Fallback: extrae tarjetas vencidas/vigentes bancarias via API CMF."""
    log.info("=== Pipeline B Fallback: Bancarias → API CMF ===")
    frames = {}
    for nombre, codigo in CODIGOS_TARJETAS.items():
        log.info(f"Descargando serie {nombre} (código {codigo})...")
        df = fetch_serie_banco(codigo, desde=desde)
        if not df.empty:
            frames[nombre] = df
            log.info(f"  {len(df)} registros obtenidos.")
        else:
            log.warning(f"  Serie vacía. Verifica el código {codigo} en el CNC 2022.")

    if len(frames) < 2:
        log.error(
            "No se obtuvieron las dos series necesarias. "
            "Descarga el CNC 2022 (Capítulo C-3) y confirma los códigos contables de tarjetas."
        )
        return pd.DataFrame()

    vigentes = frames["tc_vigentes"].rename(columns={"valor": "monto_tc_vigente_MM"})
    vencidas  = frames["tc_vencidas"].rename(columns={"valor": "monto_tc_vencida_MM"})

    merge_cols = [c for c in ["periodo", "banco", "codigobanco"] if c in vigentes.columns and c in vencidas.columns]
    df = vigentes.merge(vencidas[merge_cols + ["monto_tc_vencida_MM"]], on=merge_cols, how="outer")
    df["indice_mora_pct"] = (
        pd.to_numeric(df["monto_tc_vencida_MM"], errors="coerce") /
        (pd.to_numeric(df["monto_tc_vigente_MM"], errors="coerce") +
         pd.to_numeric(df["monto_tc_vencida_MM"], errors="coerce")) * 100
    ).round(2)
    df["segmento"] = "Bancaria"
    return df


# ─── Consolidación final ──────────────────────────────────────────────────────

def consolidar(df_no_banc: pd.DataFrame, df_banc: pd.DataFrame) -> pd.DataFrame:
    """Unifica ambos DataFrames en un único fact table de mora de tarjetas."""
    frames = []
    if not df_no_banc.empty:
        frames.append(df_no_banc)
    if not df_banc.empty:
        frames.append(df_banc)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def guardar_excel(df_no_banc: pd.DataFrame, df_banc: pd.DataFrame, df_total: pd.DataFrame):
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        if not df_no_banc.empty:
            df_no_banc.to_excel(writer, sheet_name="No_Bancarias", index=False)
        if not df_banc.empty:
            df_banc.to_excel(writer, sheet_name="Bancarias", index=False)
        if not df_total.empty:
            df_total.to_excel(writer, sheet_name="Mercado_Total", index=False)
    log.info(f"Archivo guardado: {OUTPUT_FILE.resolve()}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # ── Pipeline A: No bancarias ─────────────────────────────────────────────
    df_no_banc = pd.DataFrame()
    try:
        df_no_banc = scrape_no_bancarias()
        log.info(f"No bancarias: {len(df_no_banc)} registros.")
    except Exception as e:
        log.error(f"Error en Pipeline A (no bancarias): {e}")

    # ── Pipeline B: Bancarias ────────────────────────────────────────────────
    df_banc = pd.DataFrame()
    try:
        url_excel = get_cartera_vencida_url()
        if url_excel:
            xf = download_cartera_vencida_excel(url_excel)
            if xf:
                df_banc = extraer_tarjetas_bancarias(xf)
                log.info(f"Bancarias (Excel): {len(df_banc)} registros.")

        if df_banc.empty:
            log.info("Intentando fallback vía API CMF...")
            df_banc = bancarias_via_api(desde="2022-01")
            log.info(f"Bancarias (API): {len(df_banc)} registros.")
    except Exception as e:
        log.error(f"Error en Pipeline B (bancarias): {e}")

    # ── Consolidación ────────────────────────────────────────────────────────
    df_total = consolidar(df_no_banc, df_banc)
    guardar_excel(df_no_banc, df_banc, df_total)

    # ── Resumen de cobertura ─────────────────────────────────────────────────
    print("\n" + "="*60)
    print("COBERTURA FINAL DE MORA DE TARJETAS")
    print("="*60)
    for seg in ["No Bancaria", "Bancaria"]:
        sub = df_total[df_total["segmento"] == seg] if "segmento" in df_total.columns else pd.DataFrame()
        n_entidades = sub["entidad"].nunique() if "entidad" in sub.columns else 0
        print(f"  {seg:15s} → {len(sub):5d} registros  |  {n_entidades} entidades")
    print(f"\n  TOTAL         → {len(df_total):5d} registros")
    print(f"  Archivo: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()
