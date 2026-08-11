

## 1. Gasoline Names Recorded in Different Forms

The following non-case-only names occur in the dataset:

| Raw item name | Invoice-item rows | Companies |
|---|---:|---:|
| `G93` | 78 | 16 |
| `Gasolina 93` | 52 | 10 |
| `93 S/P` | 73 | 5 |
| `Gasolina 93 octanos sin plomo` | 74 | 9 |
| `Aramco Gasolina 93` | 2 | 2 |

Example records include:

| Raw item name | Description | Company | Invoice folio | Recorded amount |
|---|---|---|---|---:|
| `G93` | `G93` | Patricio Santiago Carey Briones | `242147` | 63,575 |
| `Gasolina 93` | `Gasolina 93` | Patricio Santiago Carey Briones | `276017` | 70,626 |
| `93 S/P` | Empty | Estaciones de Servicio Paola Uslar Molina E.I.R.L. | `194828` | 31,841 |
| `Gasolina 93 octanos sin plomo` | `IE Base: 415.5900 - IE Variable: 17.4132` | Soc. Comerc. Edow Ltda. | `846539` | 73,274 |

## 2. Dinner Names With Different Specificity

Three records contain `Cena` as the complete name or as part of the name:

| Raw item name | Description | Company | Invoice folio | Date | Recorded amount |
|---|---|---|---|---|---:|
| `Cena` | Empty | Maria Jose Garcia de Ceca Latuz | `1527` | 2025-11-19 | 280,546 |
| `CENA 41 PERSONAS N.OP.080` | Empty | Victor Vera Viveros | `2866` | 2025-07-02 | 1,395,613 |


## 3. Placeholder Name With Laptop Details in Description

Three PC Factory invoices contain the literal item name `...`. Each invoice-item row has a different product description:

| Raw item name | Description | Invoice folio | Date | Recorded amount |
|---|---|---|---|---:|
| `...` | `All in One Lenovo Intel Pentium 8505 23,8" 8GB 256GB SSD Windows 11 Blanco 24IAP7` | `5419087` | 2025-07-30 | 389,824 |
| `...` | `Notebook HP 15-fd0259la Intel Core i5-1334U 15.6" 16GB 512GB SSD Windows 11 Home Gris B9TX7LA#AKH` | `5451189` | 2025-09-04 | 521,000 |
| `...` | `All in One V440 Intel Core i5-13420H 23.8" FHD 16GB 512GB SSD Windows 11 Home Blanco V440VAK-WPC185W` | `5503282` | 2025-12-16 | 611,336 |


## 4. `DETALLE` Name With Gasoline Information in Description

COPEC has 50 invoice-item rows with the raw item name `DETALLE`. The product and quantity are recorded in the description.

Example:

| Description | Recorded amount |
|---|---:|
| `GASOLINA NU 1203\| 94.146\|L` | 70,108 |
| `GASOLINA NU 1203\| 63.687\|L` | 47,944 |
| `GASOLINA NU 1203\| 49.666\|L` | 37,726 |

## 5. Generic `SERVICIO` and `SERVICIOS` Names

The dataset contains 20 rows whose complete raw name is a capitalization variant of `SERVICIO` or `SERVICIOS`. Their descriptions contain different types of work:

| Raw item name | Description | Company | Invoice folio | Recorded amount |
|---|---|---|---|---:|
| `Servicios` | `De Web Hosting, 4gb De Espacio Total, Cuentas De Correos Ilimitadas, Transferencia Ilimitada periodo 06-08-2024 al 06-08-2026` | Netsky SpA | `3367` | 205,580 |
| `SERVICIOS` | `FLETE MAICILLO` | Geo Partner SpA | `1857` | 960,000 |
| `SERVICIOS` | `CONFECCION CAMINO NUEVO` | Geo Partner SpA | `1857` | 11,748,000 |
| `SERVICIOS` | `RETIRO DE PURINES` | Geo Partner SpA | `2108` | 1,775,000 |
| `SERVICIO` | `MANTENCION GRUPO ELECTROGENO` | Bethel Electromecanica SpA | `663` | 685,000 |
| `servicio` | `mantencion de riego irripod mas materiales` | HYK Mantenimiento Makinaría Agrícola SpA | `52` | 797,500 |
| `servicio` | `mantencion de bba de purines mas materiales` | HYK Mantenimiento Makinaría Agrícola SpA | `62` | 885,780 |

## 6. Item Names Differing by Size

The following boot names differ by the size written at the end of the item name:

| Raw item name | Rows | Example recorded amount |
|---|---:|---:|
| `BOTAS BEKINA STEPLITE-X P.A.#38` | 2 | 53,790 |
| `BOTAS BEKINA STEPLITE-X P.A.#42` | 2 | 50,832 |
| `BOTAS BEKINA STEPLITE-X P.A.#43` | 1 | 50,832 |
| `BOTAS BEKINA STEPLITE-X P.A.#44` | 1 | 53,790 |

The following workwear names differ by clothing size:

| Raw item name | Rows | Recorded amount |
|---|---:|---:|
| `BUZO CANVAS AZUL 240 GRS X M2 TALLA M` | 1 | 8,775 |
| `BUZO CANVAS AZUL 240 GRS X M2 TALLA XL` | 1 | 8,775 |
| `BUZO CANVAS AZUL 240 GRS X M2 TALLA XXL` | 1 | 8,775 |

## 7. Transaction-Specific Values Inside Item Names

Electricity rows include the measured quantity inside the raw item name:

| Raw item name | Recorded amount |
|---|---:|
| `Electricidad consumida ( 6 kWh)` | 1,130 |
| `Electricidad consumida ( 19 kWh)` | 3,578 |
| `Electricidad consumida ( 746 kWh)` | 147,960 |

Monthly monitoring rows include the period and contract number in the raw item name:

```text
MONITOREO MES DE 02/2025 CONTRATO 1731576
MONITOREO MES DE 03/2025 CONTRATO 1731576
MONITOREO MES DE 05/2025 CONTRATO 1731576
```

Rental-payment rows include an installment number and contract number:

```text
Renta de Arrendamiento Nº4 del contrato Nº34589-1
Renta de Arrendamiento Nº7 del contrato Nº34589-1
```

Both rental-payment examples have a recorded amount of 1,435,898.


## 8. One-Time Assets, Projects, and Custom Work

These exact raw names occur once in the dataset:

| Raw item name | Description | Company | Invoice folio | Recorded amount |
|---|---|---|---|---:|
| `Muro galpón` | Empty | Magdiel Amalec Montecinos San Martin | `47` | 980,000 |
| `MOTO NUEVA SIN USO` | Honda TRX 420 FM, year 2025, VIN `1HFTE40U8RJ001435` | Enrique Ricardo Schmidt Rojas | `9574` | 9,990,000 |
| `portones acceso` | `saldo 30% restante proyecto portones acceso yutreco y el maiten.` | Sociedad de Inversiones MVM SpA | `559` | 1,734,118 |
| `50% según la Cotización` | `Nº 1035 proyecto purines tubería de pvc 110 mm` | Industrial Riego SpA | `839` | 3,078,250 |

Additional exact-name, one-occurrence examples from the random sample include:

```text
Smart TV LED 50" UN50CU7090 UHD 4K 2024
PODOLOGÍA CLÍNICA BOVINA
Traslado de maquina
Limpieza silo 33 T
CUBOS DE ARENA
```