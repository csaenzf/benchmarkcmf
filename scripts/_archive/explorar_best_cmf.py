"""
explorar_best_cmf.py
====================
Descarga y mapea TODO el catálogo de BEST-CMF.

Objetivo: identificar si existen reportes de MORA específicos para
tarjetas de crédito BANCARIAS (por banco individual).

Salida:
  - best_catalogo_completo.xlsx  → tabla con todos los reportes disponibles
  - Imprime en consola los reportes candidatos para mora bancaria

Uso:
  pip install playwright pandas openpyxl
  playwright install chromium
  python explorar_best_cmf.py

"""

import time
import re
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

BEST_URL  = "https://www.best-cmf.cl/best-cmf/#!/reportesintegrados"
OUT_FILE  = Path("best_catalogo_completo.xlsx")

# ─── Palabras clave para detectar candidatos de mora bancaria ─────────────────
MORA_KEYWORDS  = ["mora", "riesgo", "deterioro", "provisión", "provision",
                  "vencido", "castigo", "incobrable", "cartera"]
BANC_KEYWORDS  = ["bancari", "banco", "credito", "crédito", "tarjeta"]


def extraer_catalogo() -> pd.DataFrame:
    """
    Navega BEST-CMF y extrae todos los <tr> de la tabla del catálogo.
    Retorna DataFrame con: row_id, titulo, descripcion, categoria.
    """
    rows = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page    = browser.new_page()

        print("Cargando BEST-CMF...")
        page.goto(BEST_URL, timeout=60_000)
        page.wait_for_load_state("networkidle", timeout=60_000)
        time.sleep(3)

        # ── 1. Extraer todas las filas de la tabla del catálogo ───────────────
        # La tabla tiene <tr id="CATEGORIA_InstitucioN_NombreReporte"> con
        # varias celdas. Extraemos todo el HTML para parsearlo.
        html = page.content()

        # ── 2. Parsear con regex (sin BeautifulSoup para no añadir deps) ──────
        # Patron: <tr id="..."> ... </tr>
        tr_blocks = re.findall(
            r'<tr[^>]+id="([A-Z][^"]+)"[^>]*>([\s\S]*?)</tr>',
            html,
            re.IGNORECASE
        )
        print(f"  <tr> con id encontrados: {len(tr_blocks)}")

        for row_id, content in tr_blocks:
            # Extraer texto de todas las <td>
            tds = re.findall(r'<td[^>]*>([\s\S]*?)</td>', content, re.IGNORECASE)
            td_texts = []
            for td in tds:
                # Eliminar tags HTML internos
                clean = re.sub(r'<[^>]+>', ' ', td).strip()
                clean = re.sub(r'\s+', ' ', clean).strip()
                if clean:
                    td_texts.append(clean)

            titulo      = td_texts[0] if len(td_texts) > 0 else ""
            descripcion = " | ".join(td_texts[1:]) if len(td_texts) > 1 else ""

            # Inferir categoría desde el row_id (prefijo antes del primer _)
            partes    = row_id.split("_")
            categoria = partes[0] if partes else ""

            rows.append({
                "row_id":      row_id,
                "categoria":   categoria,
                "titulo":      titulo,
                "descripcion": descripcion,
                "raw_content": content[:200],  # primeros 200 chars para debug
            })

        # ── 3. Intentar también expandir secciones colapsadas ─────────────────
        # Algunos reportes pueden estar en acordeones. Clicar en secciones
        # con texto "Tarjetas" o "Mora" para expandir.
        accordions = page.locator("[class*='accordion'], [class*='expand'], [class*='collapse']")
        count = accordions.count()
        if count > 0:
            print(f"  Intentando expandir {count} acordeones...")
            for i in range(min(count, 20)):
                try:
                    accordions.nth(i).click(timeout=2000)
                    time.sleep(0.5)
                except Exception:
                    pass
            # Re-extraer tras expansión
            html2 = page.content()
            tr_blocks2 = re.findall(
                r'<tr[^>]+id="([A-Z][^"]+)"[^>]*>([\s\S]*?)</tr>',
                html2, re.IGNORECASE
            )
            seen_ids = {r["row_id"] for r in rows}
            new_count = 0
            for row_id, content in tr_blocks2:
                if row_id not in seen_ids:
                    tds = re.findall(r'<td[^>]*>([\s\S]*?)</td>', content, re.IGNORECASE)
                    td_texts = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', td)).strip()
                                for td in tds if td.strip()]
                    partes = row_id.split("_")
                    rows.append({
                        "row_id":      row_id,
                        "categoria":   partes[0] if partes else "",
                        "titulo":      td_texts[0] if td_texts else "",
                        "descripcion": " | ".join(td_texts[1:]),
                        "raw_content": content[:200],
                    })
                    seen_ids.add(row_id)
                    new_count += 1
            if new_count:
                print(f"  +{new_count} reportes adicionales tras expandir acordeones")

        browser.close()

    return pd.DataFrame(rows)


