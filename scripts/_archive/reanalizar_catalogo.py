"""
reanalizar_catalogo.py
======================
Re-analiza best_catalogo_completo.xlsx con keywords expandidos.
No requiere navegador ni internet — solo el Excel ya guardado.

Uso:
  python reanalizar_catalogo.py

Debe estar en la misma carpeta que best_catalogo_completo.xlsx
"""

import pandas as pd
from pathlib import Path

EXCEL = Path("best_catalogo_completo.xlsx")

# Keywords expandidos — cubre todas las variantes de mora/riesgo en español
MORA_KEYWORDS = [
    "mora", "morosidad", "moroso",
    "vencido", "vencida", "vencimiento",
    "deterioro", "deteriorada", "deteriorado",
    "castigo", "castigado", "castigos",
    "provision", "provisión", "provisiones",
    "riesgo",
    "incobrable", "incobrables",
    "impago", "impagos",
    "atraso", "atrasos",
    "cobranza",
    "default",
    "devengado suspendido",
]

# Keywords de tarjetas bancarias
BANC_KEYWORDS = [
    "tarjeta", "tarjetas",
    "bancaria", "bancarias", "bancario", "bancarios",
    "banco", "bancos",
    "credito", "crédito",
    "consumo",
    "tcred", "TCRED",
]


def main():
    if not EXCEL.exists():
        print(f"ERROR: No se encontró {EXCEL}")
        print("Ejecuta primero explorar_best_cmf.py para generar el archivo.")
        return

    df = pd.read_excel(EXCEL, sheet_name="Catalogo_Completo")
    print(f"Cargados {len(df)} reportes del catálogo.\n")

    def score_row(row):
        texto = " ".join([
            str(row.get("row_id",    "")),
            str(row.get("titulo",    "")),
            str(row.get("descripcion", "")),
        ]).lower()
        mora_hits  = [k for k in MORA_KEYWORDS  if k.lower() in texto]
        banc_hits  = [k for k in BANC_KEYWORDS  if k.lower() in texto]
        return mora_hits, banc_hits

    df["mora_hits"], df["banc_hits"] = zip(*df.apply(score_row, axis=1))
    df["mora_score"] = df["mora_hits"].apply(len)
    df["banc_score"] = df["banc_hits"].apply(len)
    df["es_candidato"] = (df["mora_score"] > 0) & (df["banc_score"] > 0)

    # ── 1. Mostrar TODOS los reportes con sus descripciones completas ──────────
    print("=" * 70)
    print("TODOS LOS 45 REPORTES — descripción completa")
    print("=" * 70)
    for _, row in df.iterrows():
        candidato_tag = " ◄ CANDIDATO" if row["es_candidato"] else ""
        print(f"\n[{row['row_id']}]{candidato_tag}")
        print(f"  Título:      {row['titulo']}")
        print(f"  Descripción: {row['descripcion']}")
        print(f"  Scores:      mora={row['mora_score']} ({', '.join(row['mora_hits']) or '-'}) | "
              f"banc={row['banc_score']} ({', '.join(row['banc_hits']) or '-'})")

    # ── 2. Candidatos con keywords expandidos ─────────────────────────────────
    candidatos = df[df["es_candidato"]].sort_values(
        ["mora_score", "banc_score"], ascending=False
    )
    print("\n" + "=" * 70)
    print(f"CANDIDATOS con keywords expandidos: {len(candidatos)}")
    print("=" * 70)
    if candidatos.empty:
        print("\n  ✗ CONFIRMADO: No existe ningún reporte de mora bancaria")
        print("    en BEST-CMF bajo ninguna denominación.")
        print()
        print("  Reportes con tarjetas (banc_score > 0, sin mora):")
        tc = df[df["banc_score"] > 0][["row_id", "titulo", "mora_score", "banc_score"]]
        print(tc.to_string(index=False))
    else:
        for _, row in candidatos.iterrows():
            print(f"\n  row_id:  {row['row_id']}")
            print(f"  titulo:  {row['titulo']}")
            print(f"  mora:    {', '.join(row['mora_hits'])}")
            print(f"  banc:    {', '.join(row['banc_hits'])}")

    # ── 3. Guardar Excel con re-análisis ──────────────────────────────────────
    out = EXCEL.parent / "best_catalogo_reanalizado.xlsx"
    df_out = df[["row_id", "categoria", "titulo", "descripcion",
                 "mora_score", "banc_score", "es_candidato",
                 "mora_hits", "banc_hits"]].copy()
    df_out["mora_hits"] = df_out["mora_hits"].apply(lambda x: ", ".join(x))
    df_out["banc_hits"] = df_out["banc_hits"].apply(lambda x: ", ".join(x))
    df_out.to_excel(out, index=False)
    print(f"\n  Guardado: {out}")


if __name__ == "__main__":
    main()
