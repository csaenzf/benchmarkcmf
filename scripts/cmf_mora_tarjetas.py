"""
cmf_mora_tarjetas_1.py
======================
Extrae todos los indicadores de mora y riesgo crediticio de tarjetas de crédito
del mercado chileno completo (bancarias + no bancarias).

Rutas:
  Script  : C:\\Dropbox\\CMF_API\\CMF_Reportes_Excel\\
  Data    : C:\\Dropbox\\CMF_API\\CMF_Reportes_Excel\\CMF_Data\\
  Output  : C:\\Dropbox\\CMF_API\\CMF_Reportes_Excel\\CMF_Output\\

Pipeline A — No bancarias (retail financiero):
  BEST-CMF → catálogo → "Informe de tarjetas de crédito no bancarias"
  (CMR Falabella, Ripley, CMC/Walmart, Cencosud, Tricard, Unicard, etc.)
  → Mora directamente por entidad.

Pipeline B — Bancarias:
  Mora    : BEST-CMF → "Informe de tarjetas de crédito bancarias"
  Stock TC: API CMF (api.cmfchile.cl) código 148000300 (MB1 — balance)
  Nota: los códigos MC1 de mora/deteriorada/castigos NO están disponibles
  vía el endpoint /balances/ de la API CMF (devuelven error 80).

Salida:
  CMF_Output/mora_tarjetas_consolidado.xlsx
    Hoja "No_Bancarias"   — mora retail por entidad
    Hoja "Bancarias"      — indicadores de mora TC por banco + stock API
    Hoja "Mercado_Total"  — consolidado de ambos segmentos

Dependencias:
  pip install requests pandas openpyxl playwright
  playwright install chromium
"""

import io
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ─── Rutas ────────────────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

