# Plumbing material vocabulary

Measured only from `backups/supabase_20260902T153305Z/`, taken
2026-09-02T15:33:05Z. The exported `invoice_items.jsonl` has 11,746 rows and
SHA-256 `4c43c93076f3116d81e6c2f707291c2af98ea67ba1d5e761e96a2ef2af276206`.
The working population is the 4,411 rows where `decision != 'auto_accept'` and
`final_categories_id IS NULL`.

This is the vocabulary checkpoint required before classification. It records
how candidate words were found and which actual invoice lines make each word
usable. A word is not sufficient by itself: the final proposal reads every
matched `item_text` and `description` row by row.

## Starting population: five hardware suppliers

The five suppliers were selected mechanically: the five highest review-row
counts whose invoice `seller_giro` or name says ferreteria/hardware or building
materials. Together they contribute 1,463 review lines worth CLP 27,400,346.

| supplier | review lines |
|---|---:|
| DORIS IVONNE CASTILLO KANTER | 800 |
| COMERCIAL CLIMENT SPA | 269 |
| SODIMAC S.A. | 232 |
| COMERCIAL HARCHA SPA | 127 |
| PUELCHE LOS RIOS SOCIEDAD POR ACCIONES | 35 |

The next supplier in that measured ranking is FERRETERIAS WEITZLER SOCIEDAD
ANONIMA with 18 review lines; it was not silently substituted into the stated
five-supplier starting set.

## Frequent-token working

Token counts below mean distinct review lines from the five suppliers whose
`item_text` contains that accent-folded token. CLP sums the full line amounts;
it is a discovery measure, not a plumbing total, because ambiguous tokens such
as `ABRAZADERA`, `MANGUERA`, `LLAVE`, and `AGUA` also occur in non-plumbing
products.

| token | lines | CLP | example that caused inspection |
|---|---:|---:|---|
| PVC | 67 | 499,838 | `TUBO PVC PRESION C/16 20 MM` |
| VALVULA | 67 | 2,176,713 | `Válvula de Bola PP 32mm HI Arangül` |
| CODO | 54 | 177,597 | `Codo Compresión 32mm Arangül` |
| ABRAZADERA | 49 | 253,507 | `ABRAZADERA MANGUERA 1 PULG 19MM A 38MM AB-12 -@` |
| TERMINAL | 43 | 127,743 | `PL-TERMINAL HE 1 2 PLANSA -@` |
| TEE | 42 | 391,801 | `Tee Compresión HI 63mm GS Pimtas` |
| MANGUERA | 38 | 651,047 | `MANGUERA JARDIN RAYADA ECONOMICA 1 2 -@` |
| BUSHING | 36 | 60,601 | `BUSHING PLAST.BCO.HI HE 1 X 3/4"` |
| LLAVE | 35 | 311,009 | `LLAVE ANGULAR C/FLEX. 1/2HI X 15/16HI 30CM HOFFENS` |
| UNION | 30 | 237,286 | `UNION STORZ SIMPLE COLA LARGA 2"` |
| PPR | 24 | 49,630 | `FU-TUBERIA FUSION 20MM O PPR -@` |
| COPLA | 24 | 81,711 | `COPLA GALVANIZADA 1,1/2"` |
| NIPLE | 22 | 41,108 | `NIPLE HEXAGONO GALVANIZADO 1"` |
| TEFLON | 22 | 67,079 | `CINTA TEFLON GENEBRE 50 MTS X 19 MM -@` |
| PLANSA | 21 | 68,070 | `PL-UNION DOBLE 1 PLANSA -@` |
| COMPRESION | 21 | 446,254 | `Tee Compresión HI 32mm Arangül` |
| SANITARIO | 21 | 143,414 | `Ñ-CODO SANITARIO GRIS 40MM -@` |
| TERMOFUSION | 21 | 70,603 | `ADAPTADOR SO HI P/TERMOFUSION 20 X 1/2` |
| AQUAPLUV | 18 | 171,796 | `AQ-TEE BAJADA AQUAPLUV TIGRE -@` |
| FLEXIBLE | 19 | 207,387 | `FLEXIBLE AGUA 1 2 X 1 2 HI-HI 40CM YTS F40HI-@` |
| HDPE | 15 | 266,268 | `HDPE-TEE COMPRESION 63MM -@` |
| TAPON | 14 | 100,585 | `TAPON GORRO PVC-H CEM. 110MM.` |
| ADAPTADOR | 14 | 115,279 | `ADAPTADOR SO HI P/TERMOFUSION 20 X 1/2` |
| ARRANQUE | 11 | 164,589 | `COLLAR ARRANQUE PVC P/PVC 40 X 3/4"` |
| ACOPLE | 11 | 219,205 | `CAMLOCK ACOPLE HEMBRA TIPO-B HE 2"` |
| CONECTOR | 11 | 35,130 | `CONECTOR RAPIDO 1/2 C/STOP REHAU (268133300)` |
| HELIFLEX | 11 | 543,933 | `HELIFLEX LIVIANA C/ANILLO 3" (75MM)` |

