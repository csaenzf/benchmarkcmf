"""
CMF Chile - Consolidador de Reportes de Tarjetas
=================================================
Consolida los 3 informes de la CMF en una tabla única tipo fact table:
  1. CMF_InformeTrjCreditoBancarias.xlsx   (Crédito Bancario)
  2. CMF_InformeTrjCreditoNoBancarias.xlsx (Crédito No Bancario)
  3. CMF_InformeTrjDeditoATM.xlsx          (Débito y ATM)

Columnas de salida:
  Fecha | Banco_Entidad | Tipo_Institucion | Producto | Titular_Adicional | Nombre_KPI | Unidad | Valor_KPI

Uso:
  python cmf_tarjetas_consolidar.py

Requisitos:
  pip install pandas openpyxl
"""

import pandas as pd
import numpy as np
import warnings
import os
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURACIÓN - Ajustar rutas según tu entorno
# ============================================================
# Carpeta donde están los 3 archivos CMF
INPUT_DIR = Path("C:\Dropbox\CMF_API\CMF_Reportes_Excel\Data")  # Cambiar a tu ruta, ej: Path(r"C:\Users\crist\Dropbox\CMF")

# Nombres de los archivos fuente
FILE_CREDITO_BANCARIO = "CMF_InformeTrjCreditoBancarias.xlsx"
FILE_CREDITO_NO_BANCARIO = "CMF_InformeTrjCreditoNoBancarias.xlsx"
FILE_DEBITO_ATM = "CMF_InformeTrjDeditoATM.xlsx"

# Archivo de salida
OUTPUT_FILE = "CMF_Tarjetas_Consolidado.xlsx"

# Excluir filas con valor 0 o vacío
EXCLUIR_CEROS = True


