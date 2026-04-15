"""
cmf_explorar_api_y_mora_3.py
=============================
CORREGIDO: usa el parsing correcto de la API CMF (basado en cmf_mora_tarjetas_1.py)

TAREA 1: Extrae series completas de 8 códigos contables vía API CMF
         (colocaciones consumo/comercial/TC/vivienda/provisiones por banco)
         Un request por AÑO (no por mes) → ~40 requests total vs ~400.

TAREA 2: Descarga Cartera Vencida + Mora ≥90d (XLSX mensuales, 24 meses)

Rutas:
  Script : C:\Dropbox\CMF_API\CMF_Reportes_Excel\
  Output : C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Output\

Dependencias: pip install requests pandas openpyxl
"""

import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ─── Configuración ────────────────────────────────────────────────────────────

CMF_API_KEY = "9c85ee02885eed933641d8c5389fe410fe6024c6"
CMF_API_BASE = "https://api.cmfchile.cl/api-sbifv3/recursos_api"

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "processed"
MORA_DIR = OUTPUT_DIR / "mora_cartera_mensual"

for d in [OUTPUT_DIR, MORA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-28913.html",
}

# ═══════════════════════════════════════════════════════════════════════════════
# TAREA 1: EXTRAER COLOCACIONES VÍA API CMF
# ═══════════════════════════════════════════════════════════════════════════════

API_CODES = {
    "148000300": "Deudores_TC",
    "148000100": "Creditos_consumo_cuotas",
    "148000200": "Deudores_CC_consumo",
    "148000000": "Colocaciones_consumo_total",
    "148000400": "Leasing_consumo",
    "145000000": "Colocaciones_comerciales",
    "146000000": "Colocaciones_vivienda",
    "140000000": "Total_colocaciones",
    "149000000": "Provisiones_total",
}

YEAR_START = 2022  # API solo tiene data desde 2022 para estos códigos
YEAR_END = 2026


def fetch_balance_serie(codigo, label, desde_year=YEAR_START, hasta_year=YEAR_END):
    """
    Descarga datos de balance mensual por código de cuenta (todos los bancos).

    Endpoint CMF confirmado:
      GET /recursos_api/balances/{year}/cuentas/{codigo}?apikey=...&formato=json
    Un request por año → retorna todos los bancos y todos los meses de ese año.

    Response: {"CodigosBalances": [{CodigoCuenta, NombreInstitucion,
                                    Anho, Mes, MonedaTotal, ...}]}
    """
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
                    msg = r.json().get("Mensaje", "")
                except Exception:
                    msg = ""
                print(f"    [{year}] HTTP {r.status_code} — {msg}")
                continue

            data = r.json()
            registros = data.get("CodigosBalances", [])

            if registros:
                df = pd.DataFrame(registros)
                df.columns = [c.lower() for c in df.columns]
                df["cuenta_label"] = label
                frames.append(df)
                print(f"    [{year}] {len(registros)} registros")
            else:
                print(f"    [{year}] vacío")

        except Exception as e:
            print(f"    [{year}] ERROR: {e}")

        time.sleep(0.5)

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # Crear columna periodo YYYY-MM
    if {"anho", "mes"}.issubset(df_all.columns):
        df_all["periodo"] = df_all.apply(
            lambda r: f"{int(r['anho'])}-{int(r['mes']):02d}", axis=1
        )

    # Convertir MonedaTotal: formato chileno "1.234.567,89" → float
    for col in ["monedatotal", "monedachilenanoreajustable", "monedareajustableporipc",
                "monedareajustableportipodecambio", "monedaextranjera"]:
        if col in df_all.columns:
            df_all[f"{col}_num"] = pd.to_numeric(
                df_all[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False),
                errors="coerce",
            )

    return df_all