## Accepted vocabulary, with the lines that justify it

The accepted vocabulary is deliberately made of material families plus
context. The example after each entry is an exact line from the review queue.

- Sanitary/drainage PVC: `PVC-SANIT`, `PVC SANITARIO`, `SANITARIO GRIS`,
  `DESAGUE`, `SIFON`, `FOSA SEPTICA`, and clamps or `VEE` when paired with
  sanitary PVC. Evidence:
  `* MT.X TIRA PVC-SANITARIO GRIS 110MM CERTIFICADA CESM`,
  `Ñ-TEE REGISTRO 110 PVC-SANITARIO HOFFENS -@`, and
  `DESAGUE TINA/RECEPTACULO E70 X S1,1/4" 9052642 VINIL`, plus the physical
  product lines `FOSA SEPTICA 1250 LT.POLIETILENO HORIZONTAL "OFERTA"` and
  `Ñ-ABRAZADERA SANITARIA OMEGA 40MM -@`.
- PPR/thermofusion water pipe and fittings: `PPR`, `TERMOFUSION`, and the
  `FU-` product family. Evidence: `FU-TUBERIA FUSION 20MM O PPR -@`,
  `FU-CODO 20MM PPR -@`, and `TUBO TERMOFUSION PN 20 20MM X 6 MT`.
- Rainwater drainage: `AQUAPLUV`, and `TUBO BAJADA`/`CANALETA` only when the
  wording identifies the gutter system. Evidence: `AQ-GOMA SELLO AQUAPLUV
  TIGRE -@`, `AQ-TUBO BAJADA X 3 METROS -ACQ-TIGRE -@`, and
  `UNION CANALETA ARENA P25- VINILIT`.
- Pressure-water PVC: `PVC PRESION`, `PVC-H CEM`, and PVC cement/adhesive.
  Evidence: `TUBO PVC PRESION C/16 20 MM`, `TAPON GORRO PVC-H CEM. 110MM.`,
  and `ADHESIVO PVC VINILIT C/BROCHA TRADICIONAL 240 CC`.
- HDPE/polyethylene compression water fittings: `HDPE`, and `COMPRESION` when
  attached to a named pipe fitting. Evidence: `HDPE-TEE COMPRESION 63MM -@`,
  `Codo Compresión 32mm Arangül`, and `Válvula Compresión HE 32mm Arangül`.
- Threaded pipe fittings: `BUSHING`, `NIPLE`/`NIPPLE`, `COPLA`, `CODO`, `TEE`,
  `UNION`, `TERMINAL`, `ADAPTADOR`, `REDUCCION`, `TAPON`, `CURVA`, and `CRUZ`
  when the wording includes pipe-thread markers/material (`HI`, `HE`, `SO`,
  galvanised, plastic, PVC, PPR, PLANSA, compression). Evidence:
  `-BUSHING REDUCCION HE-HI 1 X 3 4 -@`, `GG-NIPPLE HE-HE GALV 2 1 2 -@`,
  `TEE GALVANIZADA 3/4"`, `PL-TERMINAL HE 1 2 PLANSA -@`, and the shorthand
  line `HI PLANZA 11/2`, whose PLANSA/HI family is established by the longer
  product lines in the same data.
