"""
inspeccionar_tcred_bancarias.py
================================
Descarga el informe TCRED_CMF_InformeTrjCreditoBancarias desde BEST-CMF
e inspecciona TODAS sus hojas sin asumir estructura previa.

Objetivo: detectar si contiene datos de morosidad bancaria por institución.

Uso:
  python inspeccionar_tcred_bancarias.py

Salida:
  - tcred_bancarias_raw_<fecha>.xlsx   (archivo original descargado)
  - tcred_bancarias_estructura.txt     (reporte de hojas + primeras filas)
  - Imprime en consola diagnóstico completo
"""

import io, time, zipfile, sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

BEST_URL   = "https://www.best-cmf.cl/best-cmf/#!/reportesintegrados"
ROW_ID     = "TCRED_CMF_InformeTrjCreditoBancarias"
DATA_DIR   = Path(".")
FECHA      = datetime.now().strftime("%Y%m%d_%H%M")
RAW_FILE   = DATA_DIR / f"tcred_bancarias_raw_{FECHA}.xlsx"
REPORT_OUT = DATA_DIR / "tcred_bancarias_estructura.txt"

# Palabras clave para identificar hojas con mora
MORA_KW = ["mora", "morosidad", "moroso", "vencido", "deterioro",
           "castigo", "provision", "cartera", "riesgo", "incobrable"]


def descargar_reporte() -> Path:
    """Descarga el Excel de TCRED bancarias desde BEST-CMF."""
    save_path = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page    = browser.new_page()

        print(f"[1/4] Cargando BEST-CMF...")
        page.goto(BEST_URL, timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=60_000)
        time.sleep(2)

        print(f"[2/4] Activando checkbox: {ROW_ID}")
        checkbox = page.locator(f"tr#{ROW_ID} .MuiButtonBase-root")
        try:
            checkbox.wait_for(state="visible", timeout=15_000)
            checkbox.click()
            time.sleep(1)
        except Exception as e:
            print(f"  ERROR: No se encontró el checkbox — {e}")
            browser.close()
            return None

        print(f"[3/4] Abriendo panel de descarga...")
        try:
            page.evaluate(
                "document.querySelector('button.btn_descarga.MuiButton-outlined').click()"
            )
            time.sleep(3)
        except Exception as e:
            print(f"  WARN: click outlined falló ({e}), intentando igual...")

        print(f"[4/4] Descargando archivo...")
        try:
            with page.expect_download(timeout=90_000) as dl_info:
                page.evaluate("document.getElementById('btnDescargaSeleccion').click()")
            download  = dl_info.value
            suggested = download.suggested_filename or f"tcred_bancarias_{FECHA}.xlsx"
            ext       = Path(suggested).suffix or ".xlsx"
            save_path = DATA_DIR / f"tcred_bancarias_raw_{FECHA}{ext}"
            download.save_as(save_path)
            print(f"  Descargado: {save_path} ({save_path.stat().st_size/1024:.0f} KB)")
        except Exception as e:
            print(f"  ERROR descarga: {e}")
            # Guardar HTML para debug
            debug = DATA_DIR / f"debug_tcred_{FECHA}.html"
            debug.write_text(page.content(), encoding="utf-8")
            print(f"  HTML debug guardado: {debug}")

        browser.close()

    return save_path