def tarea1_extraer_colocaciones():
    """Extrae todas las series de colocaciones vía API."""
    print("\n" + "=" * 80)
    print("TAREA 1: EXTRACCIÓN DE COLOCACIONES VÍA API CMF")
    print(f"  Período: {YEAR_START} a {YEAR_END}")
    print(f"  Códigos: {len(API_CODES)}")
    print(f"  Requests estimados: {len(API_CODES) * (YEAR_END - YEAR_START + 1)}")
    print("=" * 80)

    all_frames = []

    for codigo, label in API_CODES.items():
        print(f"\n  ── {codigo} — {label} ──")
        df = fetch_balance_serie(codigo, label)
        if not df.empty:
            all_frames.append(df)
            print(f"  → {len(df)} filas")
        else:
            print(f"  → sin datos")

    if all_frames:
        df_all = pd.concat(all_frames, ignore_index=True)

        # Seleccionar y renombrar columnas útiles
        cols_rename = {
            "codigocuenta": "codigo_cuenta",
            "descripcioncuenta": "descripcion_cuenta",
            "codigoinstitucion": "codigo_institucion",
            "nombreinstitucion": "entidad",
            "anho": "year",
            "mes": "month",
            "monedatotal": "monto_total_raw",
            "monedatotal_num": "monto_total",
            "monedachilenanoreajustable_num": "monto_clp_nr",
            "monedaextranjera_num": "monto_extranjera",
            "cuenta_label": "cuenta",
            "periodo": "periodo",
        }

        # Solo renombrar las que existan
        cols_exist = {k: v for k, v in cols_rename.items() if k in df_all.columns}
        df_out = df_all.rename(columns=cols_exist)

        # Seleccionar columnas finales
        cols_final = [v for v in cols_rename.values() if v in df_out.columns]
        df_out = df_out[cols_final]

        output_file = OUTPUT_DIR / "api_cmf_colocaciones_por_banco.xlsx"
        df_out.to_excel(output_file, index=False)

        print(f"\n  ✅ Guardado: {output_file}")
        print(f"  Total: {len(df_out)} filas")
        print(f"  Cuentas: {df_out['cuenta'].nunique()}")
        print(f"  Períodos: {df_out['periodo'].nunique()}")
        print(f"  Instituciones: {df_out['entidad'].nunique()}")

        print("\n  Resumen por cuenta:")
        for cuenta, grp in df_out.groupby("cuenta"):
            periodos = grp["periodo"].nunique()
            bancos = grp["entidad"].nunique()
            print(f"    {cuenta}: {periodos} meses × {bancos} bancos = {len(grp)} filas")

        # Muestra: Top TC stock último período
        ultimo = df_out["periodo"].max()
        tc = df_out[(df_out["cuenta"] == "Deudores_TC") & (df_out["periodo"] == ultimo)]
        tc = tc.sort_values("monto_total", ascending=False)
        print(f"\n  Top TC Stock {ultimo}:")
        for _, r in tc.head(6).iterrows():
            monto_mm = r["monto_total"] / 1e6 if pd.notna(r["monto_total"]) else 0
            print(f"    {r['entidad']}: ${monto_mm:,.0f} MM")

    else:
        print("\n  ❌ No se extrajeron datos")


# ═══════════════════════════════════════════════════════════════════════════════
# TAREA 2: DESCARGAR MORA CARTERA CONSUMO (XLSX MENSUALES)
# ═══════════════════════════════════════════════════════════════════════════════

MORA_ARTICLES = {
    "cartera_vencida": [
        ("109115", "2026-02"), ("103971", "2026-01"), ("103185", "2025-12"),
        ("102407", "2025-11"), ("101096", "2025-10"), ("100155", "2025-09"),
        ("99053", "2025-08"), ("98092", "2025-07"), ("97057", "2025-06"),
        ("96043", "2025-05"), ("94891", "2025-04"), ("93985", "2025-03"),
    ],
    "morosidad_90d": [
        ("109116", "2026-02"), ("103972", "2026-01"), ("103187", "2025-12"),
        ("102408", "2025-11"), ("101097", "2025-10"), ("100156", "2025-09"),
        ("99054", "2025-08"), ("98093", "2025-07"), ("97058", "2025-06"),
        ("96044", "2025-05"), ("94892", "2025-04"), ("93986", "2025-03"),
        ("92947", "2025-02"), ("92042", "2025-01"),
    ],
}


def tarea2_descargar_mora():
    """Descarga XLSX mensuales de mora."""
    print(f"\n{'=' * 80}")
    print(f"TAREA 2: DESCARGA DE MORA CARTERA")
    print("=" * 80)

    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    ok = 0
    err = 0

    for tipo, articles in MORA_ARTICLES.items():
        print(f"\n  ── {tipo} ({len(articles)} meses) ──")
        for article_id, periodo in articles:
            fname = f"{tipo}_{periodo}_{article_id}.xlsx"
            fpath = MORA_DIR / fname

            if fpath.exists():
                print(f"    ⏭️  {periodo} ya existe")
                continue

            url = f"https://www.cmfchile.cl/portal/estadisticas/617/articles-{article_id}_recurso_1.xlsx"
            try:
                r = session.get(url, timeout=30)
                r.raise_for_status()
                if len(r.content) < 1000:
                    print(f"    ⚠️  {periodo} archivo muy pequeño")
                    err += 1
                    continue
                fpath.write_bytes(r.content)
                print(f"    ✅  {periodo} — {len(r.content)/1024:.0f} KB")
                ok += 1
            except Exception as e:
                print(f"    ❌  {periodo} — {e}")
                err += 1
            time.sleep(1)

    print(f"\n  {ok} descargados, {err} errores → {MORA_DIR}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("CMF — Extracción API + Mora v3 (parsing corregido)")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Output: {OUTPUT_DIR}")

    tarea1_extraer_colocaciones()
    tarea2_descargar_mora()

    print("\n" + "=" * 80)
    print("COMPLETADO")
    print("=" * 80)