- Water valves and taps: `VALVULA DE BOLA`, `VALVULA COMPACTA`,
  `LLAVE BOLA JARDIN`, `LLAVE ANGULAR`, water `LLAVE PASO`, `FLOTADOR`, and
  `VENTOSA`, except when the line explicitly names gas, a vehicle, a machine,
  or a milking-system component. Evidence: `VALVULA DE BOLA HI ITALI 1"`,
  `LLAVE BOLA JARDIN PN16 DE 3 4 X 1 GENEBRE -@`, and
  `Válvula Ventosa Triple 2" GTR`.
- Plumbing fixture connections: water/calefont `FLEXIBLE`, `SIFON`, `DESAGUE`,
  and named taps or sanitary fixtures. Evidence: `FLEXIBLE CALEFONT 1/2HI X
  1/2HI X 25CM 051033211 TAUM`, `SIFON LAVAPLATOS LOA HOFFENS S/CURVA -@`,
  `LLAVE LAVAMANOS 1001 AQUAKIT J1001 UNIDAD -@`, `MONOMANDO LAVATORIO
  AUSTIN (20AS5003400) PLUMBER`, and `LAVAPLATO 100X50 IZQ 0,5MM 190502502
  CONSTRUCTORA TAU`.
- Pipe seal/joining consumables: `TEFLON`, PVC adhesive/cement, and rubber
  seals only when their wording names the pipe system. Evidence: `TEFLON
  MAESTRO 3/4"`, `ADHESIVO VINILIT 240CC.SECADO LENTO`, and
  `AQ-GOMA SELLO AQUAPLUV TIGRE -@`.
- Tank/pipe take-offs and irrigation fittings that themselves name a plumbing
  material: `COLLAR ARRANQUE`, `COLLARIN POLIPROPILENO`, `SALIDA ESTANQUE`,
  water `ESTANQUE`, water `FILTRO`, and explicitly water/irrigation
  connectors. Evidence: `COLLAR ARRANQUE PVC P/PVC 63 X 1"`, the same-family
  line `Collarín Arranque 63 x 1" Arangül`, `SALIDA ESTANQUE CEM 63 X 2 -@`,
  `ESTANQUE AGUA ESTACION. 5000 L WENCO`, and `FILTRO AGUA PVC NEGRO 2 PULG.
  PRAKTUS -@`.
- Explicit water/garden hose: `MANGUERA` is accepted only when its own wording
  names garden/water or it names a connector in that exact garden-hose product
  family. Evidence: `MANGUERA JARDIN ALEMANA C/TELA 1/2"`, `MANGUERA JARDIN
  3 4 P COLOR VERDE 19MM 24MM ROHS -@`, and `TERMINAL CONECTOR RAPIDO 1/2-3/4
  GARDTECH -@`.

## Candidate words that are not automatic membership

- `MANGUERA`, `HELIFLEX`, `CAMLOCK`, `STORZ`, generic `ESPIGA`, and generic
  `ABRAZADERA` can belong to irrigation, a milking parlour, compressed air,
  gas, a vehicle, or a machine. They are unresolved unless the same wording
  names water/plumbing use.
- `LLAVE` also names hand tools and keys. Examples rejected by the broad token:
  `JGO 10 LLAVES ALLEN TRUPER -@`, `LLAVE STILLSON 14 TRUPER 15838 -@`, and
  `CANDADO ODIS 340 2 LLAVES`.
- `BOLA` also names tow balls. `BOLA ARRASTRE` is not a valve.
- `AGUA` also appears in paint (`ESMALTE AL AGUA ...`), so it is not a rule.
- `PRESION` appears in washers and gas regulators; it requires pipe/valve
  context.
- `PVC` appears outside plumbing, and a generic `TUBO` may be structural or
  electrical. The line must name the plumbing system/material.
- Generic `FILTRO`, `BOMBA`, `SELLO`, `GOMA`, `EMPAQUETADURA`, and `ANILLO`
  are not plumbing vocabulary without system context.
- Gas-specific hose, regulators, and valves are excluded from this proposal:
  the standing client convention places gas hoses in `EXP-16.2`, and the
  2026-09-02 answer discussed farm water and building water plumbing.
- A service, repair, installation, project, property, or other job description
  is not a material even if it mentions a pipe or valve. Those rows remain in
  review under the open construction/use question.

This vocabulary is a candidate generator, not the classifier. Every resulting
row must still be read in full before it enters either JSONL file.
