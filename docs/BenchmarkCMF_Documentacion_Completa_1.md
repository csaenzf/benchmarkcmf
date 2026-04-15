# BenchmarkCMF.cl — Documentación Completa del Dashboard de Inteligencia Competitiva

## 1. Resumen Ejecutivo

**benchmarkcmf.cl** es un dashboard interactivo de inteligencia competitiva para **Banco de Chile** construido con data pública de la CMF (Comisión para el Mercado Financiero de Chile). Permite al banco comparar su performance en tarjetas de crédito y débito contra los principales bancos del mercado chileno.

El dashboard fue desarrollado por Cristobal Sáenz como herramienta de consultoría estratégica. Se compone de una **landing page pública** y un **dashboard protegido** (`/dashboard/`), ambos desplegados en Cloudflare Pages con autenticación Cloudflare Access (lista de emails autorizados, login por OTP).

**Período de datos:** Diciembre 2025 (con series mensuales de 24 meses y series históricas trimestrales desde 2020Q1).
**Última actualización:** Marzo 2026 — versión v3 del dashboard (31/03/2026).

---

## 2. Fuente de Datos

### 2.1 Origen
La data proviene de los **Informes de Tarjetas Bancarias** publicados por la CMF Chile. Cristobal construyó un pipeline de consolidación Python (`cmf_tarjetas_consolidar.py`) que normaliza tres reportes Excel de la CMF en una sola fact table:

- `CMF_InformeTrjCreditoBancarias.xlsx` — Tarjetas de crédito bancarias
- `CMF_InformeTrjCreditoNoBancarias.xlsx` — Tarjetas de crédito no bancarias
- Informes de tarjetas de débito y ATM

El archivo consolidado es `CMF_Tarjetas_Consolidado.xlsx` con una sola hoja "Data".

### 2.2 Estructura del Archivo Consolidado

**106,958 filas** con 15 columnas:

| Columna | Tipo | Descripción | Valores ejemplo |
|---------|------|-------------|-----------------|
| Fecha | datetime | Primer día del mes del reporte | 2009-04-01 a 2025-12-01 |
| Emisor_Comercial | string | Nombre comercial del emisor (normalizado) | Banco de Chile, Santander, BCI... |
| Grupo_Comercial | string | Grupo económico | Scotiabank (agrupa BBVA + Scotiabank legacy) |
| Emisor_Formal | string | Razón social ante CMF | — |
| Marca | string | Red de pago (solo para Apertura=Marca/Emisor y Marca) | Visa, Mastercard, American Express |
| Tipo_Institucion | string | Clasificación CMF | Financiera, No Financiera |
| Producto | string | Tipo de tarjeta | Credito, Debito, ATM, Debito/ATM |
| Titular_Adicional | string | Corte por tipo de tarjetahabiente | Total, Titular, Adicional |
| Apertura | string | Nivel de agregación del dato | Emisor, Marca, Agregado, Tipo Transaccion, Emisor y Marca |
| Nombre_KPI | string | Indicador reportado | (ver lista completa abajo) |
| Unidad | string | Unidad de medida | millones de pesos, número, % del monto total |
| Valor_KPI | float | Valor numérico del indicador | — |
| Archivo_Fuente | string | Excel original de la CMF | — |
| Hoja_Fuente | string | Pestaña del Excel original | — |
| KPI_Original | string | Nombre original antes de normalización | — |

### 2.3 KPIs Disponibles (23 indicadores)

**Tarjetas (stock):**
- Tarjetas Vigentes — número de tarjetas activas en el sistema
- Tarjetas con Operaciones — tarjetas que registraron al menos una operación en el mes

**Transaccionalidad crédito:**
- Monto Compras (millones de pesos) — valor total de compras con TC
- Nro Compras (número) — cantidad de transacciones de compra
- Monto Avances Efectivo (MM$) — retiros de efectivo con TC
- Nro Avances Efectivo — cantidad de avances
- Monto Cargos Servicios (MM$) — cargos automáticos (seguros, suscripciones)
- Nro Cargos Servicios — cantidad de cargos

**Transaccionalidad débito:**
- Monto Transacciones (MM$) — valor total transacciones débito
- Nro Transacciones — cantidad de transacciones débito
- Monto Giros (MM$) — retiros ATM
- Nro Giros — cantidad de retiros ATM

**Débito/ATM combinado:**
- Monto Operaciones (MM$) — débito + ATM combinado
- Nro Operaciones — débito + ATM combinado

**Morosidad (solo disponible para no bancarias):**
- % Mora Total, % Mora hasta 29 dias, % Mora 30-89 dias, % Mora 90-179 dias, % Mora 180 dias a 1 año
- % Creditos Al Dia, Monto Creditos Al Dia, Monto Mora Total

**Otros:**
- Indice de Utilizacion — solo disponible como Agregado para Total Sistema

### 2.4 Dimensiones de Corte

**Apertura** (cómo se desagrega el dato):
- `Emisor` — dato por banco individual. **Es la apertura principal usada en el dashboard.**
- `Marca` — dato por red de pago (Visa, Mastercard, etc.), solo para "Todas las entidades"
- `Agregado` — total del sistema (usado para Total Sistema, Total Sistema No Bancario)
- `Tipo Transaccion` — compras vs avances vs cargos
- `Emisor y Marca` — cruce banco × red (disponibilidad parcial)

**Producto:**
- `Credito` — tarjetas de crédito
- `Debito` — tarjetas de débito
- `ATM` — tarjetas de cajero automático (legacy, en desuso)
- `Debito/ATM` — consolidado débito + ATM (KPIs: Monto Operaciones, Nro Operaciones)

**Titular_Adicional:**
- `Total` — suma de titulares + adicionales
- `Titular` — solo tarjetas del titular principal
- `Adicional` — solo tarjetas adicionales (familiares, dependientes)

### 2.5 Emisores en el Dashboard

El dashboard se enfoca en **6 bancos principales** (todos Tipo_Institucion = Financiera):

