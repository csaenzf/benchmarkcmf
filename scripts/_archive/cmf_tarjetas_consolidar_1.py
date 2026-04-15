"""
CMF Chile - Consolidador de Reportes de Tarjetas v2.0
=====================================================
Consolida los 3 informes de la CMF en una tabla única tipo fact table:
  1. CMF_InformeTrjCreditoBancarias.xlsx   (Crédito Bancario)
  2. CMF_InformeTrjCreditoNoBancarias.xlsx (Crédito No Bancario)
  3. CMF_InformeTrjDeditoATM.xlsx          (Débito y ATM)

Columnas de salida:
  Fecha | Emisor_Formal | Emisor_Comercial | Marca | Tipo_Institucion |
  Producto | Titular_Adicional | Apertura | Nombre_KPI | Unidad | Valor_KPI

Uso:
  python cmf_tarjetas_consolidar.py

Requisitos:
  pip install pandas openpyxl
"""

import pandas as pd
import numpy as np
import warnings
import re
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURACIÓN - Ajustar rutas según tu entorno
# ============================================================
INPUT_DIR = Path("C:\Dropbox\CMF_API\CMF_Reportes_Excel\Data")
FILE_CREDITO_BANCARIO = "CMF_InformeTrjCreditoBancarias.xlsx"
FILE_CREDITO_NO_BANCARIO = "CMF_InformeTrjCreditoNoBancarias.xlsx"
FILE_DEBITO_ATM = "CMF_InformeTrjDeditoATM.xlsx"
OUTPUT_FILE = "CMF_Tarjetas_Consolidado.xlsx"
EXCLUIR_CEROS = True


# ============================================================
# MAPEO DE NOMBRES COMERCIALES
# ============================================================
# Clave: nombre formal exacto (o base antes de " - Tarjeta")
# Valor: nombre comercial
NOMBRE_COMERCIAL = {
    # --- Bancos ---
    "BBVA":                               "BBVA",
    "BCI":                                "BCI",
    "Banco BICE":                         "BICE",
    "Banco Consorcio":                    "Banco Consorcio",
    "Banco Falabella":                    "Banco Falabella",
    "Banco Internacional":                "Banco Internacional",
    "Banco Itaú Chile":                   "Itaú",
    "Banco Itaú Chile (*)":               "Itaú (legacy)",
    "Banco París":                        "Banco París",
    "Banco Ripley":                       "Banco Ripley",
    "Banco Santander":                    "Santander",
    "Banco Security":                     "Security",
    "Banco de Chile":                     "Banco de Chile",
    "Banco del Estado de Chile":          "BancoEstado",
    "CAR S.A.":                           "Ripley",
    "CAT Administradora de Tarjetas":     "CAT (Cencosud)",
    "CMR Falabella S.A (SAG)":            "CMR Falabella (SAG)",
    "Consorcio Tarjetas de Crédito":      "Consorcio",
    "Coopeuch":                           "Coopeuch",
    "Corpbanca":                          "Corpbanca",
    "HSBC":                               "HSBC",
    "Scotiabank":                         "Scotiabank",
    "Servicios Financieros y Administración de Créditos Comerciales S.A. (SAG)": "Cencosud (SAG)",

    # --- No Bancarias ---
    "ABC Inversiones Ltda.":              "ABCDin",
    "Cencosud":                           "Cencosud",
    "Comercializadora y Administradora de Tarjetas Extra S.A.": "Extra (La Polar)",
    "Consorcio tarjetas de crédito":      "Consorcio",
    "Créditos Organización y Finanzas S.A.": "ABCDin (COF)",
    "Efectivo Ltda.":                     "Johnson's",
    "Fiso S.A.":                          "FISO",
    "Inversiones y Tarjetas S.A.":        "Hites",
    "LP S.A.":                            "La Polar",
    "Matic Kard":                         "SBPay",
    "Matic Kard S.A.":                    "SBPay",
    "Presto S.A.":                        "Presto (Lider/Walmart)",
    "Promotora CMR Falabella S.A.":       "CMR Falabella",
    "SCG S.A.":                           "La Polar (SCG)",
    "SMU Corp":                           "SMU (Unimarc)",
    "SMU Corp S.A.":                      "SMU (Unimarc)",
    "Sociedad Emisora de tarjetas CyD":   "CyD",
    "Sociedad de Créditos Comerciales":   "Corona (SCC)",
    "Solventa":                           "Cruz Verde (Solventa)",
    "Tenpo Payments S.A.":                "Tenpo",
    "Tricard S.A.":                       "Tricot (Tricard)",

    # --- Agregados / Sistema ---
    "Total Sistema":                      "Total Sistema",
    "Total Sistema No Bancario":          "Total Sistema No Bancario",
    "Todas las entidades":                "Todas las entidades",
}