def abrir_excel(path: Path):
    """Abre el Excel (o descomprime zip si aplica) y retorna (ExcelFile, fuente)."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            xlsx_names = [n for n in z.namelist()
                          if n.lower().endswith((".xlsx", ".xls"))]
            if not xlsx_names:
                print("  ERROR: Zip sin archivos Excel.")
                return None, None
            with z.open(xlsx_names[0]) as f:
                src = io.BytesIO(f.read())
    else:
        src = path

    return pd.ExcelFile(src), src


def inspeccionar(path: Path):
    """
    Inspecciona todas las hojas del Excel descargado.
    Para cada hoja muestra: dimensiones, columnas, primeras 5 filas,
    y evalúa si contiene datos de mora.
    """
    xf, src = abrir_excel(path)
    if xf is None:
        return

    sheets = xf.sheet_names
    print(f"\n{'='*65}")
    print(f"ESTRUCTURA DEL ARCHIVO: {path.name}")
    print(f"{'='*65}")
    print(f"Total hojas: {len(sheets)}")
    print(f"Nombres: {sheets}\n")

    lines = [f"Archivo: {path.name}", f"Total hojas: {len(sheets)}",
             f"Nombres: {sheets}", ""]

    mora_sheets   = []
    banco_sheets  = []

    for sheet in sheets:
        print(f"\n{'─'*55}")
        print(f"HOJA: [{sheet}]")
        lines += [f"\n{'─'*55}", f"HOJA: [{sheet}]"]

        try:
            # Leer con header=None para ver estructura cruda
            df_raw = pd.read_excel(src, sheet_name=sheet, header=None,
                                   nrows=10, dtype=str)
            df_raw = df_raw.fillna("")

            # También leer con header=3 (convención BEST-CMF)
            try:
                df_h3 = pd.read_excel(src, sheet_name=sheet, header=3, dtype=str)
                cols_h3 = list(df_h3.columns)
            except Exception:
                df_h3   = pd.DataFrame()
                cols_h3 = []

            # Texto completo del raw para búsqueda de keywords
            all_text = " ".join(df_raw.values.flatten()).lower()

            # Detectar keywords de mora
            mora_found = [k for k in MORA_KW if k in all_text]
            # Detectar nombres de bancos
            bancos_kw  = ["banco de chile", "santander", "bci", "bancoestado",
                          "itaú", "itau", "scotiabank", "banco estado"]
            bancos_found = [k for k in bancos_kw if k in all_text]

            info = (f"  Dims (raw 10 filas): {df_raw.shape}\n"
                    f"  Cols con header=3: {cols_h3[:10]}\n"
                    f"  Mora keywords: {mora_found or '(ninguna)'}\n"
                    f"  Bancos detectados: {bancos_found or '(ninguno)'}")
            print(info)
            lines.append(info)

            print("\n  Primeras 8 filas (raw):")
            raw_str = df_raw.head(8).to_string()
            print(raw_str)
            lines += ["  Primeras 8 filas (raw):", raw_str]

            if mora_found:
                mora_sheets.append(sheet)
                print(f"\n  *** POSIBLE MORA: {mora_found} ***")
                lines.append(f"  *** POSIBLE MORA: {mora_found} ***")

                # Si hay mora + bancos → candidato fuerte
                if bancos_found:
                    banco_sheets.append(sheet)
                    print(f"  *** BANCOS DETECTADOS: {bancos_found} ← CANDIDATO FUERTE ***")
                    lines.append(f"  *** BANCOS DETECTADOS: {bancos_found} ← CANDIDATO FUERTE ***")

        except Exception as e:
            msg = f"  ERROR al leer hoja: {e}"
            print(msg)
            lines.append(msg)

    # ── Resumen final ─────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("DIAGNÓSTICO FINAL")
    print(f"{'='*65}")
    lines += [f"\n{'='*65}", "DIAGNÓSTICO FINAL", f"{'='*65}"]

    if banco_sheets:
        msg = (f"✓ MORA BANCARIA ENCONTRADA en hojas: {banco_sheets}\n"
               f"  → Proceder a extraer datos y construir pipeline.")
        print(msg)
        lines.append(msg)
    elif mora_sheets:
        msg = (f"⚠ Mora encontrada pero SIN desglose por banco: {mora_sheets}\n"
               f"  → Revisar manualmente si hay subtotales por institución.")
        print(msg)
        lines.append(msg)
    else:
        msg = ("✗ CONFIRMADO: Este reporte NO contiene datos de morosidad.\n"
               "  'Morosidad' figura en los metadatos de BEST-CMF pero no\n"
               "  está en el contenido del Excel descargado.\n\n"
               "  CONCLUSIÓN FINAL: La mora bancaria por institución no es\n"
               "  accesible en ningún canal público de la CMF.\n\n"
               "  Opciones para el dashboard:\n"
               "  A) Pestaña Mora No Bancaria (data disponible ahora)\n"
               "  B) Omitir pestaña mora, mantener 6 tabs")
        print(msg)
        lines.append(msg)

    # Guardar reporte txt
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Reporte guardado: {REPORT_OUT}")


def main():
    print("=" * 65)
    print("  BEST-CMF — Inspección TCRED Bancarias")
    print(f"  Row ID: {ROW_ID}")
    print("=" * 65 + "\n")

    path = descargar_reporte()

    if path is None or not path.exists():
        print("\nNo se pudo descargar el archivo. Verifica:")
        print("  1. Conexión a internet")
        print("  2. playwright install chromium")
        print("  3. BEST-CMF accesible desde tu red")
        sys.exit(1)

    inspeccionar(path)


if __name__ == "__main__":
    main()