| Banco | Abreviatura | Color |
|-------|-------------|-------|
| Banco de Chile | BdCh | #0033A0 (azul banco) |
| Santander | Sant. | #EC0000 (rojo) |
| BCI | BCI | #FFB800 (amarillo) ← antes #FF6900 naranja |
| BancoEstado | BEst. | #00843D (verde) |
| Itaú | Itaú | #FF6600 (naranja) ← antes #003DA5 azul oscuro |
| Scotiabank | Scotia | #B4272A (rojo oscuro) |

Otros emisores presentes en la data pero NO en el dashboard: BICE, Banco Consorcio, Banco Internacional, Coopeuch, Banco Falabella, Banco Ripley, BBVA (legacy→Scotiabank), Corpbanca (legacy→Itaú), Security, HSBC, y todas las instituciones no bancarias (CMR Falabella, Cencosud, Ripley retail, etc.).

### 2.6 Nota Técnica sobre Totales

Hay una asimetría importante en la data CMF:
- Los datos **por banco** usan `Apertura = Emisor`
- Los datos **totales del sistema** usan `Apertura = Agregado` con `Emisor_Comercial = Total Sistema`
- Para KPIs donde Total Sistema no está disponible (ej: Monto Compras en periodos recientes), el total se computa como **suma de todos los emisores individuales**
- Para Tarjetas Vigentes, sí existe Total Sistema en Agregado → se usa directamente para calcular market share del sistema total (incluyendo no bancarias)
- Para Monto/Nro Compras, el denominador del market share se calcula como suma de los emisores financieros

---

## 3. Estructura del Sitio

### 3.1 Arquitectura General (post-landing v2)

El sitio tiene **dos capas** diferenciadas:

```
benchmarkcmf.cl/              → Landing page pública (sin autenticación)
benchmarkcmf.cl/dashboard/    → Dashboard protegido (Cloudflare Access → OTP)
```

```
[Usuario] → benchmarkcmf.cl (DNS Cloudflare)
    ↓
[Landing page pública] ← index.html + Video_Portada_01.mp4
    ↓ (clic en "Ingresar al Dashboard")
[Cloudflare Access] ← Lista de emails autorizados (OTP por email)
    ↓ (autenticado)
[Cloudflare Pages /dashboard/] ← HTML estático del dashboard
    ↓
[CDN Global] ← SSL automático, cache
```

### 3.2 Stack Técnico

**Landing page (`index.html`):**
- HTML + CSS puro, sin frameworks
- Video de fondo en loop (`Video_Portada_01.mp4`, H264, 1280×720, 8s, ~2.2MB)
- Fuentes: DM Sans + DM Mono + Playfair Display (Google Fonts)
- Diseño: fondo navy oscuro, overlay degradado multicapa, grain sutil, animaciones CSS

**Dashboard (`dashboard/index.html`):**
- React 18.2.0 (UMD desde CDN jsdelivr)
- Chart.js 4.4.1 (UMD desde CDN jsdelivr) — reemplazó a Recharts que no tiene UMD funcional
- Babel Standalone 7.23.9 (runtime en browser)
- Fuentes: DM Sans (UI), JetBrains Mono (datos numéricos)
- Archivo autónomo (~209KB, expandido desde ~33KB por inclusión de 24 meses de data)

**Cambios de UI en v3 (31/03/2026):**
- **Logo SVG de Banco de Chile** embebido en el header (blanco, como data URL base64). Título cambió a "Competitive Intelligence Dashboard".
- **Color highlight de BdCh** cambió de dorado `#C4A962` a azul celeste `#598CFF` (aplica a valores en tablas, pills activos, badges de ranking, bordes de diagnósticos, tabs activos, selector de mes).
- **Footer actualizado:** "Benchmark CMF · [mes seleccionado]" — eliminadas todas las referencias a "Visa Consulting & Analytics".

**Infraestructura:**
- Cloudflare Pages (plan Free)
- Cloudflare Access Zero Trust (plan Free, hasta 50 usuarios)
- Dominio: benchmarkcmf.cl

### 3.3 Pestañas del Dashboard

El dashboard tiene **6 pestañas** (tabs). A continuación se describe la versión v3 (31/03/2026).

#### TAB 1: Resumen (Overview)
**Propósito:** Vista panorámica de la posición de Banco de Chile.

**Filtros interactivos:**
- Producto: Crédito / Débito
- Tipo: Total / Titular / Adicional
- **Vista: Mes / Serie** — toggle entre vista puntual e histórica (nuevo en v3)
- **Selector de mes** — dropdown con los 24 meses disponibles (visible en modo Mes) (nuevo en v3)
- **Selector de KPI** — pills para elegir el KPI del ranking: Tarjetas Vigentes, TC/TD con Operaciones, Monto Compras/Transacciones, Nro Compras/Transacciones (nuevo en v3)

**Modo Mes (barra horizontal):**
- El market share del KPI se muestra **dentro de la barra** (texto blanco semitransparente)
- Valores con un decimal adicional (ej: "795.3K")
- Columnas **YoY** y **MoM** con flechas ▲/▼ coloreadas
- Rankings y tabla YoY son dinámicos según el mes seleccionado
- Tabla YoY muestra los 4 KPIs del producto seleccionado

**Modo Serie (nuevo en v3):**
- Gráfico **stacked bar** (Chart.js) de los últimos 24 meses para el KPI seleccionado
- Tooltip: valor del banco + share en ese mes
- Debajo: gráfico de línea **YoY** mes a mes de cada banco (12 meses con dato anterior)
- Leyenda con los 6 bancos

#### TAB 2: Market Share
**Propósito:** Evolución temporal de la participación de mercado.

**Filtros (v3):**
- **Producto: Crédito / Débito** (nuevo en v3, divisor con barra vertical)
- **4 métricas:** Tarjetas Vigentes | TC/TD con Operaciones | Monto Compras/Transacciones | Nro Compras/Transacciones (antes solo 2)
- **Filtro de emisores:** click en nombre de banco en leyenda activa/desactiva (mínimo 1 banco)

**Datos:**
- Serie temporal **mensual** (24 puntos), antes trimestral (7 puntos)
- Tooltip muestra valor absoluto además del share% (ej: "BdCh: 31.0% · 1.8M")
- BdCh se destaca con línea más gruesa (3px vs 1.5px)

**8 series de market share disponibles:** `cards_c`, `cards_d`, `ops_c`, `ops_d`, `spend_c`, `spend_d`, `nops_c`, `nops_d`.

