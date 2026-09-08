# Alias harvest — 2026-09-08

**Nothing here has been written.** These are proposals for review.

## What this is

Every wording below already sits on the catalog item named beside it, assigned by
the canonical migration (D-044, D-045) and verified against live. So this is not
an inference — it is a **fact already in the database**, written down in the one
place the resolver can look it up next time.

That distinction is the whole design. An alias is a *memorised observation*; a
pattern is a *derived rule*. You cannot tell from the string alone whether `5 kg`
in `cloro organico 5 kg` is specification or identity — and here we never have to,
because the assignment already exists. Deriving a "strip trailing weights" rule is
what would break `Gasolina 93`.

## Effect, measured over all 11,746 lines

| | resolved automatically | disagreeing with today |
|---|---|---|
| live aliases only (8 rows) | 9,255 (78.8%) | 7 |
| + these 222 | 10,125 (86.2%) | 7 |

870 lines gained, **zero new disagreements**. The 7 are the `Confeccion de Bolos`
duplicate, which these aliases neither cause nor fix.

## Needed before loading

`milk-company/supabase/006_alias_provenance.sql` — `item_aliases` has no `source`
column, so after a bulk load an alias you approved would be indistinguishable from
one the machine proposed.

## Proposed — 222 wordings, 870 lines