# ============================================================
# NORMALIZACIÓN DE KPIs
# ============================================================
# Patrón: KPI original → (KPI normalizado, Apertura)
# "Apertura" indica si el dato está desglosado por Emisor, Marca, etc.
KPI_NORMALIZE = {
    # Crédito Bancarias - Agregados
    "Tarjetas Vigentes":                        ("Tarjetas Vigentes",           "Agregado"),
    "Tarjetas con Operaciones":                 ("Tarjetas con Operaciones",    "Agregado"),
    "Indice de Utilizacion":                    ("Indice de Utilizacion",       "Agregado"),

    # Crédito Bancarias - Por Emisor
    "Tarjetas Vigentes por Emisor":             ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas con Operaciones por Emisor":      ("Tarjetas con Operaciones",    "Emisor"),
    "Nro Avances Efectivo por Emisor":          ("Nro Avances Efectivo",        "Emisor"),
    "Monto Avances Efectivo por Emisor":        ("Monto Avances Efectivo",      "Emisor"),
    "Nro Cargos Servicios por Emisor":          ("Nro Cargos Servicios",        "Emisor"),
    "Monto Cargos Servicios por Emisor":        ("Monto Cargos Servicios",      "Emisor"),
    "Nro Compras por Emisor":                   ("Nro Compras",                 "Emisor"),
    "Monto Compras por Emisor":                 ("Monto Compras",               "Emisor"),

    # Crédito Bancarias - Por Marca
    "Tarjetas Vigentes por Marca":              ("Tarjetas Vigentes",           "Marca"),
    "Tarjetas con Operaciones por Marca":       ("Tarjetas con Operaciones",    "Marca"),
    "Nro Avances Efectivo por Marca":           ("Nro Avances Efectivo",        "Marca"),
    "Monto Avances Efectivo por Marca":         ("Monto Avances Efectivo",      "Marca"),
    "Nro Compras por Marca":                    ("Nro Compras",                 "Marca"),
    "Monto Compras por Marca":                  ("Monto Compras",               "Marca"),
    "Nro Cargos Servicios por Marca":           ("Nro Cargos Servicios",        "Marca"),
    "Monto Cargos Servicios por Marca":         ("Monto Cargos Servicios",      "Marca"),

    # Crédito Bancarias - Tipo Transacción
    "Nro Operaciones por Tipo Transaccion":     ("Nro Operaciones",             "Tipo Transaccion"),
    "Monto Operaciones por Tipo Transaccion":   ("Monto Operaciones",           "Tipo Transaccion"),

    # Crédito No Bancarias - Por Emisor y Marca (combinado en columnas)
    "Tarjetas Vigentes por Emisor":             ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas con Operaciones por Emisor":      ("Tarjetas con Operaciones",    "Emisor"),
    "Nro Operaciones por Emisor y Marca":       ("Nro Operaciones",             "Emisor y Marca"),
    "Monto Operaciones por Emisor y Marca":     ("Monto Operaciones",           "Emisor y Marca"),
    "Monto Creditos Al Dia":                    ("Monto Creditos Al Dia",       "Emisor"),
    "Monto Mora Total":                         ("Monto Mora Total",            "Emisor"),
    "Porcentaje Creditos Al Dia":               ("% Creditos Al Dia",           "Emisor"),
    "Porcentaje Mora Total Sistema":            ("% Mora",                      "Agregado"),
    "Porcentaje Mora por Emisor":               ("% Mora Total",                "Emisor"),
    "Porcentaje Mora hasta 29 dias":            ("% Mora hasta 29 dias",        "Emisor"),
    "Porcentaje Mora 30-89 dias":               ("% Mora 30-89 dias",           "Emisor"),
    "Porcentaje Mora 90-179 dias":              ("% Mora 90-179 dias",          "Emisor"),
    "Porcentaje Mora 180 dias a 1 año":         ("% Mora 180 dias a 1 año",     "Emisor"),

    # Débito / ATM - Agregados
    "Tarjetas Debito Vigentes":                 ("Tarjetas Vigentes",           "Agregado"),
    "Tarjetas ATM Vigentes":                    ("Tarjetas Vigentes",           "Agregado"),
    "Tarjetas Debito/ATM con Operaciones":      ("Tarjetas con Operaciones",    "Agregado"),
    "Operaciones Tarjetas Debito/ATM":          ("Nro Operaciones",             "Agregado"),
    "Nro Giros Debito":                         ("Nro Giros",                   "Agregado"),
    "Nro Transacciones Debito":                 ("Nro Transacciones",           "Agregado"),

    # Débito / ATM - Por Emisor
    "Tarjetas Debito Vigentes por Emisor":              ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas ATM Vigentes por Emisor":                 ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas Debito Vigentes Titulares por Emisor":    ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas Debito Vigentes Adicionales por Emisor":  ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas ATM Vigentes Titulares por Emisor":       ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas ATM Vigentes Adicionales por Emisor":     ("Tarjetas Vigentes",           "Emisor"),
    "Tarjetas Debito con Operaciones por Emisor":       ("Tarjetas con Operaciones",    "Emisor"),
    "Tarjetas ATM con Operaciones por Emisor":          ("Tarjetas con Operaciones",    "Emisor"),
    "Nro Giros Debito por Emisor":                      ("Nro Giros",                   "Emisor"),
    "Monto Giros Debito por Emisor":                    ("Monto Giros",                 "Emisor"),
    "Nro Transacciones Debito por Emisor":              ("Nro Transacciones",           "Emisor"),
    "Monto Transacciones Debito por Emisor":            ("Monto Transacciones",         "Emisor"),
    "Nro Operaciones Debito/ATM por Emisor":            ("Nro Operaciones",             "Emisor"),
    "Monto Operaciones Debito/ATM por Emisor":          ("Monto Operaciones",           "Emisor"),
}