#### TAB 3: Estratégico
**Propósito:** Benchmark de métricas derivadas de consultoría.

**Filtros (v3):**
- **Producto: Crédito / Débito** (nuevo en v3)
- **Selector de mes** — dropdown para la tabla comparativa (nuevo en v3)

**Tabla comparativa — modo Crédito:**
- Tasa Activación (TC c/ops ÷ TC vigentes)
- ─ divisor ─
- Frecuencia (Compras ÷ TC con operaciones)
- ─ divisor ─
- Ticket Promedio (Monto ÷ Nro compras)
- Spend / Activa (Monto compras ÷ TC c/ops)
- ─ divisor ─
- **Cargo Srv / TC Activa** (NUEVO v3) — Monto cargos servicios ÷ TC con operaciones × 1M
- **Ticket Cargos Srv** (NUEVO v3) — Monto cargos servicios ÷ Nro cargos servicios × 1M

**Tabla comparativa — modo Débito (NUEVO v3):**
- Tasa Activación (TD c/ops ÷ TD vigentes)
- ─ divisor ─
- Frecuencia (Txn ÷ TD c/ops)
- ─ divisor ─
- Ticket Promedio (Monto ÷ Nro transacciones)
- Spend / TD Activa (Monto txn ÷ TD c/ops)

**Rankings:** Badges #1–#6 para **todos los bancos** (antes solo BdCh).

**Tendencias:**
- Los 6 bancos incluidos (antes solo BdCh, Santander, Itaú)
- Pills Crédito: Activación | Frecuencia | Ticket | Spend/Activa | Ticket Cargos Srv
- Pills Débito: Activación | Frecuencia | Ticket | Spend/Activa

#### TAB 4: Cross-Sell
**Propósito:** Analizar la venta cruzada crédito/débito.

**Filtros (v3):**
- **Selector de mes** — dropdown para la tabla comparativa (nuevo en v3)

**Tabla comparativa (v3):**
- TC / TD Vigentes (penetración tarjetas)
- ─ divisor ─
- **TC / TD con Operaciones** (NUEVO v3) — penetración de activas
- ─ divisor ─
- **Monto TC / Monto TD** (NUEVO v3) — ratio monto crédito ÷ débito
- Monto TC / (TC+TD) — share crédito en gasto total
- Nro TC / (TC+TD) — share crédito en operaciones
- *(Eliminados: Ticket Débito y Freq. Débito → movidos a pestaña Estratégico modo Débito)*

**Rankings:** Badges para todos los bancos.

**Gráfico de tendencias (NUEVO v3):** Líneas trimestrales con 5 pills: TC/TD Vigentes | TC/TD Ops | Monto TC/TD | Share Crédito $ | Share Crédito #. 6 bancos con leyenda.

#### TAB 5: Avances
**Propósito:** Revenue mix y exposición al riesgo por avances/giros.

**Filtros (v3):**
- **Selector de mes** (nuevo en v3)

**Sección 1 — Crédito (Avances):**
- Avances / Total TC (peso revenue mix)
- ─ divisor ─
- Ticket Avance (Monto ÷ Nro avances)
- Ticket Compras (comparación)

**Sección 2 — Débito (Giros) (NUEVA v3):**
- Giros / Total TD (peso en revenue mix)
- ─ divisor ─
- Ticket Giro (Monto ÷ Nro giros)
- Ticket Transacciones (comparación)

**Gráfico de tendencias mensuales (NUEVO v3):** 4 pills: Avances/Total Crédito | Ticket Avance | Giros/Total Débito | Ticket Giro. 24 meses, 6 bancos.

#### TAB 6: Adicionales
**Propósito:** Penetración de tarjetas adicionales.

**Filtros (v3):**
- Crédito / Débito
- **Vista: Tabla / Serie** (nuevo en v3)
- **Selector de mes** (en modo Tabla, nuevo en v3)

**Modo Tabla:** Ranking banco | barra | total | adicionales | % adicionales — dinámico por mes seleccionado.

**Modo Serie (NUEVO v3):** Gráfico de líneas mensual (24 meses) de % adicionales por banco. Filtro Crédito/Débito aplica al gráfico.

---

## 4. Métricas Derivadas — Fórmulas y Definiciones

Estas métricas NO existen en la data CMF directamente. Son calculadas como ratios entre KPIs base.

### 4.1 Activación & Engagement

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Tasa de Activación | TC con Operaciones / TC Vigentes × 100 | % de tarjetas que realmente se usan. Mayor = mejor engagement. |
| Frecuencia de compras | Nro Compras / TC con Operaciones | Compras promedio por tarjeta activa en el mes. Mayor = más transaccional. |
| Ops totales / activa | (Nro Compras + Nro Avances + Nro Cargos) / TC con Operaciones | Operaciones totales incluyendo avances y cargos recurrentes. |

### 4.2 Revenue Quality

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Ticket Promedio | Monto Compras / Nro Compras × 1.000.000 | Valor promedio de cada compra en CLP. La multiplicación por 1M es porque Monto está en millones. |
| Spend / Tarjeta Vigente | Monto Compras / TC Vigentes × 1.000.000 | Revenue proxy: cuánto genera cada tarjeta emitida (incluye inactivas). |
| Spend / Tarjeta Activa | Monto Compras / TC con Operaciones × 1.000.000 | Gasto promedio de las tarjetas que sí operan. Más refinado que Spend/Vigente. |

### 4.3 Cross-Sell & Product Mix

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| TC / TD Vigentes | TC Vigentes (Crédito) / TD Vigentes (Débito) × 100 | Penetración de crédito sobre base débito. >100% = más TC que TD. |
| TC con Ops / TD Vigentes | TC con Operaciones (Crédito) / TD Vigentes (Débito) × 100 | Proxy de cross-sell: cuántas tarjetas de crédito activas hay por cada tarjeta débito. |
| Monto TC / (TC+TD) | Monto Compras (Crédito) / (Monto Compras Crédito + Monto Transacciones Débito) × 100 | Qué % del gasto total va por crédito. Mayor = más "creditero". |
| Nro TC / (TC+TD) | Nro Compras (Crédito) / (Nro Compras Crédito + Nro Transacciones Débito) × 100 | Peso transaccional del crédito en el total. |