| lines | wording as it arrives | catalog item |
|---:|---|---|
| 28 | `TOALLA PAPEL INTERFOLIADA 320 UN` | Toalla Papel Interfoliada |
| 20 | `AGUJA DESECHABLE 16G X 1/2"` | Agujas desechables |
| 17 | `CLORO ORGANICO 5 KG` | Cloro Organico |
| 16 | `FEBRECTAL BOVINO X 50 CC` | Febrectal Bovino X |
| 15 | `CALFODEX 500 CC.` | Calfodex |
| 15 | `CAÑERIA NEGRA PN4 1"` | Caneria Negra Pn4 |
| 15 | `TORDON 101 X 4 LT` | Tordon 101 |
| 13 | `LIQUAMICINA LA 250 CC.` | Liquamicina la |
| 13 | `BAYTRIL MAX X 100 CC` | Baytril Max X |
| 12 | `Botellon 20 litros` | Botellon |
| 11 | `AGUJA DESECHABLE 18G X 1"` | Agujas desechables |
| 11 | `CLAVO DE 4 KG -@` | Clavos |
| 10 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 42` | Bota Bekina Steplite Punta Acero N |
| 10 | `Cargo mensual por D. Max de potencia suministrada ( 56,860 )` | Cargo mensual por demanda máxima suministrada |
| 10 | `TRI-PFAN 200 LTS` | Tri Pfan |
| 9 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 41` | Bota Bekina Steplite Punta Acero N |
| 9 | `JERINGA DESECHABLE 20 ML C/AGUJA (L.L.)` | Jeringas desechables |
| 9 | `FORMALINA X 20 LTS` | Formalina X |
| 9 | `CLAVOS TERRANO 1 1/2 !¡` | Clavos |
| 9 | `Cargo mensual por D. Max de potencia suministrada ( 37,230 )` | Cargo mensual por demanda máxima suministrada |
| 9 | `HDPE-COPLA COMPRESION 32MM -@` | HDPE Copla Compresion |
| 8 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 43` | Bota Bekina Steplite Punta Acero N |
| 8 | `-NIPLE HE-HE 3 4 -@` | Niple HE HE |
| 8 | `Cargo mensual por D. Max de potencia suministrada ( 67,240 )` | Cargo mensual por demanda máxima suministrada |
| 8 | `UNION HDPE 32MM` | Union HDPE |
| 8 | `HDPE-TERMINAL HI COMPRESION 32MM X 1-@` | HDPE Terminal HI Compresion X |
| 7 | `JERINGA DESECHABLE 3 ML C/AGUJA (L.L.)` | Jeringas desechables |
| 7 | `CLAVO DE 3 KG -@` | Clavos |
| 7 | `HDPE-TEE COMPRESION 32MM -@` | HDPE Tee Compresion |
| 7 | `BOTAS DUNLOP THERMO+ # 43 (-40 C)` | Botas Dunlop Thermo C |
| 6 | `HELIFLEX LIVIANA C/ANILLO 3" (75MM)` | Heliflex Liviana C Anillo |
| 6 | `-NIPLE HE-HE 1 -@` | Niple HE HE |
| 5 | `TVZC TORNILLO VOLCANITA ZINC 2 1 2 CJ 100UN -@` | Tornillos |
| 5 | `CLAVOS 4 X 8` | Clavos |
| 5 | `TVZC TORNILLO VOLCANITA ZINC 2 CJ 100UN -@` | Tornillos |
| 5 | `CLAVO DE TECHO X BOLSA -@` | Clavos |
| 5 | `-BUSHING REDUCCION HE-HI 1 X 3 4 -@` | Bushing Reduccion HE HI X |
| 5 | `TRI-PFAN 60 LTS.` | Tri Pfan |
| 5 | `HDPE-COPLA COMPRESION 50MM -@` | HDPE Copla Compresion |
| 5 | `TVZC TORNILLO VOLCANITA ZINC 1 5 8 CJ 100UN -@` | Tornillos |
| 5 | `T1 TUERCA HILO-CORRIENTE 3 8 -@` | T1 Tuerca Hilo Corriente |
| 5 | `T1 TUERCA HILO-CORRIENTE 1 2 -@` | T1 Tuerca Hilo Corriente |
| 4 | `AGUJA DESECHABLE 18G X 1 1/2"` | Agujas desechables |
| 4 | `TAUTO-FINA 2 TORNILLO AUTOPERF FINA CAJA 100 UN -@` | Tornillos |
| 4 | `Ñ-CODO SANITARIO GRIS 40MM -@` | N Codo Sanitario Gris |
| 4 | `JERINGA DESECHABLE 10 ML C/AGUJA (L.L.)` | Jeringas desechables |
| 4 | `AGUJA DESECHABLE (C/PLAST) 16 G x 1/2` | Agujas desechables |
| 4 | `FU-TUBERIA FUSION 20MM O PPR -@` | Fu Tuberia Fusion O PPR |
| 4 | `BUZO VETERINARIO 1 PIEZA TALLA 50` | Buzo Veterinario Pieza Talla |
| 4 | `BOTAS DUNLOP THERMO+ # 39-40 (-40 C)` | Botas Dunlop Thermo C |
| 4 | `BOTAS DUNLOP THERMO+ # 41 (-40 C)` | Botas Dunlop Thermo C |
| 4 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 37` | Bota Bekina Steplite Punta Acero N |
| 4 | `MOSKIMIC FORTE POUR ON 3 LITRO` | Moskimic Forte Pour On |
| 4 | `FU-CODO 20MM PPR -@` | Fu Codo PPR |
| 4 | `VALVULA DE BOLA HI ITALI 1"` | Valvula de Bola HI Itali |
| 4 | `UNION HDPE 50MM.` | Union HDPE |
| 4 | `HDPE-COPLA COMPRESION 25MM -@` | HDPE Copla Compresion |
| 4 | `Cargo mensual por demanda máxima leida de potencia en horas de punta ( 0,010 )` | Cargo mensual por demanda máxima en horas de punta |
| 4 | `Cargo mensual por demanda máxima leida de potencia en horas de punta ( 44,480 )` | Cargo mensual por demanda máxima en horas de punta |
| 4 | `Multa por consumo reactivo (Recargo por consumo reactivo) ( 0,840 )` | Recargo por consumo reactivo |
| 4 | `Cargo mensual por demanda máxima leida de potencia en horas de punta ( 51,010 )` | Cargo mensual por demanda máxima en horas de punta |
| 4 | `Cargo mensual por demanda máxima leida de potencia en horas de punta ( 0,020 )` | Cargo mensual por demanda máxima en horas de punta |
| 4 | `CLAVO VOLCANITA KG -@` | Clavos |
| 4 | `ABRAZADERA C/PERNO T-510 (62-67)` | Abrazadera C Perno T |
| 4 | `TEFLON MAESTRO 3/4"` | Teflon Maestro |
| 4 | `TEE HDPE 32MM` | Tee HDPE |
| 4 | `BOTIN NORSEG NS586 PRO CAFÉ 40` | Botin Norseg Ns586 Pro Cafe |
| 4 | `G1 GOLILLA PLANA 1 2 -@` | G1 Golilla Plana |
| 4 | `TORDON 101 4 L` | Tordon 101 |
| 4 | `AGUJA DESECHABLE (C/PLAST) 18 G x 1` | Agujas desechables |
| 4 | `HDPE-TERMINAL HI COMPRESION 25MM X 3/4 -@` | HDPE Terminal HI Compresion X |
| 4 | `TORN VOLC CRS ZBR 6X 1 5/8 200` | Torn Volc Crs Zbr 6x |
| 3 | `CAÑERIA NEGRA PN4 1 1/2"` | Caneria Negra Pn4 |
| 3 | `BOTIN NORSEG NS586 PRO CAFÉ 42` | Botin Norseg Ns586 Pro Cafe |
| 3 | `CLAVOS 4 X 8 X 1 KG` | Clavos |
| 3 | `CLAVO TINGLE KG -@` | Clavos |
| 3 | `CLAVO DE 6 KG -@` | Clavos |
| 3 | `FU-TERMINAL HE 1 2 X 20MM METALICO PEGAR PPR -@` | Fu Terminal HE X Metalico Pegar PPR |
| 3 | `CODO PVC-SANIT.GRIS 40MM X 90§` | Codo PVC Sanit Gris X |
| 3 | `CLAVO TECHO DOBLE SELLO 2,1/2" X 8 (BOLSA 100 U) MET` | Clavos |
| 3 | `HDPE-CODO 32MM - PN16 -@` | HDPE Codo Pn16 |
| 3 | `FU-TERMINAL HI 1 2 X 20MM METALICO PEGAR PPR -@` | Fu Terminal HI X Metalico Pegar PPR |
| 3 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 38` | Bota Bekina Steplite Punta Acero N |
| 3 | `BOTAS DUNLOP THERMO+ # 42 (-40 C)` | Botas Dunlop Thermo C |
| 3 | `VALVULA DE BOLA PVC-HILO S/UNION 32MM = 1"` | Valvula de Bola PVC Hilo S Union |
| 3 | `PL-TERMINAL HE 1 PLANSA -@` | Pl Terminal HE Plansa |
| 3 | `VALVULA COMPACTA HI 1 -@` | Valvula Compacta HI |
| 3 | `ACEITE 2T STIHL X 250 CC` | Aceite 2t Stihl X |
| 3 | `Cargo mensual por D. Max de potencia suministrada ( 72,380 )` | Cargo mensual por demanda máxima suministrada |
| 3 | `TUBO TERMOFUSION PN 20 20MM X 6 MT` | Tubo Termofusion PN X |
| 3 | `ABRAZADERA C/PERNO T-514 (84-90)` | Abrazadera C Perno T |
| 3 | `-BUSHING REDUCCION HE-HI 1 1 4 X 1 -@` | Bushing Reduccion HE HI X |
| 3 | `JERINGA DESECHABLE 60 ML PUNTA CATETER` | Jeringas desechables |
| 3 | `VALVULA DE BOLA HI ITALI 1,1/2"` | Valvula de Bola HI Itali |
| 3 | `M.C.P.A X 1 LT` | M C P a X |
| 3 | `Ñ-TIRA PVC SANITARIO GRIS 40 MM X 6MTS -@` | N Tira PVC Sanitario Gris X |
| 3 | `BOTA BEKINA STEPLITE PUNTA ACERO N° 45` | Bota Bekina Steplite Punta Acero N |
| 3 | `TEE PVC-SANIT.GRIS 110 X 40MM` | Tee PVC Sanit Gris X |
| 3 | `ABRAZADERA CREM. 1" (21-38)` | Abrazadera Crem |
| 3 | `FILTRO COMBUSTIBLE WK-8194` | Filtro Combustible Wk |
| 3 | `UNION HDPE 50 X 1,1/2HE` | Union HDPE X 2he |
| 3 | `CARGA GAS 15 KG` | Carga Gas |
| 3 | `AZUCAR IANSA 1KG` | Azucar Iansa |
| 3 | `HN HILO ESPARRAGO NEGRO -3 8 -@` | Hn Hilo Esparrago Negro |
| 3 | `LIJA FIERRO GRANO 100 -@` | Lija Fierro Grano |
| 3 | `TIRAFONDO 3 8 X 3 -@` | Tirafondos |
| 3 | `ABRAZADERA MANGUERA 1 PULG 19MM A 38MM AB-12 -@` | Abrazadera Manguera Pulg a Ab |
| 3 | `-CODO 20 MM CEM -@` | Codo Cem |
| 3 | `LIQUAMICINA LA FCO. 250 CC.` | Liquamicina la |
| 3 | `ABRAZADERA CREM. 2" (40-64)` | Abrazadera Crem |
| 3 | `BOTIN NORSEG NS586 PRO CAFÉ 41` | Botin Norseg Ns586 Pro Cafe |
| 3 | `HDPE-TEE COMPRESION 63MM -@` | HDPE Tee Compresion |
| 3 | `G1 GOLILLA PLANA 3 8 -@` | G1 Golilla Plana |
| 3 | `LIJA FIERRO GRANO 80 -@` | Lija Fierro Grano |
| 3 | `TYVECK ROLLO 75 M2 -@` | Tyveck |
| 3 | `CAÑERIA NEGRA PN4 3/4"` | Caneria Negra Pn4 |
| 3 | `CLAVO TERRANO 11/2 1,0KG.CUN06` | Clavos |
| 3 | `CALFODEX 500 CC. -____` | Calfodex |
| 3 | `MANGUERA ESPIRALADA AMARILLA 3 -@` | Manguera Espiralada Amarilla |
| 3 | `JERINGAS DESECHABLES 3 CC.` | Jeringas desechables |
| 3 | `FUNDO CHAPICAHUIN` | Aplicación de cal |
| 3 | `AZUCAR IANSA 1 KG` | Azucar Iansa |
| 2 | `-BUSHING REDUCCION HE-HI 1 X 1 2 -@` | Bushing Reduccion HE HI X |
| 2 | `TAUTO-FINA 2 1 2 TORNILLO AUTOPERF FINA CAJA 100 UN -@` | Tornillos |
| 2 | `TVZC TORNILLO VOLCANITA ZINC 3 CJ 100UN -@` | Tornillos |
| 2 | `QUIX 10 LT.` | Quix |
| 2 | `TERMINAL HE PLASTICO 1"` | Terminal HE Plastico |
| 2 | `GALLETA GRETEL COSTA 85 GR, CHOCOLATE` | Galleta Gretel Costa Chocolate |
| 2 | `CODO PVC-SANIT.GRIS 110MM X 90§` | Codo PVC Sanit Gris X |
| 2 | `TIRA TUBO COLECTOR 200 MM X 6MTS -@` | Tira Tubo Colector X |
| 2 | `JERINGA DESECHABLE 5 ML C/AGUJA (L.L.)` | Jeringas desechables |
| 2 | `Multa por consumo reactivo (Recargo por consumo reactivo) ( 0,910 )` | Recargo por consumo reactivo |
| 2 | `Ñ-CURVA SANITARIA GRIS 40 X 45 -@` | N Curva Sanitaria Gris X |
| 2 | `CLAVOS 2 1/2 X 11` | Clavos |
| 2 | `AGUJA DESECHABLE (C/PLAST) 21 G x 1` | Agujas desechables |
| 2 | `BUSHING GALVANIZADO 1 X 3/4"` | Bushing Galvanizado X |
| 2 | `PL-TERMINAL HI 1 1 4 PLANSA -@` | Pl Terminal HI Plansa |
| 2 | `Válvula de Bola PP 63mm HI Arangül` | Valvula de Bola Pp HI Arangul |
| 2 | `VALVULA DE BOLA HI ITALI 1,1/4"` | Valvula de Bola HI Itali |
| 2 | `CLAVO CORRIENTE 3" X 10 (KG)` | Clavos |
| 2 | `BUSHING PLAST.BCO.HI HE 1,1/2 X 1,1/4"` | Bushing Plast Bco HI HE X |
| 2 | `BUSHING PLAST.BCO.HI HE 1 X 3/4"` | Bushing Plast Bco HI HE X |
| 2 | `TORNILLO VOLCANITA ZINC. 6 X 2" (100UN)` | Tornillos |
| 2 | `Multa por consumo reactivo (Recargo por consumo reactivo) ( 0,850 )` | Recargo por consumo reactivo |
| 2 | `CLAVO CORRIENTE 4" X 8 (KG) "OFERTA"` | Clavos |
| 2 | `BUSHING PLAST.BCO.HI HE 2 X 1,1/2"` | Bushing Plast Bco HI HE X |
| 2 | `VIAJE 32 VACAS` | Viaje Vacas |
| 2 | `VIAJE 50 VAQUILLAS` | Viaje Vaquillas |
| 2 | `UNION PLASTICA 1"` | Union Plastica |
| 2 | `BUSHING PLAST.BCO.HI HE 1,1/2 X 3/4"` | Bushing Plast Bco HI HE X |
| 2 | `TAPON GORRO PLAST.BCO.HI 4"` | Tapon Gorro Plast Bco HI |
| 2 | `GRAPAS 1 1/4 X 10` | Grapas X |
| 2 | `GALLETA TRITON MCKAY 126 GR, VAINILLA` | Galleta Triton Mckay Vainilla |
| 2 | `QUESO GAUDA COLUN RANCO LAM 150 GR` | Queso Gauda Colun Ranco Lam |
| 2 | `HDPE-TERMINAL HI COMPRESION 50MM X 1 1/2 -@` | HDPE Terminal HI Compresion X |
| 2 | `-BUSHING REDUCCION HE-HI 1 1 2 X 1 -@` | Bushing Reduccion HE HI X |
| 2 | `GALLETA TRITON MCKAY 116GR, NARANJA` | Galleta Triton Mckay Naranja |
| 2 | `Cargo mensual por D. Max de potencia suministrada ( 37,100 )` | Cargo mensual por demanda máxima suministrada |
| 2 | `UNION PLASTICA 1,1/4"` | Union Plastica |
| 2 | `TERMINAL HE PLASTICO 1,1/4"` | Terminal HE Plastico |
| 2 | `Multa por consumo reactivo (Recargo por consumo reactivo) ( 0,900 )` | Recargo por consumo reactivo |
| 2 | `Copla Compresión 50mm Arangül` | Copla Compresion Arangul |
| 2 | `Multa por consumo reactivo (Recargo por consumo reactivo) ( 0,920 )` | Recargo por consumo reactivo |
| 2 | `BOTAS BEKINA STEPLITE-X P.A.#42` | Botas Bekina Steplite X P a |
| 2 | `AGUJA DESECHABLE (C/PLAST) 26 G x 1/2` | Agujas desechables |
| 2 | `MOSKIMIC FORTE POUR ON 1 LITRO` | Moskimic Forte Pour On |
| 2 | `K-L TUBO ALZADOR 40 MM X 300 MM` | K L Tubo Alzador X |
| 2 | `BOTAS BEKINA STEPLITE-X P.A.#38` | Botas Bekina Steplite X P a |
| 2 | `UNION PLASTICA 1,1/2"` | Union Plastica |
| 2 | `VALVULA BOLA COMPACTA HI 1 2 -@` | Valvula Bola Compacta HI |
| 2 | `HELIFLEX LIVIANA C/ANILLO 4" (100MM)` | Heliflex Liviana C Anillo |
| 2 | `COLLAR ARRANQUE PVC P/PVC 50 X 1"` | Collar Arranque PVC P PVC X |
| 2 | `* MT.X TIRA PVC-SANITARIO GRIS 40MM "OFERTA"` | X Tira PVC Sanitario Gris |
| 2 | `VALVULA DE BOLA PVC-HILO S/UNION 50MM = 1,1/2"` | Valvula de Bola PVC Hilo S Union |
| 2 | `TERMINAL HE PLASTICO 1,1/2"` | Terminal HE Plastico |
| 2 | `TEFLON MAESTRO 1/2"` | Teflon Maestro |
| 2 | `TEFLON MAESTRO 1"` | Teflon Maestro |
| 2 | `BROCHA PLANA - HELA 3"` | Brocha Plana Hela |
| 2 | `BROCHA PLANA - HELA 4"` | Brocha Plana Hela |
| 2 | `VALVULA ACOPLE RAPIDO ASPERSOR 3/4"` | Valvula Acople Rapido Aspersor |
| 2 | `BOTIN NORSEG NS586 PRO CAFÉ 43` | Botin Norseg Ns586 Pro Cafe |
| 2 | `FORMALINA X 22 LTS` | Formalina X |
| 2 | `BOTAS DUNLOP THERMO+ # 44-45 (-40 C)` | Botas Dunlop Thermo C |
| 2 | `K-L TUBO ALZADOR 40 MM X 800 MM` | K L Tubo Alzador X |
| 2 | `HDPE-COPLA COMPRESION 63MM -@` | HDPE Copla Compresion |
| 2 | `TAPON GORRO PLAST.BCO.HI 1/2"` | Tapon Gorro Plast Bco HI |
| 2 | `BUZO VETERINARIO 1 PIEZA TALLA 52` | Buzo Veterinario Pieza Talla |
| 2 | `TAUTO-BROCA 2 1 2 TORNILLO AUTOPERF BROCA CAJA 100 UN -@` | Tornillos |
| 2 | `LIMA 5 5 MM 7 32` | Lima |
| 2 | `LLAVE BOLA JARDIN PN16 DE 1 2 X 3 4 GENEBRE -@` | Llave Bola Jardin Pn16 de X Genebre |
| 2 | `TUB CUAD NEG 75 X 3.0 MM` | Tub Cuad Neg X |
| 2 | `Botellón 20 litros` | Botellon |
| 2 | `LLAVE BOLA JARDIN PN16 DE 3 4 X 1 GENEBRE -@` | Llave Bola Jardin Pn16 de X Genebre |
| 2 | `-CODO HI-HI 3 4 -@` | Codo HI HI |
| 2 | `SULFATO COBRE 1 KG. -____` | Sulfato Cobre |
| 2 | `CAÑERIA NEGRA PN4 2"` | Caneria Negra Pn4 |
| 2 | `AZUCAR GRANULADA IANSA 1 KG` | Azucar Granulada Iansa |
| 2 | `CLAVO CTE.6 X5 BOL 2.5 KG. CUN` | Clavos |
| 2 | `CLAVO CTE 4 2,5KG CUN029` | Clavos |
| 2 | `CAÑERIA NEGRA PN4 1/2"` | Caneria Negra Pn4 |
| 2 | `MANGUERA ESPIRALADA AMARILLA 2 -@` | Manguera Espiralada Amarilla |
| 2 | `AZUCAR GRANULADA IANSA 900 GR` | Azucar Granulada Iansa |
| 2 | `COCA COLA DESECHABLE 591 CC` | Coca Cola Desechable |
| 2 | `ABRAZADERA SEBCOR 1.1/2"` | Abrazadera Sebcor |
| 2 | `ABRAZADERA OMEGA 25MM -@` | Abrazadera Omega |
| 2 | `-NIPLE HE-HE 2 -@` | Niple HE HE |
| 2 | `HDPE-CODO 25MM - PN16 -@` | HDPE Codo Pn16 |
| 2 | `AGUJA DESECHABLE (C/PLAST) 18 G x 1 1/2` | Agujas desechables |
| 2 | `CLAVO CTE 4 BOLSA 1KG CUN06C` | Clavos |
| 2 | `Cargo mensual por D. Max de potencia suministrada ( 37,500 )` | Cargo mensual por demanda máxima suministrada |
| 2 | `* VALVULA DE BOLA HI ITALI 1/2" *OFERTA*` | Valvula de Bola HI Itali |
| 2 | `BUSHING GALVANIZADO 3/4 X 1/2"` | Bushing Galvanizado X |
| 2 | `ABRAZADERA CREM. 3/4" (16-25)` | Abrazadera Crem |
| 2 | `ZINC 5V TINGLE 0 35 X 2 5 MT -@` | Zinc 5v Tingle X |
| 2 | `ABRAZADERA CON PERNO 60MM-63MM -@` | Abrazadera con Perno |
| 2 | `CLORINDA 2KG` | Clorinda |
| 2 | `PCO PERNO COCHE 5 16 X 1 -@` | Pco Perno Coche X |
| 2 | `CLAVO DE 5KG -@` | Clavos |
| 2 | `MANGA DE LECHE 16 MM./MT` | Manga de Leche |
| 2 | `CORREA BX-70` | Correa Bx |
| 2 | `MANZANA ROJA FRUTALAN MALLA KG` | Manzana Roja Frutalan Malla |
| 2 | `Copla Compresión 63mm Arangül` | Copla Compresion Arangul |

