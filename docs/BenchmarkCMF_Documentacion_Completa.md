# BenchmarkCMF.cl — Documentación Completa del Dashboard de Inteligencia Competitiva

## 1. Resumen Ejecutivo

**benchmarkcmf.cl** es un dashboard interactivo de inteligencia competitiva para **Banco de Chile** construido con data pública de la CMF (Comisión para el Mercado Financiero de Chile). Permite al banco comparar su performance en tarjetas de crédito y débito contra los principales bancos del mercado chileno.

El dashboard fue desarrollado por Cristobal Sáenz (Visa Consulting & Analytics / VCA Chile) como herramienta de consultoría estratégica. Se despliega como un archivo HTML único autónomo (~33KB) en Cloudflare Pages con autenticación Cloudflare Access (lista de emails autorizados, login por OTP).

**Período de datos:** Diciembre 2025 (con series históricas trimestrales desde 2020).
**Última actualización:** Diciembre 2025.

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
| BCI | BCI | #FF6900 (naranja) |
| BancoEstado | BEst. | #00843D (verde) |
| Itaú | Itaú | #003DA5 (azul oscuro) |
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

## 3. Estructura del Dashboard

### 3.1 Stack Técnico
- **Frontend:** React 18.2.0 (UMD desde CDN jsdelivr)
- **Gráficos:** Chart.js 4.4.1 (UMD desde CDN jsdelivr) — reemplazó a Recharts que no tiene UMD funcional
- **JSX Transpilation:** Babel Standalone 7.23.9 (runtime en browser)
- **Fonts:** DM Sans (UI), JetBrains Mono (datos numéricos)
- **Deployment:** Cloudflare Pages + Cloudflare Access (Zero Trust)
- **Dominio:** benchmarkcmf.cl
- **Archivo:** un solo `index.html` autónomo (~33KB)

### 3.2 Pestañas del Dashboard

El dashboard tiene **6 pestañas** (tabs):

#### TAB 1: Resumen (Overview)
**Propósito:** Vista panorámica de la posición de Banco de Chile.

**Filtros interactivos:**
- Producto: Crédito / Débito
- Tipo: Total / Titular / Adicional

**Contenido:**
- Ranking de Tarjetas Vigentes (barra horizontal con valores) — se actualiza según filtros
- Ranking de Tarjetas con Operaciones — se actualiza según filtros
- Ranking de Monto Compras (solo Crédito Total) — MM$
- Ranking de Nro Compras (solo Crédito Total)
- Ranking de Monto Transacciones (solo Débito Total) — MM$
- Ranking de Nro Transacciones (solo Débito Total)
- Tabla YoY: crecimiento Dic 2024 → Dic 2025 para los 6 bancos en 3 KPIs (Tarjetas Vigentes, Monto Compras, Nro Compras)

#### TAB 2: Market Share
**Propósito:** Evolución temporal de la participación de mercado.

**Toggle:** Tarjetas Vigentes / Monto Compras

**Contenido:**
- Gráfico de líneas (Chart.js) con la evolución trimestral del % de market share de cada banco desde 2020Q3 hasta 2025Q4
- Leyenda con colores por banco
- BdCh se destaca con línea más gruesa (3px vs 1.5px)

**Datos de series temporales incluidos (trimestral):**
- Market share Tarjetas Vigentes: 7 trimestres × 6 bancos = 42 data points
- Market share Monto Compras: 7 trimestres × 6 bancos = 42 data points

#### TAB 3: Estratégico
**Propósito:** Benchmark de métricas derivadas de consultoría.

**Contenido:**
- Tabla comparativa: Tasa Activación, Frecuencia, Ticket Promedio, Spend/Activa — con valor para cada banco, badge de ranking para BdCh
- Gráfico de tendencias (Chart.js): 3 métricas seleccionables (Activación, Ticket, Spend/Activa) para BdCh vs Santander vs Itaú, trimestral 2020-2025
- Toggle: Activación / Ticket / Spend/Activa

#### TAB 4: Cross-Sell
**Propósito:** Analizar la venta cruzada crédito/débito.

**Contenido:**
- Tabla comparativa: TC/TD Vigentes, Monto TC/(TC+TD), Ticket Débito, Freq. Débito
- Diagnóstico estratégico con insights

#### TAB 5: Avances
**Propósito:** Revenue mix y exposición al riesgo por avances en efectivo.

**Contenido:**
- Tabla comparativa: Avances/Total TC, Ticket Avance, Ticket Compras (para comparar)
- Diagnóstico estratégico

#### TAB 6: Adicionales
**Propósito:** Penetración de tarjetas adicionales.