### 4.4 Cash Advance (Avances)

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Avances / Total TC | Monto Avances / (Monto Compras + Monto Avances) × 100 | Peso de los avances en el revenue mix. Alto = más riesgo crediticio. |
| Avance $ / Tarjeta Activa | Monto Avances / TC con Operaciones × 1.000.000 | Intensidad de avances por tarjeta que opera. |
| Ticket Avance | Monto Avances / Nro Avances × 1.000.000 | Valor promedio de cada avance en CLP. |
| Freq. relativa avances | Nro Avances / Nro Compras × 100 | Cuántos avances se hacen por cada 100 compras. |

### 4.5 Tarjetas Adicionales

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| % Adicionales | Tarjetas Vigentes (Adicional) / Tarjetas Vigentes (Total) × 100 | Penetración de venta de adicionales. Mayor = mejor cross-sell familiar. |

### 4.6 Débito

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Tasa Activación Débito | TD con Operaciones / TD Vigentes × 100 | % de tarjetas débito que registran operaciones. |
| Ticket Débito | Monto Transacciones (Débito) / Nro Transacciones (Débito) × 1.000.000 | Valor promedio de cada transacción débito. |
| Freq. Débito | Nro Transacciones (Débito) / TD con Operaciones (Débito) | Transacciones débito por tarjeta activa por mes. |
| Spend / TD Activa | Monto Transacciones (Débito) / TD con Operaciones × 1.000.000 | Gasto promedio de tarjetas débito activas. |

### 4.7 Cargos por Servicios (nuevas en v3)

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Cargo Srv / TC Activa | Monto Cargos Servicios / TC con Operaciones × 1.000.000 | Ingresos promedio por cargos automáticos (seguros, suscripciones) por tarjeta activa. |
| Ticket Cargos Srv | Monto Cargos Servicios / Nro Cargos Servicios × 1.000.000 | Valor promedio de cada cargo de servicio. |

### 4.8 Giros ATM — Débito (nuevas en v3)

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Giros / Total TD | Monto Giros / (Monto Transacciones + Monto Giros) × 100 | Peso de los retiros ATM en el revenue mix débito. Alto = base con más necesidad de efectivo. |
| Ticket Giro | Monto Giros / Nro Giros × 1.000.000 | Valor promedio de cada retiro ATM en CLP. |

### 4.9 Cross-Sell ampliado (nuevas en v3)

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| TC / TD con Operaciones | TC con Operaciones (Crédito) / TD con Operaciones (Débito) × 100 | Penetración crédito activo sobre débito activo. Más preciso que TC/TD Vigentes. |
| Monto TC / Monto TD | Monto Compras (Crédito) / Monto Transacciones (Débito) × 100 | Ratio del volumen de crédito respecto al volumen de débito. |

---

## 5. Snapshot de Datos — Diciembre 2025

### 5.1 KPIs Base — Tarjetas de Crédito (Total)

| Banco | TC Vigentes | TC c/ Ops | Monto Compras (MM$) | Nro Compras | Monto Avances (MM$) |
|-------|-------------|-----------|---------------------|-------------|---------------------|
| Banco de Chile | 1,832,845 | 957,527 | 794,030 | 15,584,661 | 76,098 |
| Santander | 1,676,293 | 937,200 | 1,034,340 | 17,933,513 | 15,486 |
| BCI | 795,272 | 446,207 | 358,721 | 6,375,958 | 20,598 |
| BancoEstado | 808,404 | 435,116 | 107,661 | 2,610,688 | 34,981 |
| Itaú | 428,774 | 263,715 | 273,351 | 4,597,495 | 18,783 |
| Scotiabank | 366,280 | 216,246 | 209,517 | 3,668,255 | 31,386 |

### 5.2 Métricas Derivadas — Crédito

| Métrica | BdCh | Santander | BCI | BancoEstado | Itaú | Scotiabank |
|---------|------|-----------|-----|-------------|------|------------|
| Tasa Activación | 52.2% | 55.9% | 56.1% | 53.8% | **61.5%** | 59.0% |
| Frecuencia | 16.3 | **19.1** | 14.3 | 6.0 | 17.4 | 17.0 |
| Ticket Promedio | $50,949 | $57,676 | $56,262 | $41,239 | **$59,457** | $57,116 |
| Spend / Activa | $829,251 | **$1,103,649** | $803,934 | $247,431 | $1,036,541 | $968,883 |
| TC / TD | 45.1% | 70.7% | 26.4% | 5.6% | **108.2%** | 68.7% |
| Monto TC / Total | 46.4% | 53.7% | 36.3% | 3.3% | **61.0%** | 41.4% |
| Avances / Total TC | 8.7% | 1.5% | 5.4% | **24.5%** | 6.4% | 13.0% |
| Ticket Avance | $509,958 | $281,190 | $439,874 | $192,328 | $690,983 | **$1,317,135** |
| % Adicionales (crédito) | 13.5% | 16.8% | 12.3% | 1.6% | **17.5%** | 13.3% |
| Ticket Débito | $17,993 | $20,549 | $19,177 | $13,743 | **$23,337** | $20,426 |
| Freq. Débito | 12.6 | 18.3 | 10.9 | 15.7 | 18.9 | **27.3** |

### 5.3 YoY (Dic 2024 → Dic 2025) — Crédito

| KPI | BdCh | Santander | BCI | BancoEstado | Itaú | Scotiabank |
|-----|------|-----------|-----|-------------|------|------------|
| Tarjetas Vigentes | +2.7% | +2.5% | **+9.6%** | -1.4% | -4.2% | +8.3% |
| Monto Compras | +6.5% | +4.4% | **+13.4%** | +5.2% | +10.0% | -4.7% |
| Nro Compras | +8.0% | +7.7% | **+17.2%** | +9.5% | +5.9% | -2.5% |

### 5.4 Tarjetas Adicionales

| Banco | Crédito % | Débito % |
|-------|-----------|----------|
| Itaú | **17.5%** | 2.7% |
| Santander | 16.8% | 1.3% |
| Banco de Chile | 13.5% | 1.1% |
| Scotiabank | 13.3% | **15.3%** |
| BCI | 12.3% | 2.6% |
| BancoEstado | 1.6% | 0.3% |