# Mapeo para la hoja OPMORA_PORC: los "Banco_Entidad" son en realidad sub-KPIs
MORA_SISTEMA_MAP = {
    "Porcentaje de créditos al día":                                          "% Creditos Al Dia",
    "Porcentaje de créditos con mora total":                                  "% Mora Total",
    "Porcentaje de créditos con mora menos de 30 días":                       "% Mora hasta 29 dias",
    "Porcentaje de créditos con mora de 30 días o más, pero menos de 90 días":"% Mora 30-89 dias",
    "Porcentaje de créditos con mora de 90 días o más, pero menos de 180 días":"% Mora 90-179 dias",
    "Porcentaje de créditos con mora de 180 días o más, pero menos de 1 año": "% Mora 180 dias a 1 año",
}

# Mapeo para Total Sistema con tipo transacción
TIPO_TRANSAC_MAP = {
    "Avances en efectivo efectuados con tarjetas de crédito": "Avance Efectivo",
    "Cargos por servicios efectuados con tarjetas de crédito": "Cargo Servicios",
    "Compras efectuados con tarjetas de crédito": "Compras",
}


# ============================================================
# FUNCIONES DE LECTURA (mismas que v1)
# ============================================================
def read_cmf_sheet(filepath, sheet_name, kpi_name, producto, tipo_inst,
                   titular_adicional="Total"):
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
    raw_unit = str(df.iloc[1, 1]).strip() if pd.notna(df.iloc[1, 1]) else ""
    unidad = raw_unit.replace("(", "").replace(")", "").strip()
    headers = df.iloc[3].tolist()
    headers[0] = "Fecha"
    data = df.iloc[4:].copy()
    data.columns = headers
    data = data.dropna(subset=["Fecha"])
    value_vars = [c for c in data.columns if c != "Fecha" and pd.notna(c)]
    melted = data.melt(id_vars=["Fecha"], value_vars=value_vars,
                       var_name="Entidad_Original", value_name="Valor_KPI")
    melted["Valor_KPI"] = pd.to_numeric(melted["Valor_KPI"], errors="coerce")
    melted = melted.dropna(subset=["Valor_KPI"])
    if EXCLUIR_CEROS:
        melted = melted[melted["Valor_KPI"] != 0]
    melted["Producto"] = producto
    melted["Tipo_Institucion"] = tipo_inst
    melted["Titular_Adicional"] = titular_adicional
    melted["Nombre_KPI_Original"] = kpi_name
    melted["Unidad"] = unidad
    return melted