**Filtro:** Crédito / Débito

**Contenido:**
- Tabla con ranking: banco, barra visual, total, adicionales, % adicionales
- Diagnóstico estratégico

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
| Ticket Débito | Monto Transacciones (Débito) / Nro Transacciones (Débito) × 1.000.000 | Valor promedio de cada transacción débito. |
| Freq. Débito | Nro Transacciones (Débito) / TD Vigentes (Débito) | Transacciones débito por tarjeta por mes. |

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

### 7.1 Variable `S` — Snapshot (KPIs base)
Array de objetos con claves comprimidas:
- `b`: banco (Emisor_Comercial)
- `p`: producto ("C"=Crédito, "D"=Débito)
- `t`: tipo ("X"=Total, "T"=Titular, "A"=Adicional)
- `k`: nombre del KPI
- `v`: valor numérico

### 7.2 Variable `MS` — Market Share Series
Objeto con dos arrays (`cards` y `spend`), cada uno con:
- `d`: trimestre (ej: "2024Q2")
- `b`: banco
- `s`: share (%)

### 7.3 Variable `STRAT` — Métricas Estratégicas
Array de 6 objetos (uno por banco) con todas las métricas derivadas calculadas.

### 7.4 Variable `ADIC` — Tarjetas Adicionales
Array con datos de adicionales por banco y producto.

### 7.5 Variable `YOY` — Crecimiento Interanual
Array con variación % Dic 2024 → Dic 2025.

### 7.6 Variable `DT` — Derived Trends
Series trimestrales de métricas derivadas (activación, ticket, spend/activa) para BdCh, Santander e Itaú.

---

## 8. Infraestructura de Despliegue

### 8.1 Resumen de Infraestructura

| Componente | Detalle |
|------------|---------|
| **Dominio** | `benchmarkcmf.cl` (registrado en NIC Chile) |
| **DNS / CDN** | Cloudflare — nameservers: `lily.ns.cloudflare.com`, `owen.ns.cloudflare.com` |
| **Hosting** | Cloudflare Pages (plan Free) |
| **Auth** | Cloudflare Zero Trust Access (plan Free, 50 seats) |
| **Repo** | GitHub `csaenzf/benchmarkcmf` (público) |
| **URL producción** | `https://benchmarkcmf.cl` |
| **URL alternativa** | `https://benchmarkcmf.pages.dev` |
| **Zero Trust team** | `benchmarkcmf.cloudflareaccess.com` |
| **Archivos locales** | `C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Benchmark_Website` |
| **Archivo principal** | `index.html` (renombrado desde `benchmarkcmf_index.html`) |

### 8.2 Arquitectura
```
[Usuario] → benchmarkcmf.cl (DNS Cloudflare)
    ↓
[Cloudflare Access] ← Lista de emails autorizados (OTP por email)
    ↓ (autenticado)
[Cloudflare Pages] ← HTML estático único
    ↓
[CDN Global] ← SSL automático, cache
```

### 8.3 Pasos de Despliegue Inicial

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
Rename-Item "benchmarkcmf_index.html" "index.html"
git init
git add index.html
git commit -m "Dashboard CMF v1"
gh repo create benchmarkcmf --public --source=. --remote=origin --push
```
- Repo creado en `csaenzf/benchmarkcmf`, branch `main`
- Archivo `index.html` (~37KB) subido

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
  - Domain: `benchmarkcmf.cl`
  - Session duration: 24 horas
- Policy creada: **Usuarios Autorizados**
  - Action: Allow
  - Selector: Emails
  - Emails autorizados: `cristobal.saenzf@gmail.com`, `mkt@chilelentes.cl`, `adm@chilelentes.cl`
- Policy asignada a la aplicación

### 8.4 Flujo de Autenticación

1. Usuario visita `https://benchmarkcmf.cl`
2. Cloudflare Access intercepta → muestra pantalla de login
3. Usuario ingresa su email
4. Si email está en la lista → recibe código OTP de 6 dígitos por email
5. Ingresa código → accede al dashboard
6. Sesión válida por 24 horas
7. Email no autorizado → acceso denegado

> **Nota:** La personalización visual del login (logo, colores) requiere plan pagado (~$7/seat/mes) y fue omitida intencionalmente.

### 8.5 Dependencias CDN (cargadas en runtime)
- React 18.2.0: `cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js`
- ReactDOM 18.2.0: `cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js`
- Chart.js 4.4.1: `cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`
- Babel Standalone 7.23.9: `cdn.jsdelivr.net/npm/@babel/standalone@7.23.9/babel.min.js`
- Google Fonts: DM Sans + JetBrains Mono