### 5.5 Débito — Rankings

| Banco | TD Vigentes | Nro Transacciones | Monto Txn (MM$) |
|-------|-------------|-------------------|-----------------|
| BancoEstado | 14,390,507 | 226,120,389 | 3,107,674 |
| Banco de Chile | 4,062,682 | 51,010,309 | 917,803 |
| BCI | 3,010,526 | 32,760,930 | 628,255 |
| Santander | 2,369,582 | 43,455,352 | 892,943 |
| Scotiabank | 532,779 | 14,533,730 | 296,871 |
| Itaú | 396,402 | 7,490,220 | 174,802 |

---

## 6. Hallazgos Estratégicos Clave

### 6.1 Fortalezas de Banco de Chile
- **#1 en tarjetas de crédito vigentes** (1.83M) con 31% de market share entre bancos del dashboard
- **#1 en tarjetas con operación** (957K), superando a Santander (937K)
- **Crecimiento sólido:** +8% en nro compras, +6.5% en monto YoY
- **Market share en tendencia alcista:** pasó de ~10% (2020) a 13.2% (2025Q4) en tarjetas vigentes del sistema total
- En monto compras subió de ~16% a ~17% en el mismo período
- **#2 en débito** con 4M tarjetas (detrás de BancoEstado que domina con 14.4M)

### 6.2 Debilidades / Oportunidades
- **Tasa de activación más baja (52.2%)** entre los 6 bancos. Itaú lidera con 61.5%. Cerrar ese gap (+9pp) representaría ~170K tarjetas adicionales operando.
- **Ticket promedio más bajo entre privados ($50,949)**. Santander e Itaú superan $57K. Señal de base más masiva vs premium.
- **Spend/tarjeta activa ($829K) está 33% bajo Santander ($1.1M)**. Oportunidad de upsell significativa.
- **Penetración TC/TD de 45%** vs 108% de Itaú. Enorme base de 4M tarjetas débito donde solo 1.8M tienen crédito. Cada punto de mejora son ~40K tarjetas.
- **Gasto 46% crédito** — casi la mitad del gasto va por débito. Mover hacia crédito mejoraría interchange fees.
- **Adicionales en 13.5%** vs 17.5% de Itaú. Cada punto son ~18K tarjetas adicionales nuevas.

### 6.3 Perfiles Competitivos

**Santander:** Principal competidor directo. #1 en monto compras ($1.03B vs $794M de BdCh). Ticket alto ($57K), alta frecuencia (19.1), pero solo recientemente mejoró su activación (de 37% en 2020 a 56% en 2025). Mínima exposición a avances (1.5%).

**Itaú:** Benchmark de eficiencia. Menor escala (429K TC) pero la mejor activación (61.5%), mayor ticket ($59K), mayor penetración TC/TD (108%), y mayor % de adicionales (17.5%). Es un banco "premium creditero" — 61% del gasto va por crédito.

**BCI:** Competidor en crecimiento acelerado. Creció +9.6% en tarjetas y +17.2% en compras YoY — el más rápido del mercado. Base de 795K TC.

**BancoEstado:** No es competidor en crédito (base masiva pero poco transaccional). Domina débito con 14.4M tarjetas. 24.5% del monto en avances — señal de base con necesidad de liquidez.

**Scotiabank:** Outlier en avances (ticket de $1.3M — probablemente corporativo) y en adicionales débito (15.3%). Base pequeña (366K TC) pero bien activada (59%).

---

## 7. Datos Embebidos en el Dashboard

El dashboard contiene los datos embebidos directamente en el HTML como variables JavaScript. No hay API ni base de datos — todo es estático.

### 7.1 Arquitectura v3: Objeto `_D` (reemplaza variables S, MS, STRAT, ADIC, YOY, DT)

En la versión v3 se migró de 6 variables estáticas independientes a un **único objeto compacto `_D`** con estructura indexada para optimizar tamaño y flexibilidad.

> ⚠️ **Las variables `S`, `MS`, `STRAT`, `ADIC`, `YOY` y `DT` ya no existen en el HTML.** Están reemplazadas por `_D`.

**Estructura de `_D`:**

| Clave | Contenido | Registros aprox. |
|-------|-----------|-----------------|
| `M` | Array de meses disponibles (strings "YYYY-MM"), orden ascendente | 24 |
| `B` | Array de nombres de bancos (6, orden fijo) | 6 |
| `K` | Array de nombres de KPIs ordenados | 12 |
| `S` | Snapshot mensual: arrays `[month_idx, bank_idx, prod, ta, kpi_idx, valor]` | ~2,880 |
| `MSM` | Market share mensual: arrays `[mes, bank_idx, share%, valor_abs]` por 8 series | ~1,152 |
| `DT` | Derived trends trimestrales crédito: `[quarter, bank_idx, activación, ticket, spend, freq, cs_ticket]` | ~144 |
| `DTD` | Derived trends trimestrales débito: `[quarter, bank_idx, activación, ticket, spend, freq, giro_pct, giro_ticket]` | ~144 |
| `CS` | Cross-sell trends trimestrales: `[quarter, bank_idx, tc_td_v, tc_td_ops, monto_ratio, share_monto, share_nro]` | ~144 |
| `AVM` | Avances/giros mensuales: `[mes, bank_idx, avance_pct, avance_ticket, giro_pct, giro_ticket]` | ~144 |
| `ADM` | Adicionales mensuales: `[mes, bank_idx, prod_code, pct_adicional]` | ~288 |

### 7.2 Función de acceso `gv()`

La función de acceso a datos fue actualizada: `gv(month, bank, kpi, prod, ta)` donde `month` es un string "YYYY-MM", `bank` es el nombre completo del banco, y busca dentro del array indexado `_D.S`. (Antes recibía parámetros de snapshot estático sin mes.)

### 7.3 Período de datos

El dashboard incluye **24 meses completos** de data mensual. Las series de market share y tendencias son ahora **mensuales** (antes trimestrales). Las derived trends (`DT`, `DTD`, `CS`) siguen siendo trimestrales desde 2020Q1.

### 7.4 Tamaño del archivo

