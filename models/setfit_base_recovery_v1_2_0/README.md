---
tags:
- setfit
- sentence-transformers
- text-classification
- generated_from_setfit_trainer
widget:
- text: Uso del sistema de transmision | COOPERATIVA RURAL ELECT.R.BUENO LTDA.
- text: GALLETA DONUTS COSTA 100 GR, BITTER | 2.0 x 1 UN $1340 Bruto/$1126.5 Neto
    | RENDIC HERMANOS S.A.
- text: RIEGO PURINES RAICES | Purines raices 29 carradas de 11.000 lts | SERVICIOS
    AGRICOLAS CORPAL SPA
- text: CAERIA NEGRA PN4 3/4" | CAERIA NEGRA PN4 3/4" | COOPERATIVA AGRICOLA Y LECHERA
    DE LA UNION LTDA.
- text: MANIJA SOFT TOUCH CUERDA (G69703) | COLUN
metrics:
- accuracy
pipeline_tag: text-classification
library_name: setfit
inference: true
base_model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
---

# SetFit with sentence-transformers/paraphrase-multilingual-mpnet-base-v2

This is a [SetFit](https://github.com/huggingface/setfit) model that can be used for Text Classification. This SetFit model uses [sentence-transformers/paraphrase-multilingual-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2) as the Sentence Transformer embedding model. A [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance is used for classification.

The model has been trained using an efficient few-shot learning technique that involves:

1. Fine-tuning a [Sentence Transformer](https://www.sbert.net) with contrastive learning.
2. Training a classification head with features from the fine-tuned Sentence Transformer.

## Model Details

### Model Description
- **Model Type:** SetFit
- **Sentence Transformer body:** [sentence-transformers/paraphrase-multilingual-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2)
- **Classification head:** a [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance
- **Maximum Sequence Length:** 64 tokens
- **Number of Classes:** 68 classes
<!-- - **Training Dataset:** [Unknown](https://huggingface.co/datasets/unknown) -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Repository:** [SetFit on GitHub](https://github.com/huggingface/setfit)
- **Paper:** [Efficient Few-Shot Learning Without Prompts](https://arxiv.org/abs/2209.11055)
- **Blogpost:** [SetFit: Efficient Few-Shot Learning Without Prompts](https://huggingface.co/blog/setfit)

### Model Labels
| Label    | Examples                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|:---------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ADM-1.10 | <ul><li>'PREVENCION DE RIESGOS | CONSULTORIA POR PROFESIONAL EN SEGURIDAD Y SALUD OCUPACIONAL OCTUBRE | SERVICIOS PROFESIONALES EN SEGURIDAD Y SALUD OCUPACIONAL JACQUELINE FU'</li><li>'CONSULTORIA EN GESTION DE PERSONAS | SERVICIOS PROFESIONALES EN SEGURIDAD Y SALUD OCUPA'</li><li>'RECURSOS HUMANOS | CONSULTORIA EN GESTIÓN DE PERSONAS MAYO | SERVICIOS PROFESIONALES EN SEGURIDAD Y SALUD OCUPACIONAL JACQUELINE FU'</li></ul>                                                                                                                                               |
| ADM-1.2  | <ul><li>'Decodificadores Adicionales | DIRECTV Chile Televisión Limitada'</li><li>'KIT INSTALACION 0 VISION 100 | VERISURE CHILE SPA'</li><li>'Cargo Fijo BAM | Telefnica Mviles Chile S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                  |
| ADM-1.3  | <ul><li>'Arriendo junio 26 | ADDVISE SPA'</li><li>'ARRIENDO OCTUBRE 25 | ADDVISE SPA'</li><li>'Arriendo mayo 26 | ADDVISE SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ADM-1.4  | <ul><li>'Gastos Cobranza | RUTA DEL MAIPO SOCIEDAD CONCESIONARIA, S.A.'</li><li>'Intereses Exentos | SOCIEDAD CONCESIONARIA RUTA 5 TALCA-CHILLAN S.A.'</li><li>'Recarga de Prepagos | Ruta de los Rios Sociedad Concesionaria S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                           |
| ADM-1.5  | <ul><li>'SERVICIOS DE ALOJAMIENTO | RESERVA ID 103631 HAB 109 - TPL Hotel Diego de Almagro Los Angeles DESDE 01-10-2025 A 02-10-2025 CRISTIAN ANGUITA YV | COMERCIAL MAIFA LTDA.'</li><li>'Habitaciones ( 1) | TALBOT HOTELS S A'</li><li>'ALMUERZOS | MINERVA RUTH ARELLANO VASQUEZ'</li></ul>                                                                                                                                                                                                                                                                                         |
| ADM-1.6  | <ul><li>'PAPEL HIG ULTRA DH ELITE 40MTX18 | 2.0 x 1 UN $19290 Bruto/$16210.0 Neto | RENDIC HERMANOS S.A.'</li><li>'Recarga Agua Purificada | Fundo Raices | PURIFICADORA DE AGUA ALEJANDRO SALAZAR RIVERA E.I.R.L.'</li><li>'CABLE TIPO-C A HDMI 1.8M TM-100539 | COOPRINSEM'</li></ul>                                                                                                                                                                                                                                                                                                 |
| ADM-1.7  | <ul><li>'MONITOREO MES DE 01/2025 CONTRATO 1731305 | VERISURE CHILE SPA'</li><li>'TRANSPORTE DE CARGA Y ENCOMIENDA | EGT LIMITADA'</li><li>'MONITOREO MES DE 07/2025 CONTRATO 1731305 | VERISURE CHILE SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                   |
| ADM-1.8  | <ul><li>'FACTURACION ELECTRONICA | GestionDTE Facturas Periodo Marzo de 2025 | AUDISOFT SPA'</li><li>'FACTURACION ELECTRONICA | GestionDTE Facturas Periodo Octubre de 2025 | AUDISOFT SPA'</li><li>'FACTURACION ELECTRONICA | GestionDTE Facturas Periodo Agosto de 2025 | AUDISOFT SPA'</li></ul>                                                                                                                                                                                                                                                                                     |
| ADM-2.1  | <ul><li>'Ramo VEHICULOS MOTORIZADOS - HDI/ Poliza 586507 Item 5 | HDI SEGUROS S.A.'</li><li>'Pago cuota 9. Póliza Vehiculos | REALE CHILE SEGUROS GENERALES S.A.'</li><li>'Ramo VEHICULOS MOTORIZADOS - HDI/ Poliza 586507 Item 4 | HDI SEGUROS S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                         |
| ADM-2.2  | <ul><li>'RUTCOBRANZA 96685810 | Cia de Seguros de Vida Consorcio Nacional de Seguros SA'</li><li>'SEGURO COLECTIVO. POLIZA N°12799 | CIA DE SEGUROS DE VIDA CONSORCIO'</li><li>'Periodo de Cobertura octubre 2025 | Cia de Seguros de Vida Consorcio Nacional de Seguros SA'</li></ul>                                                                                                                                                                                                                                                                                                  |
| ADM-2.3  | <ul><li>'DEVOLUCION DE PRIMA CUOTA 9 | REALE CHILE SEGUROS GENERALES S.A.'</li><li>'POLIZA 6615118, FECHA DE PAGO 11/12/2025 | Cia de Seguros Generales Consorcio Nacional de Seguros SA'</li><li>'POLIZA 6615118, FECHA DE PAGO 08/08/2025 | Cia de Seguros Generales Consorcio Nacional de Seguros SA'</li></ul>                                                                                                                                                                                                                                                                      |
| EXP-1.1  | <ul><li>'CENA 41 PERSONAS N.OP.080 | VICTOR VERA VIVEROS'</li><li>'Programa de inglés | ENGLISH TRAINING SPA'</li><li>'HARRY POTTER 1 Y LA PIEDRA FILOSOFAL | Ainilebu SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                   |
| EXP-10.1 | <ul><li>'MANGAS PARA ORDEA MECANICA | MANGA REUTILIZABLE IMPERMEABLE | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'JUEGO DE SERVICIO-TRANSPORTE DE LECHE(C) VAR SANITARY TRAP 22 | GEA Farm Technologies Osorno Ltda.'</li><li>'MOSQUETON | GEA Farm Technologies Osorno Ltda.'</li></ul>                                                                                                                                                                                                                                                                                |
| EXP-10.2 | <ul><li>'FULLDIP 5000 PROMOCION 230 kg | GEA Farm Technologies Osorno Ltda.'</li><li>'COW GUARD BARRERA 210KG | BIOGENESIS ANIMAL HEALTH SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| EXP-10.3 | <ul><li>'ORACID 60 L | HGS DAIRY SOLUTIONS SPA'</li><li>'PIOLA PERLON RETIRADOR (NEGRA)/ MT | GEA Farm Technologies Osorno Ltda.'</li><li>'SOLUTION 60 lts | GEA Farm Technologies Osorno Ltda.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                              |
| EXP-10.4 | <ul><li>'JUEGO PEZONERAS COLECTOR 300 | GEA Farm Technologies Osorno Ltda.'</li><li>'TAPA COLECTOR 300 CC. SIN CIERRE | GEA Farm Technologies Osorno Ltda.'</li><li>'SEAL KIT FOR HILGE MILK PUMP 2.2KW | GEA Farm Technologies Osorno Ltda.'</li></ul>                                                                                                                                                                                                                                                                                                                                 |
| EXP-11.1 | <ul><li>'Cargo fondo de estabilizacion ley 21.472 | COOPERATIVA RURAL ELECT.R.BUENO LTDA.'</li><li>'Transporte de Electricidad | CIA ELECTRICA OSORNO S A'</li><li>'Recargo lectura de BT de consumos de cliente en AT(E) 3,5% | COOPERATIVA ELECTRICA PAILLACO LIMITADA'</li></ul>                                                                                                                                                                                                                                                                                                     |
| EXP-11.2 | <ul><li>'Electricidad consumida ( 458 kWh) | COOPERATIVA ELECTRICA PAILLACO LIMITADA'</li><li>'Cargo por servicio publico Base ( 458 kWh) (Ex. IVA) | COOPERATIVA ELECTRICA PAILLACO LIMITADA'</li><li>'Electricidad Casas e Instalaciones - COOPERATIVA ELECTRICA PAILLACO LTDA | COOPERATIVA ELECTRICA PAILLACO LTDA'</li></ul>                                                                                                                                                                                                                                                       |
| EXP-11.3 | <ul><li>'PETROLEO DIESEL ULTRA | COOP. AGRICOLA Y LECHERA LA UNION'</li><li>'PETROLEO DIESEL ULTRA | COOPERATIVA AGRICOLA Y LECHERA DE LA UNI'</li><li>'PETROLEO DIESEL | FEROSOR AGRICOLA S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                              |
| EXP-11.4 | <ul><li>'Aramco Gasolina 93 | Aramco Gasolina 93@@Fecha 12/12/2025 Base 6.00 UTM/m3; 417,252; Variable 1 UTM/m3; 35,119 | Esmax Distribucion SpA'</li><li>'GASOLINA 93 | COOPERATIVA AGRICOLA Y LECHERA DE LA UNI'</li><li>'Gasolina 95 octanos sin plomo | IE Base: 417.2520 - IE Variable: 0.0000 | INVERSIONES ENEX S.A.'</li></ul>                                                                                                                                                                                                                                                  |
| EXP-11.5 | <ul><li>'Galón de Gas 45 kgs. | JULIA IGNACIA FUENTES FLORES'</li><li>'FLEXIBLE GAS 1 2X1 2 SERCOGAS 1METRO CER -@ | FLEXIBLE GAS 1 2X1 2 SERCOGAS 1METRO CER -@ | DORIS IVONNE CASTILLO KANTER'</li><li>'CARGA GAS 15 KG | RICARDO GERMAN OSWALD BUCHNER'</li></ul>                                                                                                                                                                                                                                                                                                                    |
| EXP-12.1 | <ul><li>'PLANILLA NUMERO 73698 - ANALISIS : COOP-FECAS-PARASITOS PUL | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'ANALISIS COMPLETO TEJIDO VEGETAL | COOPERATIVA AGRICOLA Y DE SERVICIOS LTDA'</li><li>'REVERSA ANALISIS COOPERADO | REVERSA ANALISIS COOPERADO | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li></ul>                                                                                                                                                                                                                                           |
| EXP-12.2 | <ul><li>'PLANILLA NÚMERO 71339 - ANÁLISIS : COOP | COLUN'</li><li>'PLANILLA NÚMERO 71081 - ANÁLISIS : COOP | COLUN'</li><li>'PLANILLA NÚMERO 70563 - ANÁLISIS : COOP | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                 |
| EXP-13.1 | <ul><li>'A. SPIRAX S4 TXM X 18,9 L (958955) | COLUN'</li><li>'ACEITE DE CADENA LTS | ACEITE DE CADENA LTS | LIDIA ANGELICA SANHUEZA FUENTES'</li><li>'A. TELLUS S2 MX 68 X 18,9 L (964630) | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                           |
| EXP-13.2 | <ul><li>'MANTENION Y REPARACION | MANTENCION MOTOS RAICES SEGUN OT N° 496, 497- | MULTIMOTOS OSORNO SPA'</li><li>'BATERIA | MULTIMOTOS OSORNO SPA'</li><li>'FUELLES HOMOCINETICAS | MULTIMOTOS OSORNO SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                    |
| EXP-13.3 | <ul><li>'BLUEMAX | DISTRIBUIDORA COMERCIAL P Y G LIMITADA'</li><li>'Reparar tapa trasera | Camioneta Maxus | SERVIMEC SPA'</li><li>'Cambio manguera turbo | Camioneta. | SERVIMEC SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                        |
| EXP-14.1 | <ul><li>'ARRIENDO EXCAVADORA | 3,9 HRS. x $50.000.- | JUAN ALBERTO MIRANDA REYES'</li><li>'CORTE DE LIMPIEZA | AGRÍCOLA J-S-E LIMITADA'</li><li>'ARRIENDO DE RETRO EXCAVADORA | SOC COMERCIAL NAHUM CORREA LTDA'</li></ul>                                                                                                                                                                                                                                                                                                                                                              |
| EXP-14.2 | <ul><li>'CLAVOS TERRANO 1 1/2 !¡ | COLUN'</li><li>'A. SPIRAX S4 TXM JC X 20 L (968314) | A. SPIRAX S4 TXM X 20 L (958708) | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'CABLE POLY BLA 6SS 500M (G62007) | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                              |
| EXP-14.3 | <ul><li>'TERMINAL HE PLANSA 1/2 " - HOFFENS | TERMINAL HE PLANSA 1/2 " - HOFFENS | COMERCIAL HARCHA SPA'</li><li>'HANSEN REP VARILLA CORTA 202MM SUPER-FLO | COLUN'</li><li>'MANGUERA STAR GARDEN 3/4" 5 BAR | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                         |
| EXP-14.4 | <ul><li>'INSTALACIN DE | FOSA SPTICA Y CMARA EN LECHERA. | SERVICIOS DE MANTENCIN DOMICILIARIA NONTUELA SPA'</li><li>'INSTALACION DE LAVADORA | EN SALA DE ORDEÑA | SERVICIOS DE MANTENCIÓN DOMICILIARIA NONTUELA SPA'</li><li>'HULE AFRANELADO DELGADO 1.40 ANCHO | HULE AFRANELADO DELGADO 1.40 ANCHO | COMERCIAL HARCHA SPA'</li></ul>                                                                                                                                                                                                                                               |
| EXP-15.1 | <ul><li>'ASESORIA AGROPECUARIA | SOC ROBERTO AICHELE Y CIA LIMITADA'</li><li>'ASESORIA AGROPECUARIA | SOCIEDAD ROBERTO AICHELE Y CIA LTDA.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| EXP-15.2 | <ul><li>'HONORARIOS VETERINARIOS LDS | LECHERIAS DEL SUR'</li><li>'PODOLOGÍA CORRECTIVA | 26 febrero: 25 vacas cojas | MOLINA MANNS SPA'</li><li>'PODOLOGÍA CLÍNICA BOVINA | Servicio realizado 15 abril 2025 por Roberto Molina | MOLINA MANNS SPA'</li></ul>                                                                                                                                                                                                                                                                                                                          |
| EXP-15.3 | <ul><li>'Flete de Fdo. Yutreco a | Feria 26.09 | EDGARDO EDMUNDO MANCILLA CARRION'</li><li>'FLETE DE FDO YUTRECO A FERIA | EDGARDO EDMUNDO MANCILLA CARRION'</li><li>'Fletes - SERVICIOS FABIAN ROLDAN SPA | SERVICIOS FABIAN ROLDAN SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                     |
| EXP-15.4 | <ul><li>'ARRIENDO DE VEHICULOS | ARRIENDO DE VEHICULOS~ | ARRENDADORA DE VEHICULOS SOCIEDAD ANONIMA'</li><li>'Arriendo de tractor Junio | JORGE HECTOR KIESSLING PINUER'</li><li>'Arriendo Maquinaria y Vehiculos - HAKA INDUSTRIAL SPA | HAKA INDUSTRIAL SPA'</li></ul>                                                                                                                                                                                                                                                                                                                |
| EXP-15.5 | <ul><li>'INCORPORADOR | AGRÍCOLA J-S-E LIMITADA'</li><li>'TRASLADO DE ABONO | 2 VUELTAS - TINEO | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'OCTUBRE | SERVICIO DE CARRO PURINERO CORRESPONDIENTE A ( 36 CARROS X 11.000 LT) | AGRÍCOLA RIBERAS DEL SAUCE SPA'</li></ul>                                                                                                                                                                                                                                                                                          |
| EXP-16.1 | <ul><li>'PICOTA TRUPER 5 LB C/MANGO | COLUN'</li><li>'Guante Ordea Nitrilo Soflo Bio Largo Talla L (Caja 100u) | SOCIEDAD COMERCIAL SOFLO SPA'</li><li>'PM ESCOBILLA MANGO P/ EST. | COOPRINSEM'</li></ul>                                                                                                                                                                                                                                                                                                                                                                              |
| EXP-16.2 | <ul><li>'PINTACAL X 25 KILOS SOPROCAL | COOPRINSEM'</li><li>'SULFATO DE COBRE X 25 KL. | SULFATO DE COBRE X 25 KL. | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'RECARGA GAS BUTANO 300 ML 216059 | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                     |
| EXP-2.1  | <ul><li>'ORBENIN X 36 JER | ORBENIN X 36 JER | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'UBRISEC'</li><li>'FATROXIMIN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| EXP-2.2  | <ul><li>'PATHOZONE | COLUN'</li><li>'MASTIPLAN LC X 20 JER | COLUN'</li><li>'GUANTES SHOOF LARGO (L) NITRI.AZUL CAJA 100 UN -____ | ____ | FEROSOR AGRICOLA S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                             |
| EXP-2.3  | <ul><li>'VACUNA FORTRESS 50 DS BORGPETERSENIL HAR | COOPRINSEM'</li><li>'VACUNA LEPTOFERM 5 X 50 DOSIS | COLUN'</li><li>'VACUNA CATTLEMASTER GOLD 25 DOSIS | COOPERATIVA AGRICOLA Y DE SERVICIO LTDA.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                        |
| EXP-2.4  | <ul><li>'COLUBLOCK SUPERCRIANZA COX X 18 KG | COLUN'</li><li>'SALFORT PASTOREO X | COOPERATIVA AGRÍCOLA Y LECHERA DE LA UNIÓN LTDA'</li><li>'VITAMIN+ TERNERO X 10 BOLOS | VITAMIN+ TERNERO X 10 BOLOS | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li></ul>                                                                                                                                                                                                                                                                                                                    |
| EXP-2.5  | <ul><li>'MOSKIMIC FORTE X 3 LT. | COLUN'</li><li>'VIVEFORT 3 AMPOLLAS X 10 ML | COLUN'</li><li>'MOSKIMIC FORTE POUR ON 3 LITRO | COOPRINSEM'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| EXP-2.6  | <ul><li>'BANDEJAS TEST MASTITIS | COLUN'</li><li>'ALLFLEX MAXI(H)-BOTON(M) ESTAMPADO | COOPRINSEM'</li><li>'PINTURA CELO TELL TAIL SPRAY ROJ 500 cc | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                  |
| EXP-3.1  | <ul><li>'METRICURE X 12 JER | COLUN'</li><li>'HORM. CIDR BOVINO APLICADOR | COOPRINSEM'</li><li>'Semen Bovino Leche Convencional CENTURION | ABS CHILE LIMITADA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                              |
| EXP-4.1  | <ul><li>'CULTIVO SILO RASTRA | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'TRASLADO BOLOS SILOS | CON CARRO Y RETORNO DESDE MAITEN A YUTRECO ( 1 VIAJE ) | LUIS ANTONIO TORRES JARAMILLO'</li><li>'PLASTICO SILO FEROSOR X UNIDAD -Ferosor_14x35x125_NEGRO__ | Ferosor_14x35x125_NEGRO__ | FEROSOR AGRICOLA S.A.'</li></ul>                                                                                                                                                                                                                                        |
| EXP-4.2  | <ul><li>'Aplicacin de lodo | HECTOR ADRIAN VALENZUELA PAREDES'</li><li>'SILOSOLVE MC X 100 G | COLUN'</li><li>'Diferencia bolos tineo | HECTOR ADRIAN VALENZUELA PAREDES'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                     |
| EXP-4.3  | <ul><li>'BOLOS PASTO SECO PELLECO | 392 bolos pasto seco | SERVICIOS AGRICOLAS CORPAL SPA'</li><li>'FILM PARA BOLO WINPACK 750MM X 1500MT BLANCO | ROLLO 1500 MT| | Tattersall AgroInsumos S.A.'</li><li>'CONFECCION BOLOS PELLECO | AGRÍCOLA J-S-E LIMITADA'</li></ul>                                                                                                                                                                                                                                                                                                                 |
| EXP-5.1  | <ul><li>'Mipro Pastoreo | //FUNDO MAITEN G/6986 y 6999 | SANO - NUTRICION ANIMAL MODERNA SPA'</li><li>'BIOLACT ANTILLANCA GRANEL | AGROCOMERCIAL IANSA S.A.'</li><li>'MAIZ ROLEADO PF GRANEL x KG-ALIMENTOS(E)-MAIZ | COMPAÃ\x91Ã\x8dA AGROPECUARIA COPEVAL S.A.'</li></ul>                                                                                                                                                                                                                                                                                                             |
| EXP-5.2  | <ul><li>'T. SURALIM INICIAL RF X 25 KG | COLUN'</li><li>'T. SURALIM CRECIMIENTO RF X 25 KG | COLUN'</li><li>'CONCENTRADO TERNERO 1 STANDARD -Ferosor_25kg_Sin Sal_PBF_ | Ferosor_25kg_Sin Sal_PBF_ | FEROSOR AGRICOLA S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                                   |
| EXP-5.3  | <ul><li>'COLMILLO BLANCO X 20KG (ADULTO&amp;CACHORRO) | COLMILLO BLANCO X 20KG (ADULTO&amp;CACHORRO) | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li><li>'COLMILLO BLANCO X 20KG (ADULTO&CACHORRO) | COLUN'</li><li>'TOALLA PAPEL INTERFOLIADA | COOPERATIVA AGRÍCOLA Y LECHERA DE LA UNIÓN LTDA'</li></ul>                                                                                                                                                                                                                                                                     |
| EXP-5.4  | <ul><li>'BOLOS FUTRONO | Bolos futrono 149 | SERVICIOS AGRICOLAS CORPAL SPA'</li><li>'MOVIMIENTOS DE BOLOS | AGRÍCOLA J-S-E LIMITADA'</li><li>'Maxxifardos | SERVICIOS AGRICOLAS MECANIZADOS SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                             |
| EXP-5.5  | <ul><li>'SUST. KALMILAC PLUS 25 KGS SCHILS | COOPRINSEM'</li><li>'SUST. EUROLAC BLUE 25 KGS. SCHILS | COOPRINSEM'</li><li>'SUSTITUTO LACTEO COLUN (SPT) 25 KG | SUSTITUTO LACTEO COLUN (SPT) 25 KG | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li></ul>                                                                                                                                                                                                                                                                                                                        |
| EXP-6.1  | <ul><li>'FOSFATO DIAMONICO'</li><li>'BRAM. FERTILIZACION MAP | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'FOSFATO MONOAMONICO FUNDO | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                            |
| EXP-6.2  | <ul><li>'CAN 27 FUNDO | COLUN'</li><li>'FERT. SMART-BRAMADERO | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'SMART BLUE - MAITEN | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                |
| EXP-6.3  | <ul><li>'CAL SUR IANSA A GRANEL | IANSAGRO S.A.'</li><li>'CAL IM MINERALS FUNDO | COLUN'</li><li>'Ton Aplicación Cal | Ton Aplicación Cal | Servicios Bergström Limitada'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                     |
| EXP-6.4  | <ul><li>'APLICACION KG GUANO TEBBE | APLICACION KG GUANO TEBBE | Servicios Bergström Limitada'</li><li>'GUANO DE GALLINA FUNDO | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| EXP-6.5  | <ul><li>'TRAS.FERTILIZANT VITRAMAG | DESDE MAITEN A TINEO | LUIS ANTONIO TORRES JARAMILLO'</li><li>'YUTRECO | APLICACION FERTILIZANTE VITRAMAC 200 HA | SERVICIOS AGRICOLAS CORPAL SPA'</li><li>'VITRAMAG FUNDO | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                      |
| EXP-7.0  | <ul><li>'aplicac.dron | SERVICIOS AGRICOLAS SCHUCK SPA'</li><li>'GLADIADOR 450 WP X 250 GR | COLUN'</li><li>'GARLON 4 3,79 L | COAGRA S.A.'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| EXP-8.1  | <ul><li>'SEMILLA TREBOL BLANCO KOTUKU X 4 KG | COLUN'</li><li>'SEMILLA TREBOL BLANCO RURU X | COOPERATIVA AGRÍCOLA Y LECHERA DE LA UNIÓN LTDA'</li><li>'SEMILLA BALLICA TAMA CTE X 25 KG | SEMILLA BALLICA TAMA CTE | COOPERATIVA AGRICOLA Y LECHERA DE LA UNION LTDA.'</li></ul>                                                                                                                                                                                                                                                                                                       |
| EXP-8.2  | <ul><li>'SIEMBRA RAP - MAITEN | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'SEMILLA BALLICA PASTURE PACK KABUL 25 KG | ^ ! Cuota Vencimiento Monto ! Cuota Vencimiento Monto ! Cuota Vencimiento Monto ! ^ !==============================!==============================!==============================! ^ ! CU01 03-04-2026 663.980 ! CU02 03-05-2026 663.980 ! CU03 02-06-2026 663.980 ! ^ ! CU04 02-07-2026 663.980 ! CU05 01-08-2026 663.979 | COAGRA S.A.'</li><li>'SEMILLA BALLICA FORGE AGR X | COOPERATIVA AGRÍCOLA Y LECHERA DE LA UNIÓN LTDA'</li></ul> |
| EXP-8.3  | <ul><li>'SEMILLA BALLICA DAIRY PRIME DES X | COOPERATIVA AGRÍCOLA Y LECHERA DE LA UNIÓN LTDA'</li><li>'INCORPORADOR CATROS | GUILLERMO ENRIQUE RIEDEL MARTINEZ'</li><li>'SIEMBRA REPOBLAMIENTO | SIEMBRA REPOBLAMIENTO'</li></ul>                                                                                                                                                                                                                                                                                                                                                       |
| EXP-8.4  | <ul><li>'RAPS TORDON 21K - | BRAMADERO | PRESTACIONES DE SERVICIOS AGRICOLAS EL SIERVO LIMITADA'</li><li>'Siembra Papas Maiten | HSV SPA'</li><li>'SEMILLA PASTO PRADO MZ MNQHUE PLS X 5 KG | COLUN'</li></ul>                                                                                                                                                                                                                                                                                                                                                                          |
| EXP-9.1  | <ul><li>'Demanda maxima suministrada 40.44 x $ 18117.161226508408 | COOPERATIVA RURAL ELECT.R.BUENO LTDA.'</li><li>'Demanda maxima suministrada 38.55 x $ 18007.159533073933 | COOPERATIVA RURAL ELECT.R.BUENO LTDA.'</li><li>'Energia Electrica Riego - COOPERATIVA ELECTRICA PAILLACO LTDA | COOPERATIVA ELECTRICA PAILLACO LTDA'</li></ul>                                                                                                                                                                                                                                           |
| EXP-9.2  | <ul><li>'K-L TUBO ALZADOR 40 MM X 800 MM | FACTURA ELECTRONICA COOPERATIVA AGRICOLA Y DE SERVICIOS LTDA'</li><li>'K-L COPLA 40 MM | NOTA DE CREDITO COOPERATIVA AGRICOLA Y DE SERVICIOS LTDA'</li><li>'RIEGO PURINES EN PRADERAS | 39 carradas de purines de 11.000 lts c/u 429.000 lts | SERVICIOS AGRICOLAS CORPAL SPA'</li></ul>                                                                                                                                                                                                                                                     |
| ING-0.1  | <ul><li>'VENTA DE LECHE | 9.663 kg de leche a $ 592,51 Estanque 03076-7, El Maiten Guia entre 1267029 - 1256625 | ANTILLANCA SPA'</li><li>'VENTA DE LECHE | 473.548 kg de leche a $ 414,16 Estanque 21215-6, Yutreco Guias entre 1328394 - 1311274 | ANTILLANCA SPA'</li><li>'VENTA DE LECHE | 415009 kg de leche a $ 452,11 Estanque 21215-6, Yutreco Guias entre 1333836 - 1361824 | ANTILLANCA SPA'</li></ul>                                                                                                                                                                        |
| ING-0.2  | <ul><li>'VENTA DE VACAS | DESDE EL MAITEN FMA 101610652 | ANTILLANCA SPA'</li><li>'VENTA DE VACAS | 25 VACAS NOTA VENTA 22599-A | ANTILLANCA SPA'</li><li>'VENTA DE VACAS | DESDE RAICES FMA 112626628 | ANTILLANCA SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                      |
| ING-0.3  | <ul><li>'VENTA DE VAQUILLAS | 23 VAQUILLAS NV 22599-A | ANTILLANCA SPA'</li><li>'VENTA DE VAQUILLAS | ANTILLANCA SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ING-0.4  | <ul><li>'VENTAS TERNEROS | DESDE EL MAITEN FMA 170004282 | ANTILLANCA SPA'</li><li>'VENTAS TERNEROS | DESDE EL MAITEN FMA 084917582 | ANTILLANCA SPA'</li><li>'VENTAS TERNEROS | DESDE PREDIO RAICES FMA 105103472 | ANTILLANCA SPA'</li></ul>                                                                                                                                                                                                                                                                                                                                          |

## Uses

### Direct Use for Inference

First install the SetFit library:

```bash
pip install setfit
```

Then you can load this model and run inference.

```python
from setfit import SetFitModel

# Download from the 🤗 Hub
model = SetFitModel.from_pretrained("setfit_model_id")
# Run inference
preds = model("MANIJA SOFT TOUCH CUERDA (G69703) | COLUN")
```

<!--
### Downstream Use

*List how someone could finetune this model on their own dataset.*
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Set Metrics
| Training set | Min | Median  | Max |
|:-------------|:----|:--------|:----|
| Word count   | 1   | 11.0426 | 67  |

| Label    | Training Sample Count |
|:---------|:----------------------|
| ADM-1.10 | 13                    |
| ADM-1.2  | 8                     |
| ADM-1.3  | 3                     |
| ADM-1.4  | 9                     |
| ADM-1.5  | 6                     |
| ADM-1.6  | 23                    |
| ADM-1.7  | 42                    |
| ADM-1.8  | 10                    |
| ADM-2.1  | 12                    |
| ADM-2.2  | 4                     |
| ADM-2.3  | 13                    |
| EXP-1.1  | 26                    |
| EXP-10.1 | 22                    |
| EXP-10.2 | 2                     |
| EXP-10.3 | 14                    |
| EXP-10.4 | 7                     |
| EXP-11.1 | 33                    |
| EXP-11.2 | 4                     |
| EXP-11.3 | 15                    |
| EXP-11.4 | 14                    |
| EXP-11.5 | 12                    |
| EXP-12.1 | 22                    |
| EXP-12.2 | 42                    |
| EXP-13.1 | 31                    |
| EXP-13.2 | 17                    |
| EXP-13.3 | 19                    |
| EXP-14.1 | 16                    |
| EXP-14.2 | 49                    |
| EXP-14.3 | 19                    |
| EXP-14.4 | 22                    |
| EXP-15.1 | 2                     |
| EXP-15.2 | 3                     |
| EXP-15.3 | 14                    |
| EXP-15.4 | 9                     |
| EXP-15.5 | 11                    |
| EXP-16.1 | 110                   |
| EXP-16.2 | 28                    |
| EXP-2.1  | 6                     |
| EXP-2.2  | 14                    |
| EXP-2.3  | 16                    |
| EXP-2.4  | 11                    |
| EXP-2.5  | 68                    |
| EXP-2.6  | 95                    |
| EXP-3.1  | 18                    |
| EXP-4.1  | 9                     |
| EXP-4.2  | 22                    |
| EXP-4.3  | 13                    |
| EXP-5.1  | 4                     |
| EXP-5.2  | 9                     |
| EXP-5.3  | 11                    |
| EXP-5.4  | 9                     |
| EXP-5.5  | 4                     |
| EXP-6.1  | 6                     |
| EXP-6.2  | 12                    |
| EXP-6.3  | 3                     |
| EXP-6.4  | 2                     |
| EXP-6.5  | 12                    |
| EXP-7.0  | 46                    |
| EXP-8.1  | 14                    |
| EXP-8.2  | 6                     |
| EXP-8.3  | 4                     |
| EXP-8.4  | 11                    |
| EXP-9.1  | 22                    |
| EXP-9.2  | 26                    |
| ING-0.1  | 38                    |
| ING-0.2  | 12                    |
| ING-0.3  | 2                     |
| ING-0.4  | 37                    |

### Training Hyperparameters
- batch_size: (8, 8)
- num_epochs: (1, 1)
- max_steps: 1500
- sampling_strategy: oversampling
- body_learning_rate: (2e-05, 2e-05)
- head_learning_rate: 0.01
- loss: CosineSimilarityLoss
- distance_metric: cosine_distance
- margin: 0.25
- end_to_end: False
- use_amp: False
- warmup_proportion: 0.1
- l2_weight: 0.01
- seed: 42
- eval_max_steps: -1
- load_best_model_at_end: False

### Training Results
| Epoch  | Step | Training Loss | Validation Loss |
|:------:|:----:|:-------------:|:---------------:|
| 0.0007 | 1    | 0.2664        | -               |
| 0.0067 | 10   | 0.1791        | -               |
| 0.0133 | 20   | 0.1978        | -               |
| 0.02   | 30   | 0.2085        | -               |
| 0.0267 | 40   | 0.1542        | -               |
| 0.0333 | 50   | 0.1887        | -               |
| 0.04   | 60   | 0.1861        | -               |
| 0.0467 | 70   | 0.1565        | -               |
| 0.0533 | 80   | 0.1752        | -               |
| 0.06   | 90   | 0.1657        | -               |
| 0.0667 | 100  | 0.1667        | -               |
| 0.0733 | 110  | 0.1603        | -               |
| 0.08   | 120  | 0.1482        | -               |
| 0.0867 | 130  | 0.1558        | -               |
| 0.0933 | 140  | 0.1468        | -               |
| 0.1    | 150  | 0.1742        | -               |
| 0.1067 | 160  | 0.143         | -               |
| 0.1133 | 170  | 0.1419        | -               |
| 0.12   | 180  | 0.1573        | -               |
| 0.1267 | 190  | 0.1834        | -               |
| 0.1333 | 200  | 0.1655        | -               |
| 0.14   | 210  | 0.1244        | -               |
| 0.1467 | 220  | 0.1527        | -               |
| 0.1533 | 230  | 0.1163        | -               |
| 0.16   | 240  | 0.1412        | -               |
| 0.1667 | 250  | 0.1551        | -               |
| 0.1733 | 260  | 0.0999        | -               |
| 0.18   | 270  | 0.0824        | -               |
| 0.1867 | 280  | 0.1502        | -               |
| 0.1933 | 290  | 0.1474        | -               |
| 0.2    | 300  | 0.124         | -               |
| 0.2067 | 310  | 0.1148        | -               |
| 0.2133 | 320  | 0.1469        | -               |
| 0.22   | 330  | 0.0754        | -               |
| 0.2267 | 340  | 0.0933        | -               |
| 0.2333 | 350  | 0.0923        | -               |
| 0.24   | 360  | 0.1475        | -               |
| 0.2467 | 370  | 0.1474        | -               |
| 0.2533 | 380  | 0.0991        | -               |
| 0.26   | 390  | 0.1105        | -               |
| 0.2667 | 400  | 0.0698        | -               |
| 0.2733 | 410  | 0.0983        | -               |
| 0.28   | 420  | 0.1035        | -               |
| 0.2867 | 430  | 0.1089        | -               |
| 0.2933 | 440  | 0.0841        | -               |
| 0.3    | 450  | 0.0758        | -               |
| 0.3067 | 460  | 0.0902        | -               |
| 0.3133 | 470  | 0.082         | -               |
| 0.32   | 480  | 0.1118        | -               |
| 0.3267 | 490  | 0.0496        | -               |
| 0.3333 | 500  | 0.081         | -               |
| 0.34   | 510  | 0.094         | -               |
| 0.3467 | 520  | 0.1233        | -               |
| 0.3533 | 530  | 0.0873        | -               |
| 0.36   | 540  | 0.1126        | -               |
| 0.3667 | 550  | 0.0724        | -               |
| 0.3733 | 560  | 0.0674        | -               |
| 0.38   | 570  | 0.0897        | -               |
| 0.3867 | 580  | 0.1008        | -               |
| 0.3933 | 590  | 0.0807        | -               |
| 0.4    | 600  | 0.0904        | -               |
| 0.4067 | 610  | 0.0769        | -               |
| 0.4133 | 620  | 0.0889        | -               |
| 0.42   | 630  | 0.0538        | -               |
| 0.4267 | 640  | 0.085         | -               |
| 0.4333 | 650  | 0.1141        | -               |
| 0.44   | 660  | 0.0996        | -               |
| 0.4467 | 670  | 0.082         | -               |
| 0.4533 | 680  | 0.0514        | -               |
| 0.46   | 690  | 0.086         | -               |
| 0.4667 | 700  | 0.0364        | -               |
| 0.4733 | 710  | 0.1119        | -               |
| 0.48   | 720  | 0.0495        | -               |
| 0.4867 | 730  | 0.0584        | -               |
| 0.4933 | 740  | 0.0651        | -               |
| 0.5    | 750  | 0.0759        | -               |
| 0.5067 | 760  | 0.0614        | -               |
| 0.5133 | 770  | 0.0752        | -               |
| 0.52   | 780  | 0.0616        | -               |
| 0.5267 | 790  | 0.0976        | -               |
| 0.5333 | 800  | 0.0598        | -               |
| 0.54   | 810  | 0.0346        | -               |
| 0.5467 | 820  | 0.089         | -               |
| 0.5533 | 830  | 0.0531        | -               |
| 0.56   | 840  | 0.0782        | -               |
| 0.5667 | 850  | 0.051         | -               |
| 0.5733 | 860  | 0.0633        | -               |
| 0.58   | 870  | 0.0626        | -               |
| 0.5867 | 880  | 0.0671        | -               |
| 0.5933 | 890  | 0.0532        | -               |
| 0.6    | 900  | 0.0565        | -               |
| 0.6067 | 910  | 0.1017        | -               |
| 0.6133 | 920  | 0.0746        | -               |
| 0.62   | 930  | 0.0509        | -               |
| 0.6267 | 940  | 0.0492        | -               |
| 0.6333 | 950  | 0.0362        | -               |
| 0.64   | 960  | 0.064         | -               |
| 0.6467 | 970  | 0.0598        | -               |
| 0.6533 | 980  | 0.0601        | -               |
| 0.66   | 990  | 0.0555        | -               |
| 0.6667 | 1000 | 0.0817        | -               |
| 0.6733 | 1010 | 0.0658        | -               |
| 0.68   | 1020 | 0.0729        | -               |
| 0.6867 | 1030 | 0.0631        | -               |
| 0.6933 | 1040 | 0.0632        | -               |
| 0.7    | 1050 | 0.0608        | -               |
| 0.7067 | 1060 | 0.0603        | -               |
| 0.7133 | 1070 | 0.036         | -               |
| 0.72   | 1080 | 0.0556        | -               |
| 0.7267 | 1090 | 0.0877        | -               |
| 0.7333 | 1100 | 0.033         | -               |
| 0.74   | 1110 | 0.046         | -               |
| 0.7467 | 1120 | 0.0522        | -               |
| 0.7533 | 1130 | 0.0682        | -               |
| 0.76   | 1140 | 0.06          | -               |
| 0.7667 | 1150 | 0.0557        | -               |
| 0.7733 | 1160 | 0.0549        | -               |
| 0.78   | 1170 | 0.0411        | -               |
| 0.7867 | 1180 | 0.0627        | -               |
| 0.7933 | 1190 | 0.0693        | -               |
| 0.8    | 1200 | 0.0464        | -               |
| 0.8067 | 1210 | 0.0447        | -               |
| 0.8133 | 1220 | 0.025         | -               |
| 0.82   | 1230 | 0.0518        | -               |
| 0.8267 | 1240 | 0.0349        | -               |
| 0.8333 | 1250 | 0.0199        | -               |
| 0.84   | 1260 | 0.0601        | -               |
| 0.8467 | 1270 | 0.0785        | -               |
| 0.8533 | 1280 | 0.0671        | -               |
| 0.86   | 1290 | 0.0652        | -               |
| 0.8667 | 1300 | 0.0405        | -               |
| 0.8733 | 1310 | 0.0392        | -               |
| 0.88   | 1320 | 0.0428        | -               |
| 0.8867 | 1330 | 0.0213        | -               |
| 0.8933 | 1340 | 0.0461        | -               |
| 0.9    | 1350 | 0.0652        | -               |
| 0.9067 | 1360 | 0.0833        | -               |
| 0.9133 | 1370 | 0.0616        | -               |
| 0.92   | 1380 | 0.0427        | -               |
| 0.9267 | 1390 | 0.0357        | -               |
| 0.9333 | 1400 | 0.0531        | -               |
| 0.94   | 1410 | 0.0467        | -               |
| 0.9467 | 1420 | 0.0479        | -               |
| 0.9533 | 1430 | 0.0444        | -               |
| 0.96   | 1440 | 0.0316        | -               |
| 0.9667 | 1450 | 0.0545        | -               |
| 0.9733 | 1460 | 0.0312        | -               |
| 0.98   | 1470 | 0.0583        | -               |
| 0.9867 | 1480 | 0.0477        | -               |
| 0.9933 | 1490 | 0.0445        | -               |
| 1.0    | 1500 | 0.0295        | -               |

### Framework Versions
- Python: 3.11.15
- SetFit: 1.1.1
- Sentence Transformers: 3.4.1
- Transformers: 4.57.6
- PyTorch: 2.12.1
- Datasets: 3.6.0
- Tokenizers: 0.22.2

## Citation

### BibTeX
```bibtex
@article{https://doi.org/10.48550/arxiv.2209.11055,
    doi = {10.48550/ARXIV.2209.11055},
    url = {https://arxiv.org/abs/2209.11055},
    author = {Tunstall, Lewis and Reimers, Nils and Jo, Unso Eun Seo and Bates, Luke and Korat, Daniel and Wasserblat, Moshe and Pereg, Oren},
    keywords = {Computation and Language (cs.CL), FOS: Computer and information sciences, FOS: Computer and information sciences},
    title = {Efficient Few-Shot Learning Without Prompts},
    publisher = {arXiv},
    year = {2022},
    copyright = {Creative Commons Attribution 4.0 International}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->