**IMPORTANTE: Recharts NO funciona desde CDN.** No tiene UMD build en versiones 2.x. Se usa Chart.js en su lugar. Los artifacts .jsx de Claude.ai SÍ pueden usar Recharts porque el entorno lo provee nativamente.

### 8.6 Acceso / Seguridad
- Cloudflare Access (Zero Trust, plan Free hasta 50 usuarios)
- Lista de emails autorizados (o dominio completo, ej: @bancochile.cl)
- Login por OTP (código de 6 dígitos enviado al email)
- Sesión configurable (default 24 horas)

Para agregar un usuario: Cloudflare Dashboard → Zero Trust → Access → Applications → Benchmark CMF → Edit Policy → agregar email.

### 8.7 Costo
- Cloudflare (Pages + Access + DNS): $0/mes
- Dominio .cl: ~$12,000 CLP/año
- Total: ~$12,000 CLP/año (~USD 12/año)

---

## 9. Pipeline de Actualización

### 9.1 Workflow de Actualización de Datos (ej: nuevo mes)

1. Descargar los nuevos reportes de la CMF
2. Correr `cmf_tarjetas_consolidar_3.py` para regenerar `CMF_Tarjetas_Consolidado.xlsx`
3. Correr el script de extracción de datos (genera `full_dashboard_data.json`)
4. Regenerar `index.html` con los nuevos datos embebidos
5. Publicar con git push:

```powershell
cd "C:\Dropbox\CMF_API\CMF_Reportes_Excel\CMF_Benchmark_Website"
git add index.html
git commit -m "Datos Enero 2026"
git push
# Cloudflare Pages redespliegue automático en ~1 minuto
```

Todo el pipeline es Python y no requiere servidor. Cloudflare Pages detecta el push a `main` y redespliega automáticamente.

### 9.2 Notas del Repositorio

- **Subcarpeta `20260330_1003/`** — existe en el repo con un `index.html` adicional subido por error. No afecta el deploy (Cloudflare Pages sirve el `index.html` raíz) pero puede limpiarse con:
  ```powershell
  git rm -r 20260330_1003/
  git commit -m "Limpiar carpeta subida por error"
  git push
  ```
- **Branch activo:** `main`
- **Remote:** `https://github.com/csaenzf/benchmarkcmf.git`

---

## 10. Notas Técnicas para Desarrollo Futuro

### 10.1 Restricciones del HTML Standalone
- **No usar Recharts** — no tiene UMD. Usar Chart.js.
- **No usar optional chaining (`?.`) ni nullish coalescing (`??`)** — Babel standalone con preset "react" no los transpila, y no todos los browsers corporativos los soportan.
- **No usar `import`/`export`** — todo es global via CDN UMD.
- **Google Fonts debe ir en `<head>`**, no dentro del JSX de React.
- **El `<script>` de Babel debe tener `type="text/babel" data-presets="react"`**.

### 10.2 Posibles Extensiones
- Agregar datos de morosidad cuando estén disponibles para bancarias
- Agregar corte por marca (Visa/Mastercard) — la data existe en Apertura="Emisor y Marca" pero no para todos los períodos
- Agregar datos de no bancarias (CMR Falabella, Cencosud, etc.) como competencia extendida
- Conectar con CMF API (key: 9c85ee02885eed933641d8c5389fe410fe6024c6) para automatizar la descarga
- Agregar índice de utilización (disponible como Agregado para Total Sistema)
- Implementar con un framework build (Vite/Next.js) si se necesita más complejidad

### 10.3 Archivos del Proyecto
- `CMF_Tarjetas_Consolidado.xlsx` — data fuente consolidada (106K filas)
- `cmf_tarjetas_consolidar.py` — script de consolidación de reportes CMF
- `full_dashboard_data.json` — datos procesados para el dashboard
- `index.html` — dashboard HTML standalone (deploy en `csaenzf/benchmarkcmf`, branch `main`)
- `BdCh_CMF_Dashboard_v3.jsx` — versión React/Recharts para artifact de Claude.ai (interactivo)
- `GUIA_DEPLOY_benchmarkcmf.md` — guía paso a paso de despliegue en Cloudflare

---

## 11. Glosario

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
| Tarjeta adicional | Tarjeta emitida a nombre de un familiar o dependiente del titular principal |
| OTP | One-Time Password — código temporal de un solo uso para autenticación |
| UMD | Universal Module Definition — formato de empaquetado JavaScript compatible con browsers |
| CDN | Content Delivery Network — red de distribución de contenido |
| Interchange fee | Comisión que cobra el banco emisor al banco adquirente por cada transacción con tarjeta |