def analizar_candidatos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra reportes candidatos para mora bancaria de tarjetas.
    Un candidato tiene al menos 1 keyword de mora Y 1 de bancaria.
    """
    def score(row):
        texto = (row["row_id"] + " " + row["titulo"] + " " + row["descripcion"]).lower()
        mora_hits = sum(1 for k in MORA_KEYWORDS if k in texto)
        banc_hits = sum(1 for k in BANC_KEYWORDS if k in texto)
        return mora_hits, banc_hits

    df["mora_score"], df["banc_score"] = zip(*df.apply(score, axis=1))
    df["es_candidato"] = (df["mora_score"] > 0) & (df["banc_score"] > 0)
    return df


def main():
    print("=" * 60)
    print("  BEST-CMF — Exploración de catálogo")
    print("=" * 60)

    df = extraer_catalogo()

    if df.empty:
        print("\n  ERROR: No se pudo extraer el catálogo. Verificar:")
        print("    1. Conexión a internet activa")
        print("    2. playwright install chromium ejecutado")
        print("    3. BEST-CMF accesible desde tu red")
        return

    print(f"\n  Total reportes encontrados: {len(df)}")

    df = analizar_candidatos(df)

    # ── Guardar Excel completo ────────────────────────────────────────────────
    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        df.drop(columns=["raw_content"]).to_excel(
            writer, sheet_name="Catalogo_Completo", index=False
        )
        candidatos = df[df["es_candidato"]].copy()
        if not candidatos.empty:
            candidatos.drop(columns=["raw_content"]).to_excel(
                writer, sheet_name="Candidatos_Mora_Bancaria", index=False
            )

    print(f"  Catálogo completo guardado: {OUT_FILE}")
    print()

    # ── Resumen por categoría ─────────────────────────────────────────────────
    print("── Reportes por categoría ──────────────────────────────────")
    print(df.groupby("categoria").size().to_string())
    print()

    # ── Candidatos ───────────────────────────────────────────────────────────
    candidatos = df[df["es_candidato"]].sort_values(
        ["mora_score", "banc_score"], ascending=False
    )

    if candidatos.empty:
        print("  ⚠ No se encontraron reportes con indicadores de mora bancaria.")
        print()
        print("  Reportes bancarios disponibles (sin mora):")
        banc_only = df[df["banc_score"] > 0][["row_id", "titulo", "mora_score", "banc_score"]]
        print(banc_only.to_string(index=False))
        print()
        print("  CONCLUSIÓN: La mora bancaria por institución no está disponible")
        print("  en BEST-CMF. Opciones:")
        print("    A) Tab 'Mora No Bancaria' con datos ya disponibles")
        print("    B) Usar estados financieros CMF (nivel banco, no tarjetas)")
        print("    C) Omitir pestaña mora del dashboard")
    else:
        print(f"  ✓ {len(candidatos)} reportes CANDIDATOS para mora bancaria:")
        print()
        for _, row in candidatos.iterrows():
            print(f"  row_id:      {row['row_id']}")
            print(f"  titulo:      {row['titulo']}")
            print(f"  descripcion: {row['descripcion']}")
            print(f"  scores:      mora={row['mora_score']}  bancaria={row['banc_score']}")
            print()

        print("  Para descargar y explorar cada candidato, usar:")
        print()
        for _, row in candidatos.head(5).iterrows():
            print(f"  _scrape_best_reporte(row_id='{row['row_id']}', ...)")

    # ── Lista completa de TODOS los row_ids (para referencia) ─────────────────
    print()
    print("── Todos los row_ids ───────────────────────────────────────")
    for row_id in sorted(df["row_id"].tolist()):
        print(f"  {row_id}")


if __name__ == "__main__":
    main()