## Deliberately excluded — 781 wordings, 859 lines

Unbounded wordings. `SEGUN OT 107`, `108`, `109` would need one alias row each,
forever, which is exactly what D-044 forbids. These need a **pattern**, and deciding
whether the varying part is a quantity or an identity is where the Yunt earns its
cost.

| wording | why |
|---|---|
| `SEGUN OT 107` | unbounded wording (OT/folio/month/contract number) |
| `SEGUN OT 240` | unbounded wording (OT/folio/month/contract number) |
| `SEGUN OT 175` | unbounded wording (OT/folio/month/contract number) |
| `SEGUN OT 108` | unbounded wording (OT/folio/month/contract number) |
| `SEGUN OT 173` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70563 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `01/12/2025 - Tiquet Restaurante - 5085110 - Restaura` | unbounded wording (OT/folio/month/contract number) |
| `21/10/2025 - Tiquet Restaurante - 5061563 - Restaura` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71335 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `TRANSPORTE DE CARGA Y ENCOMIENDA: 252700360` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71694 - ANALISIS : COOP-FECAS-RECUEN` | unbounded wording (OT/folio/month/contract number) |
| `TRANSPORTE DE CARGA Y ENCOMIENDA: 254539329` | unbounded wording (OT/folio/month/contract number) |
| `COMISION DE USO MENSUAL (Nro. Documento: 47415000142` | unbounded wording (OT/folio/month/contract number) |
| `LIJA AL AGUA GRANO 100 M 611309` | unbounded wording (OT/folio/month/contract number) |
| `Transporte de Electricidad ( 21 kWh)` | unbounded wording (OT/folio/month/contract number) |
| `Transporte de Electricidad ( 5.691 kWh)` | unbounded wording (OT/folio/month/contract number) |
| `Transporte de Electricidad ( 4.519 kWh)` | unbounded wording (OT/folio/month/contract number) |
| `Transporte de Electricidad ( 18.400 kWh)` | unbounded wording (OT/folio/month/contract number) |
| `Transporte de Electricidad ( 110 kWh)` | unbounded wording (OT/folio/month/contract number) |
| `TRANSPORTE DE CARGA Y ENCOMIENDA: 247753082` | unbounded wording (OT/folio/month/contract number) |
| `MONITOREO MES DE 11/2025 CONTRATO 1731275` | unbounded wording (OT/folio/month/contract number) |
| `Cargo por servicio publico Base ( 16.410 kWh) (Ex. I` | unbounded wording (OT/folio/month/contract number) |
| `MONITOREO MES DE 08/2025 CONTRATO 1731275` | unbounded wording (OT/folio/month/contract number) |
| `MONITOREO MES DE 03/2025 CONTRATO 1731275` | unbounded wording (OT/folio/month/contract number) |
| `Cargo por servicio publico Base ( 39 kWh) (Ex. IVA)` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70912 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70919 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70701 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71334 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71617 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71336 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70922 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 70374 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71082 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `PLANILLA NUMERO 71081 - ANALISIS : COOP-SANGRE/SUERO` | unbounded wording (OT/folio/month/contract number) |
| `Cargo Fondo de Estabilizacion Ley 21.472 ( 3.101 kWh` | unbounded wording (OT/folio/month/contract number) |
| `MONITOREO MES DE 03/2026 CONTRATO 1697527` | unbounded wording (OT/folio/month/contract number) |
| `MONITOREO MES DE 12/2025 CONTRATO 1731576` | unbounded wording (OT/folio/month/contract number) |
| `SEGUN OT 82` | unbounded wording (OT/folio/month/contract number) |
| `TRANSPORTE DE CARGA Y ENCOMIENDA: 247095160` | unbounded wording (OT/folio/month/contract number) |

…and 741 more in `excluded.jsonl`.

## Not proposed — 585 wordings, 585 lines

Seen exactly once in fifteen months. An alias that has already fired and will
probably never fire again is memorised noise. They are in `once_stable.jsonl` if
you want them; my recommendation is to leave them out.