def read_agg_titadic(filepath, sheet_name, kpi_name, producto, tipo_inst):
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
        tit = "Titular" if "titular" in col_lower else ("Adicional" if "adicional" in col_lower else "Total")
        temp = data[["Fecha", col]].copy()
        temp.columns = ["Fecha", "Valor_KPI"]
        temp["Valor_KPI"] = pd.to_numeric(temp["Valor_KPI"], errors="coerce")
        temp = temp.dropna(subset=["Valor_KPI"])
        if EXCLUIR_CEROS:
            temp = temp[temp["Valor_KPI"] != 0]
        temp["Entidad_Original"] = "Total Sistema"
        temp["Producto"] = producto
        temp["Tipo_Institucion"] = tipo_inst
        temp["Titular_Adicional"] = tit
        temp["Nombre_KPI_Original"] = kpi_name
        temp["Unidad"] = unidad
        results.append(temp)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def safe_read(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        sheet = args[1] if len(args) > 1 else "?"
        print(f"  ⚠ Error en hoja '{sheet}': {e}")
        return pd.DataFrame()


# ============================================================
# POST-PROCESAMIENTO: Normalizar KPIs y Nombres
# ============================================================
def post_process(df):
    """
    1. Normaliza KPIs → Nombre_KPI limpio + Apertura
    2. Separa Emisor y Marca en entidades con " - Tarjeta X"
    3. Mapea nombres comerciales
    4. Corrige casos especiales (Mora Sistema, Tipo Transaccion)
    """

    # --- 1. Normalizar KPIs ---
    df["Nombre_KPI"] = df["Nombre_KPI_Original"].map(
        lambda x: KPI_NORMALIZE.get(x, (x, "Desconocido"))[0]
    )
    df["Apertura"] = df["Nombre_KPI_Original"].map(
        lambda x: KPI_NORMALIZE.get(x, ("", "Desconocido"))[1]
    )

    # --- 2. Separar Emisor / Marca en entidades combinadas ---
    # Patrón: "Emisor Formal - Tarjeta NombreMarca"
    mask_tarjeta = df["Entidad_Original"].str.contains(" - Tarjeta ", na=False)

    # Extraer emisor formal (antes de " - Tarjeta ")
    df["Emisor_Formal"] = df["Entidad_Original"]
    df.loc[mask_tarjeta, "Emisor_Formal"] = (
        df.loc[mask_tarjeta, "Entidad_Original"]
        .str.split(" - Tarjeta ").str[0]
    )

    # Extraer marca (después de " - Tarjeta ")
    df["Marca"] = ""
    df.loc[mask_tarjeta, "Marca"] = (
        df.loc[mask_tarjeta, "Entidad_Original"]
        .str.split(" - Tarjeta ").str[1]
    )

    # Para entradas de apertura Marca (ej: "Tarjeta Visa" → Marca = "Visa")
    mask_marca_apertura = (df["Apertura"] == "Marca") & (~mask_tarjeta)
    mask_starts_tarjeta = mask_marca_apertura & df["Entidad_Original"].str.startswith("Tarjeta ", na=False)
    df.loc[mask_starts_tarjeta, "Marca"] = (
        df.loc[mask_starts_tarjeta, "Entidad_Original"].str.replace("Tarjeta ", "", n=1)
    )
    df.loc[mask_starts_tarjeta, "Emisor_Formal"] = "Todas las entidades"

    # --- 3. Corregir Apertura: si tiene Marca extraída, es "Emisor y Marca" ---
    mask_has_marca = (df["Marca"] != "") & (df["Apertura"] == "Emisor")
    df.loc[mask_has_marca, "Apertura"] = "Emisor y Marca"

    # --- 4. Normalizar nombres de Marca ---
    MARCA_NORMALIZE = {
        "VISA": "Visa",
        "Censosud": "Cencosud",
        "Lider Martercard": "Lider Mastercard",
        "Martercard": "Mastercard",
        "Mas Easy": "Más Easy",
    }
    df["Marca"] = df["Marca"].replace(MARCA_NORMALIZE)

    # --- 5. Corregir caso especial: Mora Total Sistema ---
    # En estas filas, Entidad_Original contiene el sub-KPI, no la entidad
    mask_mora = df["Entidad_Original"].str.startswith("Porcentaje de créditos", na=False)
    df.loc[mask_mora, "Nombre_KPI"] = df.loc[mask_mora, "Entidad_Original"].map(MORA_SISTEMA_MAP)
    df.loc[mask_mora, "Emisor_Formal"] = "Total Sistema No Bancario"
    df.loc[mask_mora, "Apertura"] = "Agregado"

    # --- 6. Corregir caso especial: Tipo Transacción ---
    mask_tt = df["Entidad_Original"].str.startswith("Total Sistema (", na=False)
    for original, clean in TIPO_TRANSAC_MAP.items():
        mask_match = mask_tt & df["Entidad_Original"].str.contains(original, na=False, regex=False)
        df.loc[mask_match, "Marca"] = clean  # Usamos Marca para el tipo de transacción
        df.loc[mask_match, "Emisor_Formal"] = "Total Sistema"

    # --- 7. Mapear nombre comercial ---
    df["Emisor_Comercial"] = df["Emisor_Formal"].map(NOMBRE_COMERCIAL)
    # Fallback: si no hay mapeo, usar el nombre formal limpio
    df["Emisor_Comercial"] = df["Emisor_Comercial"].fillna(df["Emisor_Formal"])

    # --- 8. Asegurar que Marca sea string limpio (sin NaN) ---
    df["Marca"] = df["Marca"].fillna("").astype(str)

    return df


# ============================================================
# DEFINICIÓN DE HOJAS A PROCESAR
# ============================================================

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

DEBITO_AGG = [
    ("NTRJDEBVIG",  "Tarjetas Debito Vigentes",           "Debito"),
    ("NTRJATMVIG",  "Tarjetas ATM Vigentes",              "ATM"),
    ("COPEDEBATM",  "Tarjetas Debito/ATM con Operaciones", "Debito/ATM"),
    ("OPTRJDEBATM", "Operaciones Tarjetas Debito/ATM",    "Debito/ATM"),
    ("NGIRDEB",     "Nro Giros Debito",                   "Debito"),
    ("NTRXDEB",     "Nro Transacciones Debito",           "Debito"),
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
    print("CMF Chile - Consolidador de Tarjetas v2.0")
    print("=" * 60)

    f_cb  = INPUT_DIR / FILE_CREDITO_BANCARIO
    f_cnb = INPUT_DIR / FILE_CREDITO_NO_BANCARIO
    f_deb = INPUT_DIR / FILE_DEBITO_ATM

    for f in [f_cb, f_cnb, f_deb]:
        if not f.exists():
            print(f"❌ Archivo no encontrado: {f}")
            return
    print("✅ Archivos fuente encontrados\n")

    all_frames = []

    # === 1. CRÉDITO BANCARIAS ===
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
            # Preservar el nombre original para que post_process lo procese
            df["Entidad_Original"] = "Total Sistema (" + df["Entidad_Original"].astype(str) + ")"
            all_frames.append(df)

    # === 2. CRÉDITO NO BANCARIAS ===
    print("📄 Procesando: Crédito No Bancarias...")

    for sn, (kpi, tit) in CREDITO_NO_BANCARIO.items():
        df = safe_read(read_cmf_sheet, f_cnb, sn, kpi, "Credito", "No Financiera", tit)
        if len(df): all_frames.append(df)

    # === 3. DÉBITO / ATM ===
    print("📄 Procesando: Débito / ATM...")

    for sn, kpi, prod in DEBITO_AGG:
        df = safe_read(read_agg_titadic, f_deb, sn, kpi, prod, "Financiera")
        if len(df): all_frames.append(df)

    for sn, (kpi, prod, tit) in DEBITO_EMISOR.items():
        df = safe_read(read_cmf_sheet, f_deb, sn, kpi, prod, "Financiera", tit)
        if len(df): all_frames.append(df)

    # === CONSOLIDAR ===
    print(f"\n🔗 Consolidando {len(all_frames)} bloques...")
    consolidated = pd.concat(all_frames, ignore_index=True)
    consolidated["Fecha"] = pd.to_datetime(consolidated["Fecha"], errors="coerce")
    consolidated = consolidated.dropna(subset=["Fecha"])

    # === POST-PROCESAR ===
    print("🔧 Normalizando KPIs y nombres comerciales...")
    consolidated = post_process(consolidated)

    # === ORDENAR Y SELECCIONAR COLUMNAS FINALES ===
    final_cols = [
        "Fecha",
        "Emisor_Comercial",
        "Emisor_Formal",
        "Marca",
        "Tipo_Institucion",
        "Producto",
        "Titular_Adicional",
        "Apertura",
        "Nombre_KPI",
        "Unidad",
        "Valor_KPI",
    ]
    consolidated = consolidated[final_cols]
    consolidated = consolidated.sort_values(
        ["Fecha", "Producto", "Emisor_Comercial", "Nombre_KPI"]
    ).reset_index(drop=True)

    # === GUARDAR ===
    output_path = INPUT_DIR / OUTPUT_FILE
    consolidated.to_excel(output_path, index=False, sheet_name="Data", freeze_panes=(1, 0))

    elapsed = (datetime.now() - start).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"✅ Consolidado v2.0 generado exitosamente")
    print(f"   📊 Filas:        {len(consolidated):,}")
    print(f"   📅 Rango:        {consolidated['Fecha'].min():%Y-%m} → {consolidated['Fecha'].max():%Y-%m}")
    print(f"   🏦 Emisores:     {consolidated['Emisor_Comercial'].nunique()}")
    print(f"   🏷️  Marcas:       {consolidated['Marca'].nunique()} (incl. vacío)")
    print(f"   📈 KPIs:         {consolidated['Nombre_KPI'].nunique()}")
    print(f"   🔍 Aperturas:    {sorted(consolidated['Apertura'].unique())}")
    print(f"   💾 Archivo:      {output_path}")
    print(f"   ⏱  Tiempo:       {elapsed:.1f}s")
    print(f"{'=' * 60}")

    # Resumen rápido
    print("\n📋 KPIs normalizados:")
    for kpi in sorted(consolidated["Nombre_KPI"].unique()):
        n = len(consolidated[consolidated["Nombre_KPI"] == kpi])
        print(f"   {kpi:40s} → {n:>6,} filas")

    # Nombres sin mapeo comercial (usaron fallback)
    all_formals = consolidated["Emisor_Formal"].unique()
    sin_mapeo = [f for f in all_formals if f not in NOMBRE_COMERCIAL]
    if sin_mapeo:
        print(f"\n⚠ Entidades sin nombre comercial asignado ({len(sin_mapeo)}):")
        print(f"  (agregá estas al diccionario NOMBRE_COMERCIAL)")
        for s in sorted(sin_mapeo):
            print(f"   \"{s}\": \"{s}\",")
    else:
        print("\n✅ Todas las entidades tienen nombre comercial asignado")


if __name__ == "__main__":
    main()