for d in [DATA_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "mora_tarjetas_consolidado.xlsx"

# ─── Configuración ────────────────────────────────────────────────────────────

CMF_API_KEY  = "9c85ee02885eed933641d8c5389fe410fe6024c6"
CMF_API_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"   # ← corregido
BEST_URL     = "https://www.best-cmf.cl/best-cmf/#!/reportesintegrados"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(DATA_DIR / "mora_tarjetas.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger("mora_tarjetas")

# ─── CÓDIGOS CNC 2022 (referencia) ────────────────────────────────────────────
#
# Fuente: "Códigos Contables Bancos" — Capítulo C-3 del CNC para Bancos (CMF).
#
# DISPONIBLE VÍA API (MB1 — Balance mensual consolidado):
#   148000300  Stock TC consumo — endpoint /recursos_api/balances/{year}/cuentas/{cod}
#
# NO DISPONIBLE VÍA API (MC1 — Información complementaria mensual):
#   857400300  Mora ≥90 días TC consumo
#   857200800  Mora ≥90 días TC comercial
#   811400300  Cartera deteriorada TC consumo
#   811200800  Cartera deteriorada TC comercial
#   812400300  Devengo suspendido TC consumo
#   813400300  Castigos TC consumo
#   814400300  Recuperaciones TC consumo
#   → Estos datos se obtienen vía BEST-CMF (Pipeline B mora).

CODIGO_STOCK_TC = "148000300"  # único código MB1 disponible via API


# ─── BEST-CMF: navegación compartida ─────────────────────────────────────────
#
# Estructura del catálogo BEST-CMF (inspeccionada vía HTML):
#   <tr id="TNOBANC_CMF_InformeTrjCreditoNoBancarias">
#     <td>Informe de tarjetas de crédito no bancarias</td>
#     ...
#     <td><span class="MuiButtonBase-root MuiCheckbox-root ...">
#           <input name="TNOBANC_CMF_InformeTrjCreditoNoBancarias" type="checkbox">
#         </span></td>
#   </tr>
#
# Las tarjetas NO tienen selectPeriodo → la descarga incluye toda la serie.
# Flujo: clic en MuiButtonBase-root del tr → esperar tablaSeleccion →
#         clic en #btnDescargaSeleccion → interceptar descarga.

def _scrape_best_reporte(
    row_id: str,
    raw_filename: str,
    segmento: str,
) -> pd.DataFrame:
    """
    Descarga el reporte BEST-CMF identificado por 'row_id' (id del <tr>).

    Flujo:
      1. Cargar catálogo BEST-CMF
      2. Clicar el checkbox MUI del <tr> con id=row_id
      3. Clicar #btnDescargaSeleccion para iniciar descarga
      4. Guardar el archivo descargado en CMF_Data/
      5. Leer y retornar el DataFrame normalizado
    """
    log.info(f"=== BEST-CMF: descargando '{row_id}' ===")

    save_path = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        log.info("Cargando BEST-CMF...")
        page.goto(BEST_URL, timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=60_000)
        time.sleep(2)

        # ── Paso 1: clicar el checkbox MUI del reporte ────────────────────────
        # El MUI checkbox tiene un <span class="MuiButtonBase-root"> visible
        # que envuelve el <input type="checkbox"> oculto.
        checkbox_locator = page.locator(f"tr#{row_id} .MuiButtonBase-root")
        try:
            checkbox_locator.wait_for(state="visible", timeout=15_000)
            checkbox_locator.click()
            log.info(f"Checkbox clicado para {row_id}")
            time.sleep(1)
        except Exception as e:
            log.error(f"No se pudo clicar checkbox de '{row_id}': {e}")
            browser.close()
            return pd.DataFrame()

        # ── Paso 2: abrir panel de descarga via JS ────────────────────────────
        # El botón outlined abre el panel de selección vía evento Angular.
        # Usar JS .click() para garantizar que el evento se dispare aunque
        # el elemento no sea "visible" según Playwright.
        try:
            page.evaluate(
                "document.querySelector('button.btn_descarga.MuiButton-outlined').click()"
            )
            log.info("Botón outlined 'Descargar' clicado (JS evaluate).")
            time.sleep(3)  # dar tiempo al panel Angular para renderizar
        except Exception as e:
            log.warning(f"JS click en outlined falló: {e}")

        # ── Paso 3: descargar via JS click en #btnDescargaSeleccion ──────────
        # El botón está en el DOM pero puede estar oculto por CSS; JS .click()
        # dispara el evento de Angular directamente sin restricciones de visib.
        try:
            with page.expect_download(timeout=60_000) as dl_info:
                page.evaluate("document.getElementById('btnDescargaSeleccion').click()")
            download = dl_info.value
            suggested = download.suggested_filename or f"{raw_filename}.xlsx"
            ext = Path(suggested).suffix or ".xlsx"
            save_path = DATA_DIR / f"{raw_filename}_{datetime.now().strftime('%Y%m%d')}{ext}"
            download.save_as(save_path)
            log.info(f"Descargado: {save_path}")
        except Exception as e:
            log.error(f"Descarga fallida para '{row_id}': {e}")
            # Guardar HTML para debug
            debug_html = DATA_DIR / f"debug_{raw_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            try:
                debug_html.write_text(page.content(), encoding="utf-8")
                log.info(f"HTML diagnóstico guardado: {debug_html}")
            except Exception:
                pass
            browser.close()
            return pd.DataFrame()

        browser.close()

    # ── Leer archivo descargado ───────────────────────────────────────────────
    return _leer_best_descarga(save_path, segmento)


def _leer_best_descarga(save_path: Path, segmento: str) -> pd.DataFrame:
    """
    Lee el Excel descargado de BEST-CMF y retorna datos de mora en formato largo.

    Estructura del Excel BEST:
      - Múltiples hojas (INDICE + datos)
      - En cada hoja de datos:
          fila 0: título
          fila 1: unidad (millones de pesos / número / %)
          fila 2: "Ver cuadro en BEST"
          fila 3: encabezados (col 0 = "Fecha", col 1..N = entidades)
          fila 4+: datos (formato wide — una columna por entidad)
    """
    import zipfile

    if save_path is None or not save_path.exists():
        log.error(f"Archivo descargado no encontrado: {save_path}")
        return pd.DataFrame()

    # Resolver fuente (xlsx directo o xlsx dentro de zip)
    try:
        if save_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(save_path) as z:
                xlsx_names = [n for n in z.namelist()
                              if n.lower().endswith((".xlsx", ".xls"))]
                if not xlsx_names:
                    log.error(f"Zip sin archivos Excel: {save_path}")
                    return pd.DataFrame()
                with z.open(xlsx_names[0]) as f:
                    excel_src = io.BytesIO(f.read())
        else:
            excel_src = save_path
    except Exception as e:
        log.error(f"Error abriendo {save_path}: {e}")
        return pd.DataFrame()

    # Identificar hojas de mora
    try:
        xf = pd.ExcelFile(excel_src)
        sheets = xf.sheet_names
        log.info(f"Hojas en archivo: {sheets}")
    except Exception as e:
        log.error(f"Error leyendo hojas: {e}")
        return pd.DataFrame()

    # Hoja mora monto: nombre contiene "MORA", "MTO", "IFI" (por institución)
    mora_mto = next((s for s in sheets if "MORA" in s and "MTO" in s and "IFI" in s), None)
    # Hoja mora %: nombre contiene "MORA", "PORC", "IFI"
    mora_pct = next((s for s in sheets if "MORA" in s and "PORC" in s and "IFI" in s), None)

    if not mora_mto:
        log.error(f"No se encontró hoja de mora MTO. Hojas: {sheets}")
        return pd.DataFrame()

    def hoja_a_largo(sheet_name: str, valor_col: str) -> pd.DataFrame:
        """Lee hoja BEST wide → formato largo (periodo, entidad, valor)."""
        df = pd.read_excel(excel_src, sheet_name=sheet_name, header=3)
        df = df.rename(columns={df.columns[0]: "periodo"})
        entity_cols = [c for c in df.columns if c != "periodo"]
        df_long = df.melt(id_vars="periodo", var_name="entidad", value_name=valor_col)
        # Parsear fechas
        df_long["periodo"] = pd.to_datetime(df_long["periodo"], errors="coerce")
        df_long = df_long.dropna(subset=["periodo"])
        df_long["periodo"] = df_long["periodo"].dt.strftime("%Y-%m")
        # Limpiar valores ("-" o espacios → NaN)
        df_long[valor_col] = pd.to_numeric(
            df_long[valor_col].astype(str).str.strip().replace({"-": None, "nan": None}),
            errors="coerce",
        )
        df_long = df_long.dropna(subset=[valor_col])
        return df_long

    df_mora = hoja_a_largo(mora_mto, "monto_mora_MM")
    log.info(f"  {mora_mto}: {len(df_mora)} registros.")

    if mora_pct:
        df_pct = hoja_a_largo(mora_pct, "indice_mora_pct")
        df_mora = df_mora.merge(
            df_pct[["periodo", "entidad", "indice_mora_pct"]],
            on=["periodo", "entidad"],
            how="left",
        )
        log.info(f"  {mora_pct}: % mora agregado.")

    df_mora["segmento"] = segmento
    log.info(f"Total {segmento}: {len(df_mora)} registros, "
             f"{df_mora['entidad'].nunique()} entidades, "
             f"período {df_mora['periodo'].min()} — {df_mora['periodo'].max()}")
    return df_mora


def _normalizar_reporte_best(df: pd.DataFrame, segmento: str) -> pd.DataFrame:
    """Mapea columnas del reporte BEST al esquema estándar por keywords."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    rename_map = {}
    for col in df.columns:
        lc = col
        if any(k in lc for k in ["entidad", "instituc", "emisor", "banco"]):
            rename_map[col] = "entidad"
        elif any(k in lc for k in ["período", "periodo", "mes", "fecha"]):
            rename_map[col] = "periodo"
        elif "mora" in lc and any(k in lc for k in ["n°", "número", "num", "tarjeta", "cantidad"]):
            rename_map[col] = "n_tarjetas_mora"
        elif any(k in lc for k in ["n° tarjeta", "n°tarjeta", "total tarjeta"]):
            rename_map[col] = "n_tarjetas_total"
        elif "mora" in lc and any(k in lc for k in ["monto", "$", "deuda", "saldo", "mm", "miles"]):
            rename_map[col] = "monto_mora_MM"
        elif any(k in lc for k in ["monto total", "deuda total", "saldo total"]):
            rename_map[col] = "monto_deuda_total_MM"
        elif "mora" in lc and "%" in lc:
            rename_map[col] = "indice_mora_pct"

    df = df.rename(columns=rename_map)

    if "indice_mora_pct" not in df.columns:
        if {"monto_mora_MM", "monto_deuda_total_MM"}.issubset(df.columns):
            df["indice_mora_pct"] = (
                pd.to_numeric(df["monto_mora_MM"], errors="coerce") /
                pd.to_numeric(df["monto_deuda_total_MM"], errors="coerce") * 100
            ).round(2)

    df["segmento"] = segmento
    return df


# ─── PIPELINE A: No bancarias ─────────────────────────────────────────────────

def scrape_no_bancarias() -> pd.DataFrame:
    """
    Extrae el reporte mensual de tarjetas no bancarias desde BEST-CMF.
    Retorna DataFrame normalizado con mora por entidad.
    """
    log.info("=== Pipeline A: No bancarias → BEST-CMF ===")
    return _scrape_best_reporte(
        row_id="TNOBANC_CMF_InformeTrjCreditoNoBancarias",
        raw_filename="best_no_bancarias_raw",
        segmento="No Bancaria",
    )


# ─── PIPELINE B: Bancarias ────────────────────────────────────────────────────

def scrape_bancarias() -> pd.DataFrame:
    """
    Extrae el reporte mensual de tarjetas bancarias desde BEST-CMF.
    Retorna DataFrame normalizado con mora por banco.
    """
    log.info("=== Pipeline B mora: Bancarias → BEST-CMF ===")
    return _scrape_best_reporte(
        row_id="TCRED_CMF_InformeTrjCreditoBancarias",
        raw_filename="best_bancarias_raw",
        segmento="Bancaria",
    )


def fetch_balance_serie(codigo: str, desde: str = "2022-01") -> pd.DataFrame:
    """
    Descarga datos de balance mensual por código de cuenta (todos los bancos).

    Endpoint CMF confirmado (200 OK):
      GET /recursos_api/balances/{year}/cuentas/{codigo}
    Un request por año, retorna todos los bancos y meses de ese año.

    Response: {"CodigosBalances": [{CodigoCuenta, NombreInstitucion,
                                    Anho, Mes, MonedaTotal, ...}]}
    """
    desde_year = int(desde.split("-")[0])
    hasta_year = datetime.now().year
    frames = []

    for year in range(desde_year, hasta_year + 1):
        url = (
            f"{CMF_API_BASE}/balances/{year}/cuentas/{codigo}"
            f"?apikey={CMF_API_KEY}&formato=json"
        )
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                try:
                    err = r.json()
                    msg = err.get("Mensaje", "")
                except Exception:
                    msg = ""
                log.warning(f"  API [{year}] código {codigo}: HTTP {r.status_code} — {msg}")
                continue
            data = r.json()
            registros = data.get("CodigosBalances", [])
            if registros:
                df = pd.DataFrame(registros)
                df.columns = [c.lower() for c in df.columns]
                frames.append(df)
                log.info(f"  API [{year}] código {codigo}: {len(registros)} registros.")
            else:
                log.warning(f"  API [{year}] código {codigo}: respuesta vacía.")
        except Exception as e:
            log.warning(f"  API [{year}] código {codigo}: {e}")

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # Columna periodo YYYY-MM
    if {"anho", "mes"}.issubset(df_all.columns):
        df_all["periodo"] = df_all.apply(
            lambda r: f"{int(r['anho'])}-{int(r['mes']):02d}", axis=1
        )

    # MonedaTotal: formato chileno "1.234,56" → 1234.56
    if "monedatotal" in df_all.columns:
        df_all["monto_tc_stock_total_MM"] = pd.to_numeric(
            df_all["monedatotal"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False),
            errors="coerce",
        )

    return df_all


def bancarias_via_api(desde: str = "2022-01") -> pd.DataFrame:
    """
    Extrae indicadores de mora bancaria combinando:
      - BEST-CMF: mora por banco/período (reporte integrado bancarias)
      - API CMF:  stock TC por banco/período (código 148000300, MB1)

    Une ambas fuentes en (periodo, banco) y calcula índice de mora
    contra el stock oficial de la API cuando hay match.
    """
    log.info("=== Pipeline B: Bancarias → BEST-CMF (mora) + API CMF (stock) ===")
    log.info(f"Período: {desde} → {datetime.now().strftime('%Y-%m')}")

    # ── Sub-pipeline B1: mora desde BEST-CMF ──────────────────────────────────
    df_mora = pd.DataFrame()
    try:
        df_mora = scrape_bancarias()
        log.info(f"BEST bancarias: {len(df_mora)} registros de mora.")
    except Exception as e:
        log.error(f"BEST bancarias falló: {e}")

    # ── Sub-pipeline B2: stock TC desde API ───────────────────────────────────
    log.info(f"  Descargando stock TC ({CODIGO_STOCK_TC}) desde API CMF...")
    df_stock = fetch_balance_serie(CODIGO_STOCK_TC, desde=desde)

    if df_stock.empty:
        log.warning("Sin datos de stock desde API CMF.")
        if df_mora.empty:
            return pd.DataFrame()
        df_mora["segmento"] = "Bancaria"
        return df_mora

    log.info(f"  Stock API: {len(df_stock)} registros.")
    raw_path = DATA_DIR / f"api_stock_tc_raw_{datetime.now().strftime('%Y%m%d')}.xlsx"
    df_stock.to_excel(raw_path, index=False)
    log.info(f"Raw stock guardado: {raw_path}")

    if df_mora.empty:
        log.warning(
            "Mora bancaria no disponible desde BEST-CMF: el 'Informe de tarjetas de "
            "credito bancarias' contiene operaciones (vigentes/transacciones), no mora. "
            "El catalogo BEST no tiene un reporte de mora especifico para TC bancarias. "
            "Solo se exporta el stock TC (148000300) desde la API CMF."
        )
        # Estandarizar nombres para el schema de salida
        if "nombreinstitucion" in df_stock.columns:
            df_stock = df_stock.rename(columns={"nombreinstitucion": "entidad"})
        df_stock["segmento"] = "Bancaria"
        raw_b = DATA_DIR / f"api_bancarias_raw_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df_stock.to_excel(raw_b, index=False)
        log.info(f"Raw bancarias guardado: {raw_b}")
        return df_stock

    # ── Merge mora (BEST) con stock (API) ─────────────────────────────────────
    # Normalizar nombre banco para el join
    df_mora_m = df_mora.copy()
    df_stock_m = df_stock.copy()

    if "entidad" in df_mora_m.columns:
        df_mora_m["_banco"] = df_mora_m["entidad"].astype(str).str.upper().str.strip()
    else:
        df_mora_m["_banco"] = ""

    if "nombreinstitucion" in df_stock_m.columns:
        df_stock_m["_banco"] = df_stock_m["nombreinstitucion"].astype(str).str.upper().str.strip()
    else:
        df_stock_m["_banco"] = ""

    stock_cols = ["periodo", "_banco", "monto_tc_stock_total_MM"]
    stock_cols = [c for c in stock_cols if c in df_stock_m.columns]

    df_merged = df_mora_m.merge(
        df_stock_m[stock_cols],
        on=["periodo", "_banco"] if "periodo" in df_mora_m.columns else ["_banco"],
        how="left",
    )
    df_merged.drop(columns=["_banco"], inplace=True)

    # Índice de mora vs stock API (cuando hay match)
    if {"monto_mora_MM", "monto_tc_stock_total_MM"}.issubset(df_merged.columns):
        df_merged["indice_mora_vs_stock_api_pct"] = (
            pd.to_numeric(df_merged["monto_mora_MM"], errors="coerce") /
            pd.to_numeric(df_merged["monto_tc_stock_total_MM"], errors="coerce") * 100
        ).round(2)

    df_merged["segmento"] = "Bancaria"

    raw_b = DATA_DIR / f"api_bancarias_raw_{datetime.now().strftime('%Y%m%d')}.xlsx"
    df_merged.to_excel(raw_b, index=False)
    log.info(f"Raw bancarias guardado: {raw_b}")

    return df_merged


# ─── Consolidación y exportación ─────────────────────────────────────────────

def consolidar(df_nb: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    frames = [df for df in [df_nb, df_b] if not df.empty]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def guardar_excel(df_nb: pd.DataFrame, df_b: pd.DataFrame, df_total: pd.DataFrame):
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        if not df_nb.empty:
            df_nb.to_excel(writer, sheet_name="No_Bancarias", index=False)
        if not df_b.empty:
            df_b.to_excel(writer, sheet_name="Bancarias", index=False)
        if not df_total.empty:
            df_total.to_excel(writer, sheet_name="Mercado_Total", index=False)
    log.info(f"Output guardado: {OUTPUT_FILE}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(desde: str = "2022-01"):
    log.info("=" * 65)
    log.info("CMF MORA TARJETAS — inicio")
    log.info(f"  Período desde: {desde}")
    log.info("=" * 65)

    # Pipeline A
    df_nb = pd.DataFrame()
    try:
        df_nb = scrape_no_bancarias()
        log.info(f"No bancarias: {len(df_nb)} registros.")
    except Exception as e:
        log.error(f"Pipeline A falló: {e}")

    # Pipeline B
    df_b = pd.DataFrame()
    try:
        df_b = bancarias_via_api(desde=desde)
        log.info(f"Bancarias: {len(df_b)} registros.")
    except Exception as e:
        log.error(f"Pipeline B falló: {e}")

    # Consolidar y guardar
    df_total = consolidar(df_nb, df_b)
    guardar_excel(df_nb, df_b, df_total)

    # Resumen consola
    print("\n" + "=" * 65)
    print("RESUMEN — MORA DE TARJETAS MERCADO COMPLETO")
    print("=" * 65)
    for seg, df_seg in [("No Bancaria", df_nb), ("Bancaria", df_b)]:
        n_ent = df_seg["entidad"].nunique() if not df_seg.empty and "entidad" in df_seg.columns else "—"
        print(f"  {seg:15s} -> {len(df_seg):5d} registros  |  {n_ent} entidades")
    print(f"\n  TOTAL MERCADO  -> {len(df_total)} registros")
    print(f"  Output: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    import sys
    desde = sys.argv[1] if len(sys.argv) > 1 else "2022-01"
    main(desde=desde)