El dashboard pasó de ~33KB a **~209KB** debido a la data mensual expandida (24 meses × 6 bancos × 12 KPIs × 3 tipos TA).

---

### 7.5 Referencia histórica: variables anteriores (v1/v2, DEPRECADAS)

> Las siguientes variables ya no existen. Se documentan solo como referencia de compatibilidad.

**`S` (snapshot):** Array de `{b, p, t, k, v}` — KPIs base del mes de referencia.
**`MS` (market share series):** Objeto `{cards:[...], spend:[...]}` con `{d, b, s}` — series trimestrales.
**`STRAT` (métricas estratégicas):** Array de 6 objetos con métricas derivadas precalculadas.
**`ADIC` (adicionales):** Array con `{b, p, x, a, r}` — datos de adicionales por banco y producto.
**`YOY` (crecimiento interanual):** Array con variación % Dic 2024 → Dic 2025.
**`DT` (derived trends):** Series trimestrales de activación, ticket y spend para BdCh, Santander e Itaú.

---

## 8. Infraestructura de Despliegue

### 8.1 Resumen de Infraestructura

| Componente | Detalle |
|------------|---------|
| **Dominio** | `benchmarkcmf.cl` (registrado en NIC Chile) |
| **DNS / CDN** | Cloudflare — nameservers: `lily.ns.cloudflare.com`, `owen.ns.cloudflare.com` |
| **Hosting** | Cloudflare Pages (plan Free) |
| **Auth** | Cloudflare Zero Trust Access (plan Free, 50 seats) — protege solo `/dashboard/` |
| **Repo** | GitHub `csaenzf/benchmarkcmf` (público), branch `main` |
| **URL raíz** | `https://benchmarkcmf.cl` → landing pública |
| **URL dashboard** | `https://benchmarkcmf.cl/dashboard/` → protegido por Access |
| **URL alternativa** | `https://benchmarkcmf.pages.dev` |
| **Zero Trust team** | `benchmarkcmf.cloudflareaccess.com` |
| **Archivos locales** | `C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Benchmark_Website` |

### 8.2 Estructura del Repositorio

```
csaenzf/benchmarkcmf (branch: main)
├── index.html                  ← Landing page pública
├── Video_Portada_01.mp4        ← Video de fondo de la landing (~2.2MB, H264, 1280×720, 8s loop)
└── dashboard/
    └── index.html              ← Dashboard React/Chart.js (protegido por Cloudflare Access)
```

### 8.3 Arquitectura de Acceso

```
benchmarkcmf.cl/              → Cloudflare Pages sirve index.html (público, sin auth)
benchmarkcmf.cl/dashboard/    → Cloudflare Access intercepta → OTP → dashboard/index.html
```

### 8.4 Pasos de Despliegue Inicial

**Paso 1 — Cloudflare: Agregar dominio**
- Agregar `benchmarkcmf.cl` en Cloudflare Dashboard → plan Free
- Cloudflare asigna nameservers: `lily.ns.cloudflare.com` / `owen.ns.cloudflare.com`

**Paso 2 — NIC Chile: Cambio de nameservers**
- Acceder a `clientes.nic.cl` → dominio `benchmarkcmf.cl` → Configuración Técnica
- Reemplazar nameservers por los de Cloudflare
- Esperar propagación → dominio queda **Active** en Cloudflare

**Paso 3 — GitHub: Crear repositorio**
```powershell
cd "C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Benchmark_Website"
git init
git add .
git commit -m "Dashboard CMF v1"
gh repo create benchmarkcmf --public --source=. --remote=origin --push
```
- Repo creado en `csaenzf/benchmarkcmf`, branch `main`

**Paso 4 — Cloudflare Pages: Deploy**
- Compute → Pages → Import Git repository
- Seleccionar repo `csaenzf/benchmarkcmf`
- Configuración: Framework preset: None, Build command: vacío, Output dir: vacío
- Deploy exitoso → `benchmarkcmf.pages.dev` activo