# ============================================================
# FUNCIONES DE LECTURA
# ============================================================
def read_cmf_sheet(filepath, sheet_name, kpi_name, producto, tipo_inst,
                   titular_adicional="Total"):
    """
    Lee una hoja CMF con formato:
      Fila 0: título
      Fila 1: unidad (ej: "número", "millones de pesos")
      Fila 2: link BEST
      Fila 3: headers (Fecha + entidades como columnas)
      Fila 4+: datos
    Hace un melt para pasar de wide a long.
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    # Extraer unidad desde fila 1
    raw_unit = str(df.iloc[1, 1]).strip() if pd.notna(df.iloc[1, 1]) else ""
    unidad = raw_unit.replace("(", "").replace(")", "").strip()

    # Headers en fila 3
    headers = df.iloc[3].tolist()
    headers[0] = "Fecha"

    # Data desde fila 4
    data = df.iloc[4:].copy()
    data.columns = headers
    data = data.dropna(subset=["Fecha"])

    # Columnas de entidades (excluir NaN)
    value_vars = [c for c in data.columns if c != "Fecha" and pd.notna(c)]

    # Melt: wide → long
    melted = data.melt(
        id_vars=["Fecha"],
        value_vars=value_vars,
        var_name="Banco_Entidad",
        value_name="Valor_KPI",
    )

    # Limpiar valores
    melted["Valor_KPI"] = pd.to_numeric(melted["Valor_KPI"], errors="coerce")
    melted = melted.dropna(subset=["Valor_KPI"])
    if EXCLUIR_CEROS:
        melted = melted[melted["Valor_KPI"] != 0]

    # Agregar dimensiones
    melted["Producto"] = producto
    melted["Tipo_Institucion"] = tipo_inst
    melted["Titular_Adicional"] = titular_adicional
    melted["Nombre_KPI"] = kpi_name
    melted["Unidad"] = unidad

    return melted


def read_agg_titadic(filepath, sheet_name, kpi_name, producto, tipo_inst):
    """
    Lee hojas agregadas donde las columnas son Titular / Adicional / Total
    (sin desglose por entidad). Asigna Banco_Entidad = 'Total Sistema'.
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    raw_unit = str(df.iloc[1, 1]).strip() if pd.notna(df.iloc[1, 1]) else ""
    unidad = raw_unit.replace("(", "").replace(")", "").strip()

    headers = df.iloc[3].tolist()
    headers[0] = "Fecha"
    data = df.iloc[4:].copy()
    data.columns = headers
    data = data.dropna(subset=["Fecha"])

    results = []
    for col in data.columns[1:]:
        if pd.isna(col):
            continue
        col_lower = str(col).lower()
        if "titular" in col_lower:
            tit = "Titular"
        elif "adicional" in col_lower:
            tit = "Adicional"
        else:
            tit = "Total"

        temp = data[["Fecha", col]].copy()
        temp.columns = ["Fecha", "Valor_KPI"]
        temp["Valor_KPI"] = pd.to_numeric(temp["Valor_KPI"], errors="coerce")
        temp = temp.dropna(subset=["Valor_KPI"])
        if EXCLUIR_CEROS:
            temp = temp[temp["Valor_KPI"] != 0]

        temp["Banco_Entidad"] = "Total Sistema"
        temp["Producto"] = producto
        temp["Tipo_Institucion"] = tipo_inst
        temp["Titular_Adicional"] = tit
        temp["Nombre_KPI"] = kpi_name
        temp["Unidad"] = unidad
        results.append(temp)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def safe_read(func, *args, **kwargs):
    """Wrapper para no detener el proceso si falla una hoja."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        sheet = args[1] if len(args) > 1 else "?"
        print(f"  ⚠ Error en hoja '{sheet}': {e}")
        return pd.DataFrame()


# ============================================================
# DEFINICIÓN DE HOJAS A PROCESAR
# ============================================================

# --- 1. Crédito Bancarias ---
CREDITO_BANCARIO_AGG = [
    ("tarj_vig", "Tarjetas Vigentes"),
    ("tarj_con", "Tarjetas con Operaciones"),
    ("ind_util", "Indice de Utilizacion"),
]

CREDITO_BANCARIO_EMISOR = {
    "tarj_vig_tit_emi":       ("Tarjetas Vigentes por Emisor", "Titular"),
    "tarj_vig_adic_emi":      ("Tarjetas Vigentes por Emisor", "Adicional"),
    "tarj_operac_tit_emi":    ("Tarjetas con Operaciones por Emisor", "Titular"),
    "tarj_operac_adic_emi":   ("Tarjetas con Operaciones por Emisor", "Adicional"),
    "nro_operac_avc_emi":     ("Nro Avances Efectivo por Emisor", "Total"),
    "mto_operac_avc_emi":     ("Monto Avances Efectivo por Emisor", "Total"),
    "nro_operac_crgserv_emi": ("Nro Cargos Servicios por Emisor", "Total"),
    "mto_operac_crgserv_emi": ("Monto Cargos Servicios por Emisor", "Total"),
    "nro_operac_comp_emi":    ("Nro Compras por Emisor", "Total"),
    "mto_operac_comp_emi":    ("Monto Compras por Emisor", "Total"),
}

CREDITO_BANCARIO_MARCA = {
    "tarj_vig_tit_marc":       ("Tarjetas Vigentes por Marca", "Titular"),
    "tarj_vig_adic_marc":      ("Tarjetas Vigentes por Marca", "Adicional"),
    "tarj_operac_tit_marc":    ("Tarjetas con Operaciones por Marca", "Titular"),
    "tarj_operac_adic_marc":   ("Tarjetas con Operaciones por Marca", "Adicional"),
    "nro_operac_avc_marc":     ("Nro Avances Efectivo por Marca", "Total"),
    "mto_operac_avc_marc":     ("Monto Avances Efectivo por Marca", "Total"),
    "nro_operac_comp_marc":    ("Nro Compras por Marca", "Total"),
    "mto_operac_comp_marc":    ("Monto Compras por Marca", "Total"),
    "nro_operac_crgserv_marc": ("Nro Cargos Servicios por Marca", "Total"),
    "mto_operac_crgserv_marc": ("Monto Cargos Servicios por Marca", "Total"),
}

CREDITO_BANCARIO_TRANSAC = [
    ("nro_operac_tipo_transac", "Nro Operaciones por Tipo Transaccion"),
    ("mto_operac_tipo_transac", "Monto Operaciones por Tipo Transaccion"),
]

# --- 2. Crédito No Bancarias ---
CREDITO_NO_BANCARIO = {
    "TVIGIFI_NUM":       ("Tarjetas Vigentes por Emisor", "Total"),
    "TCOPEIFI_NUM":      ("Tarjetas con Operaciones por Emisor", "Total"),
    "OPIFIMRC_NUM":      ("Nro Operaciones por Emisor y Marca", "Total"),
    "OPIFIMRC_MTO":      ("Monto Operaciones por Emisor y Marca", "Total"),
    "OPALDIAIFI_MTO":    ("Monto Creditos Al Dia", "Total"),
    "OPMORAIFI_MTO":     ("Monto Mora Total", "Total"),
    "OPALDIAIFI_PORC":   ("Porcentaje Creditos Al Dia", "Total"),
    "OPMORA_PORC":       ("Porcentaje Mora Total Sistema", "Total"),
    "OPMORAIFI_PORC":    ("Porcentaje Mora por Emisor", "Total"),
    "OPH29DIFI_PORC":    ("Porcentaje Mora hasta 29 dias", "Total"),
    "OP30D89IFI_PORC":   ("Porcentaje Mora 30-89 dias", "Total"),
    "OP90D179IFI_PORC":  ("Porcentaje Mora 90-179 dias", "Total"),
    "OP180D1AIFI_PORC":  ("Porcentaje Mora 180 dias a 1 año", "Total"),
}

# --- 3. Débito / ATM ---
DEBITO_AGG = [
    ("NTRJDEBVIG",  "Tarjetas Debito Vigentes",          "Debito"),
    ("NTRJATMVIG",  "Tarjetas ATM Vigentes",             "ATM"),
    ("COPEDEBATM",  "Tarjetas Debito/ATM con Operaciones","Debito/ATM"),
    ("OPTRJDEBATM", "Operaciones Tarjetas Debito/ATM",   "Debito/ATM"),
    ("NGIRDEB",     "Nro Giros Debito",                  "Debito"),
    ("NTRXDEB",     "Nro Transacciones Debito",          "Debito"),
]

DEBITO_EMISOR = {
    "TRJDEBVIGIF":  ("Tarjetas Debito Vigentes por Emisor",             "Debito",     "Total"),
    "ATMVIGIF":     ("Tarjetas ATM Vigentes por Emisor",                "ATM",        "Total"),
    "DEBVIGTITIF":  ("Tarjetas Debito Vigentes Titulares por Emisor",   "Debito",     "Titular"),
    "DEBVIGADICIF": ("Tarjetas Debito Vigentes Adicionales por Emisor", "Debito",     "Adicional"),
    "ATMVIGTITIF":  ("Tarjetas ATM Vigentes Titulares por Emisor",      "ATM",        "Titular"),
    "ATMVIGADICIF": ("Tarjetas ATM Vigentes Adicionales por Emisor",    "ATM",        "Adicional"),
    "DEBCOPEIF":    ("Tarjetas Debito con Operaciones por Emisor",      "Debito",     "Total"),
    "ATMCOPEIF":    ("Tarjetas ATM con Operaciones por Emisor",         "ATM",        "Total"),
    "NGIRDEBIF":    ("Nro Giros Debito por Emisor",                     "Debito",     "Total"),
    "MTOGIRDEB":    ("Monto Giros Debito por Emisor",                   "Debito",     "Total"),
    "NTRXDEBIF":    ("Nro Transacciones Debito por Emisor",             "Debito",     "Total"),
    "MTOTRXDEB":    ("Monto Transacciones Debito por Emisor",           "Debito",     "Total"),
    "OPDEBATMIF":   ("Nro Operaciones Debito/ATM por Emisor",           "Debito/ATM", "Total"),
    "MTODEBATMIF":  ("Monto Operaciones Debito/ATM por Emisor",         "Debito/ATM", "Total"),
}


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
def main():
    start = datetime.now()
    print("=" * 60)
    print("CMF Chile - Consolidador de Reportes de Tarjetas")
    print("=" * 60)

    f_cb  = INPUT_DIR / FILE_CREDITO_BANCARIO
    f_cnb = INPUT_DIR / FILE_CREDITO_NO_BANCARIO
    f_deb = INPUT_DIR / FILE_DEBITO_ATM

    # Validar existencia
    for f in [f_cb, f_cnb, f_deb]:
        if not f.exists():
            print(f"❌ Archivo no encontrado: {f}")
            return
    print("✅ Archivos fuente encontrados\n")

    all_frames = []

    # ----- 1. CRÉDITO BANCARIAS -----
    print("📄 Procesando: Crédito Bancarias...")

    for sn, kpi in CREDITO_BANCARIO_AGG:
        df = safe_read(read_agg_titadic, f_cb, sn, kpi, "Credito", "Financiera")
        if len(df): all_frames.append(df)

    for sn, (kpi, tit) in CREDITO_BANCARIO_EMISOR.items():
        df = safe_read(read_cmf_sheet, f_cb, sn, kpi, "Credito", "Financiera", tit)
        if len(df): all_frames.append(df)

    for sn, (kpi, tit) in CREDITO_BANCARIO_MARCA.items():
        df = safe_read(read_cmf_sheet, f_cb, sn, kpi, "Credito", "Financiera", tit)
        if len(df): all_frames.append(df)

    for sn, kpi in CREDITO_BANCARIO_TRANSAC:
        df = safe_read(read_cmf_sheet, f_cb, sn, kpi, "Credito", "Financiera", "Total")
        if len(df):
            df["Banco_Entidad"] = "Total Sistema (" + df["Banco_Entidad"].astype(str) + ")"
            all_frames.append(df)

    # ----- 2. CRÉDITO NO BANCARIAS -----
    print("📄 Procesando: Crédito No Bancarias...")

    for sn, (kpi, tit) in CREDITO_NO_BANCARIO.items():
        df = safe_read(read_cmf_sheet, f_cnb, sn, kpi, "Credito", "No Financiera", tit)
        if len(df): all_frames.append(df)

    # ----- 3. DÉBITO / ATM -----
    print("📄 Procesando: Débito / ATM...")

    for sn, kpi, prod in DEBITO_AGG:
        df = safe_read(read_agg_titadic, f_deb, sn, kpi, prod, "Financiera")
        if len(df): all_frames.append(df)

    for sn, (kpi, prod, tit) in DEBITO_EMISOR.items():
        df = safe_read(read_cmf_sheet, f_deb, sn, kpi, prod, "Financiera", tit)
        if len(df): all_frames.append(df)

    # ----- CONSOLIDAR -----
    print(f"\n🔗 Consolidando {len(all_frames)} bloques...")

    consolidated = pd.concat(all_frames, ignore_index=True)

    # Ordenar columnas
    col_order = [
        "Fecha", "Banco_Entidad", "Tipo_Institucion", "Producto",
        "Titular_Adicional", "Nombre_KPI", "Unidad", "Valor_KPI",
    ]
    consolidated = consolidated[col_order]

    # Limpiar fecha y ordenar
    consolidated["Fecha"] = pd.to_datetime(consolidated["Fecha"], errors="coerce")
    consolidated = consolidated.dropna(subset=["Fecha"])
    consolidated = consolidated.sort_values(
        ["Fecha", "Producto", "Banco_Entidad", "Nombre_KPI"]
    ).reset_index(drop=True)

    # ----- GUARDAR -----
    output_path = INPUT_DIR / OUTPUT_FILE
    consolidated.to_excel(output_path, index=False, sheet_name="Data", freeze_panes=(1, 0))

    elapsed = (datetime.now() - start).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"✅ Consolidado generado exitosamente")
    print(f"   📊 Filas:      {len(consolidated):,}")
    print(f"   📅 Rango:      {consolidated['Fecha'].min():%Y-%m} → {consolidated['Fecha'].max():%Y-%m}")
    print(f"   🏦 Entidades:  {consolidated['Banco_Entidad'].nunique()}")
    print(f"   📈 KPIs:       {consolidated['Nombre_KPI'].nunique()}")
    print(f"   💾 Archivo:    {output_path}")
    print(f"   ⏱  Tiempo:     {elapsed:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