**Paso 5 — Custom Domain**
- Pages → proyecto `benchmarkcmf` → Custom domains → agregar `benchmarkcmf.cl`
- Cloudflare crea automáticamente registro `CNAME @ → benchmarkcmf.pages.dev`
- Click "Activate domain" → SSL activado automáticamente (Let's Encrypt)

**Paso 6 — Cloudflare Zero Trust Access**
- Settings → Zero Trust → plan Free ($0/mes, hasta 50 usuarios)
- Application creada: **Benchmark CMF**
  - Type: Self-hosted
  - Domain: `benchmarkcmf.cl/dashboard`  ← protege solo /dashboard/, no la raíz
  - Session duration: 24 horas
- Policy creada: **Usuarios Autorizados**
  - Action: Allow
  - Selector: Emails
  - Emails autorizados: `cristobal.saenzf@gmail.com`, `mkt@chilelentes.cl`, `adm@chilelentes.cl`
- Policy asignada a la aplicación

### 8.5 Flujo de Autenticación

1. Usuario visita `https://benchmarkcmf.cl` → ve la landing page (sin auth)
2. Hace clic en **"Ingresar al Dashboard"** → navega a `https://benchmarkcmf.cl/dashboard/`
3. Cloudflare Access intercepta → muestra pantalla de login
4. Usuario ingresa su email
5. Si email está en la lista → recibe código OTP de 6 dígitos por email
6. Ingresa código → accede al dashboard
7. Sesión válida por 24 horas
8. Email no autorizado → acceso denegado

> **Nota importante:** El botón de la landing apunta directamente a `https://benchmarkcmf.cl/dashboard/`. No usar la URL manual `/cdn-cgi/access/login?...` — Cloudflare Access intercepta automáticamente al detectar que la ruta está protegida y no hay sesión activa.

> **Nota:** La personalización visual del login de Cloudflare (logo, colores) requiere plan pagado (~$7/seat/mes) y fue omitida intencionalmente.

### 8.6 Dependencias CDN del Dashboard (cargadas en runtime)
- React 18.2.0: `cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js`
- ReactDOM 18.2.0: `cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js`
- Chart.js 4.4.1: `cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`
- Babel Standalone 7.23.9: `cdn.jsdelivr.net/npm/@babel/standalone@7.23.9/babel.min.js`
- Google Fonts: DM Sans + JetBrains Mono

**IMPORTANTE: Recharts NO funciona desde CDN.** No tiene UMD build en versiones 2.x. Se usa Chart.js en su lugar. Los artifacts .jsx de Claude.ai SÍ pueden usar Recharts porque el entorno lo provee nativamente.

### 8.7 Acceso / Seguridad
- Cloudflare Access (Zero Trust, plan Free hasta 50 usuarios)
- Lista de emails autorizados (o dominio completo, ej: @bancochile.cl)
- Login por OTP (código de 6 dígitos enviado al email)
- Sesión configurable (default 24 horas)
- Landing pública sin autenticación — solo el dashboard está protegido

Para agregar un usuario: Cloudflare Dashboard → Zero Trust → Access → Applications → Benchmark CMF → Edit Policy → agregar email.

### 8.8 Costo
- Cloudflare (Pages + Access + DNS): $0/mes
- Dominio .cl: ~$12,000 CLP/año
- Total: ~$12,000 CLP/año (~USD 12/año)

---

## 9. Pipeline de Actualización

### 9.1 Workflow de Actualización (v3 — con `generar_dashboard.py`)

En v3 el pipeline se simplificó: los pasos 3 y 4 del workflow anterior (extracción a JSON + regeneración manual del HTML) fueron reemplazados por un **único script autónomo `generar_dashboard.py`**.

```powershell
# 1. Consolidar datos CMF
cd "C:\Dropbox\CMF_API\CMF_Reportes_Excel"
python cmf_tarjetas_consolidar_3.py

# 2. Generar dashboard (lee xlsx, calcula métricas, genera HTML completo)
cd "C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Benchmark_Website"
python generar_dashboard.py

# 3. Deploy
git add dashboard/index.html
git commit -m "Datos [Mes] [Año]"
git push
# Cloudflare Pages redespliegue automático en ~1 minuto
```

> **Nota:** `cmf_tarjetas_consolidar_3.py` copia automáticamente el xlsx a `CMF_Benchmark_Website/`, por lo que `generar_dashboard.py` lo encuentra sin path relativo.

### 9.2 Script `generar_dashboard.py` — Detalle

Script Python autónomo (~67KB) que:
- Lee `CMF_Tarjetas_Consolidado.xlsx`
- Lee `Banco_de_Chile_Logotipo.svg` (opcional, tiene fallback texto)
- Extrae los 24 meses más recientes de data
- Calcula todas las métricas derivadas: market share mensual, trends trimestrales, cross-sell, avances/giros, adicionales
- Genera `dashboard/index.html` completo con datos embebidos (código del app embebido como base64 en el script)
- No depende de archivos intermedios

**Parámetros opcionales:**
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--consolidado PATH` | `CMF_Tarjetas_Consolidado.xlsx` | Ruta al archivo fuente |
| `--logo PATH` | `Banco_de_Chile_Logotipo.svg` | Ruta al SVG del logo |
| `--output PATH` | `dashboard/index.html` | Archivo de salida |
| `--meses N` | `24` | Número de meses a incluir |

### 9.3 Workflow anterior (v1/v2 — DEPRECADO)

> Ya no aplica. Se documenta como referencia.
> 1. Descargar reportes CMF
> 2. Correr `cmf_tarjetas_consolidar_3.py` → `CMF_Tarjetas_Consolidado.xlsx`
> 3. ~~Correr script de extracción → `full_dashboard_data.json`~~
> 4. ~~Regenerar HTML manualmente con datos embebidos~~
> 5. `git push`

### 9.4 Notas del Repositorio

- **Branch activo:** `main`
- **Remote:** `https://github.com/csaenzf/benchmarkcmf.git`
- **Carpetas de sesión limpiadas:** `20260329/`, `20260330_1003/`, `20260330_1027/`, `20260330_1107/` — fueron subidas por error y eliminadas con `git rm -r`

---

## 10. Landing Page — Detalle Técnico

### 10.1 Diseño

La landing page (`index.html`) es una página de portada pública con las siguientes características:

- **Video de fondo en loop:** `Video_Portada_01.mp4` (H264, 1280×720, 8 segundos, ~2.2MB). El video carga con `autoplay muted loop playsinline` y aparece con fade-in suave al estar listo (`canplay` event).
- **Overlay multicapa:** degradado vertical navy + degradado horizontal sutil para legibilidad en cualquier fotograma del video.
- **Grain sutil:** textura noise SVG con opacidad 2.8% para profundidad.
- **Paleta:** navy oscuro (`#080F1E`), azul acento (`#1A6FD4`), dorado (`#E8B84B`), blanco.
- **Tipografía:** Playfair Display (titular serif itálico), DM Sans (body y UI), DM Mono (logo y stats).
- **Animaciones:** fade-up escalonado en los 5 bloques del hero (delays de 0.1s a 0.58s).
- **Aviso confidencial:** footer con ícono de escudo — "Información confidencial · No autorizada para su distribución o reproducción".

### 10.2 Estructura HTML

```
header          → Logo mark SVG + "BenchmarkCMF" + badge "Acceso Restringido"
hero            → eyebrow · h1 · subtítulo · pills de features · botón CTA
stats-bar       → 5 stats: 6 bancos · 23 KPIs · Dic '25 · 2020– · CMF
footer          → aviso confidencial + badge Cloudflare Access
```

### 10.3 Botón CTA — URL Correcta

```html
<a href="https://benchmarkcmf.cl/dashboard/">Ingresar al Dashboard</a>
```

Cloudflare Access intercepta automáticamente al visitar `/dashboard/` sin sesión activa. **No usar** la URL `/cdn-cgi/access/login?redirect_url=...` — genera error 404 cuando la landing es pública.

### 10.4 Archivos de la Landing

| Archivo | Ubicación en repo | Descripción |
|---------|-------------------|-------------|
| `index.html` | raíz | Landing page pública |
| `Video_Portada_01.mp4` | raíz | Video de fondo (H264, 1280×720, 8s, ~2.2MB) |

---

## 11. Notas Técnicas para Desarrollo Futuro

### 11.1 Restricciones del Dashboard HTML Standalone
- **No usar Recharts** — no tiene UMD. Usar Chart.js.
- **No usar optional chaining (`?.`) ni nullish coalescing (`??`)** — Babel standalone con preset "react" no los transpila, y no todos los browsers corporativos los soportan.
- **No usar `import`/`export`** — todo es global via CDN UMD.
- **Google Fonts debe ir en `<head>`**, no dentro del JSX de React.
- **El `<script>` de Babel debe tener `type="text/babel" data-presets="react"`**.

### 11.2 Restricciones de la Landing HTML
- El video debe estar en la **raíz del repo** junto al `index.html` para que Cloudflare Pages lo sirva correctamente con la referencia relativa `src="Video_Portada_01.mp4"`.
- Si se cambia el video, reemplazar el archivo en el repo manteniendo el mismo nombre, o actualizar la referencia en el HTML.
- La landing no usa frameworks ni JS externo — es HTML/CSS puro con un script mínimo para el fade-in del video.

### 11.3 Posibles Extensiones del Dashboard
- Agregar datos de morosidad cuando estén disponibles para bancarias
- Agregar corte por marca (Visa/Mastercard) — la data existe en Apertura="Emisor y Marca" pero no para todos los períodos
- Agregar datos de no bancarias (CMR Falabella, Cencosud, etc.) como competencia extendida
- Conectar con CMF API (key: 9c85ee02885eed933641d8c5389fe410fe6024c6) para automatizar la descarga
- Agregar índice de utilización (disponible como Agregado para Total Sistema)
- Implementar con un framework build (Vite/Next.js) si se necesita más complejidad

### 11.4 Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `index.html` | Landing page pública (raíz del repo) |
| `Video_Portada_01.mp4` | Video de fondo de la landing (raíz del repo) |
| `dashboard/index.html` | Dashboard React/Chart.js protegido (~209KB) |
| `CMF_Tarjetas_Consolidado.xlsx` | Data fuente consolidada (106K+ filas) |
| `Banco_de_Chile_Logotipo.svg` | Logo SVG del banco (se embebe como base64 en el dashboard) |
| `generar_dashboard.py` | **NUEVO v3** — Script autónomo que genera `dashboard/index.html` completo |
| `cmf_tarjetas_consolidar_3.py` | Script de consolidación (en carpeta padre `CMF_Reportes_Excel`) |

**Archivos ya no necesarios (DEPRECADOS en v3):**
| Archivo | Razón |
|---------|-------|
| `full_dashboard_data.json` | Los datos ahora se generan y embeben directamente en el HTML |
| `BdCh_CMF_Dashboard_v3.jsx` | Reemplazado por el dashboard HTML standalone autogenerado |

### 11.5 Componentes React — Cambios v3

**Nuevos componentes:**

| Componente | Descripción |
|------------|-------------|
| `MonthSelect` | Dropdown selector de mes (24 meses, orden descendente) |
| `Legend` | Leyenda de bancos con toggle de visibilidad (click para activar/desactivar) |
| `CompTableGeneric` | Tabla comparativa genérica con rankings para todos los bancos y divisores |
| `TimeSeriesChart` | Gráfico stacked bar de 24 meses con tooltip de share |
| `YoYSeriesChart` | Gráfico de línea de variación interanual mes a mes |
| `RankBar` | Barra de ranking con share dentro de la barra, valores con decimal extra, YoY y MoM |

**Componentes eliminados:**

| Componente | Razón |
|------------|-------|
| `CompTable` | Reemplazado por `CompTableGeneric` que calcula métricas dinámicamente |

**Estados del componente Dashboard:**

| Estado | Default | Descripción |
|--------|---------|-------------|
| `tab` | "overview" | Pestaña activa |
| `month` | "2025-12" | Mes seleccionado (compartido entre pestañas) |
| `prod` | "C" | Producto: C=Crédito, D=Débito |
| `ta` | "X" | Tipo: X=Total, T=Titular, A=Adicional |
| `viewMode` | "bar" | Vista Resumen: "bar" o "series" |
| `ovKPI` | "Tarjetas Vigentes" | KPI seleccionado en Resumen |
| `msKPI` | "cards" | Métrica Market Share: cards/ops/spend/nops |
| `msProd` | "C" | Producto Market Share |
| `msVis` | [todos] | Array de bancos visibles en Market Share |
| `trendM` | "a" | Métrica Tendencias Estratégico: a/f/t/s/ct |
| `stratProd` | "C" | Producto Estratégico |
| `csTrendM` | "r" | Métrica Tendencias Cross-Sell: r/ro/rm/cm/cn |
| `avTrendM` | "ap" | Métrica Tendencias Avances: ap/at/gp/gt |
| `adicMode` | "table" | Vista Adicionales: "table" o "series" |

---



| Término | Definición |
|---------|-----------|
| CMF | Comisión para el Mercado Financiero — regulador financiero de Chile |
| TC | Tarjeta de crédito |
| TD | Tarjeta de débito |
| MM$ | Millones de pesos chilenos |
| KPI | Key Performance Indicator |
| Market share | Participación de mercado (% del total del sistema) |
| Activación | % de tarjetas vigentes que registran al menos una operación en el mes |
| Ticket promedio | Valor promedio por transacción |
| Spend per card | Gasto mensual promedio por tarjeta |
| Cross-sell | Venta cruzada — penetración de un producto (crédito) sobre la base de otro (débito) |
| Avance en efectivo | Retiro de dinero en efectivo usando tarjeta de crédito (genera interés y comisiones) |
| Giro ATM | Retiro de efectivo usando tarjeta de débito en cajero automático |
| Tarjeta adicional | Tarjeta emitida a nombre de un familiar o dependiente del titular principal |
| OTP | One-Time Password — código temporal de un solo uso para autenticación |
| UMD | Universal Module Definition — formato de empaquetado JavaScript compatible con browsers |
| CDN | Content Delivery Network — red de distribución de contenido |
| Interchange fee | Comisión que cobra el banco emisor al banco adquirente por cada transacción con tarjeta |
| Zero Trust | Modelo de seguridad que no asume confianza implícita — cada acceso se verifica individualmente |
| YoY | Year-on-Year — variación porcentual respecto al mismo mes del año anterior |
| MoM | Month-on-Month — variación porcentual respecto al mes inmediatamente anterior |
