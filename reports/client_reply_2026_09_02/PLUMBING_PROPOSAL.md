# Plumbing proposal — client reply 2026-09-02

## Decisions relied on

- **D-030 — client authority outranks row volume.** Cristian's written answer
  that building and farm plumbing all go to `EXP-14.3` is the governing label,
  even where the current model predicts another code.
- **D-041 — do not resolve an open client question in the payload.** A service,
  project, place, generic hardware item, or use-ambiguous material stays in
  review. Construction, bale-making, and the hardware-store default are not
  inferred here.
- **D-042 — backing gold `source`, not `prediction_source`, carries authority.**
  This pass does not use `prediction_source` as evidence. The authority is the
  client's 2026-09-02 answer recorded above.
- **D-043 — surface decisions before acting.** This batch report records the
  load-bearing decisions before the proposal; the non-interactive run does not
  pause for confirmation.
- The hard limits remain intact: no row is added to gold, no unaudited row is
  promoted to gold, and no category is created. `EXP-14.3` already exists as
  categories_id `e083d23e-208f-4dd2-9916-70871a21e113`.

## Source and population

All measurements use only
`backups/supabase_20260902T153305Z/`, taken
2026-09-02T15:33:05Z. Its manifest reports 11,746 `invoice_items` rows and
SHA-256 `4c43c93076f3116d81e6c2f707291c2af98ea67ba1d5e761e96a2ef2af276206`.
The review population is re-derived as:

```text
decision != 'auto_accept' AND final_categories_id IS NULL
= 4,411 lines, CLP 949,052,038
```

Only those 4,411 lines are eligible. Supplier comes from the matching local
`invoices.jsonl` row. No Supabase connection or other external source is used.
Bank suppliers (BICE, Banco de Chile, Santander) and GEA are explicitly outside
this lane and cannot enter the proposal.

## Vocabulary method

The data-first working is preserved in `VOCABULARY.md`. The five highest-volume
hardware/building-material suppliers contribute 1,463 review lines worth
CLP 27,400,346. Their most frequent material signals generated candidates; the
full `item_text` and every populated `description` were then read before a row
could be proposed.

Hardware-store membership is never an inclusion rule. It is only where the
vocabulary search began. A hardware row enters this proposal only when its own
wording names a plumbing material. Conversely, a plumbing material from a
different supplier remains eligible. This keeps Cristian's two answers apart:
there is no default for hardware purchases, but a specifically named plumbing
material has the settled `EXP-14.3` destination.

## Result proposed to `EXP-14.3`

The proposal contains **539 lines worth CLP 6,782,562**. Every row has an
exact, non-empty `evidence` substring copied from that row's `item_text` (or
`description` if needed); in this result every proposed line has usable
`item_text`. No supplier-level default was used.

| Evidence group | Lines | CLP | What the wording establishes |
|---|---:|---:|---|
| Building drainage | 78 | 856,073 | Sanitary PVC, drains/siphons, septic tanks and their install kits, Aquapluv and P25 rain drainage |
| Building fixtures | 28 | 347,031 | Water flexibles, sink/basin/shower taps, mixers, shower fittings and sinks |
| Building PPR | 45 | 120,233 | PPR and thermofusion pipe/fittings |
| Farm pipe | 46 | 808,449 | Pressure PVC, HDPE/PEAD/polyethylene, hydraulic-water PVC and collector pipe |
| Farm-water-specific parts | 36 | 1,132,846 | Tank outlets, water tank, take-off collars, drinker plugs, irrigation emitters/sprinklers and explicitly water filters |
| Threaded/compression fittings | 197 | 807,206 | A fitting name plus a plumbing context such as HI/HE/SO, galvanized, PVC, Plansa, compression or bronze |
| Valves and water taps | 73 | 2,443,370 | Ball, pressure-regulating, vent, vertical check and float valves; gas, air, inflation and machine valves are excluded |
| Explicit water/garden hose | 14 | 195,220 | The line itself says garden or water, or names a connector tied by the data to that garden-hose family |
| Thread sealant | 22 | 72,134 | Teflon thread tape; the one explicitly gas-labelled tape is excluded |
| **Total proposed** | **539** | **6,782,562** | |

For comparison with the three families in the older email, the current nine
groups roll up without overlap as follows:

| Comparable family | Lines | CLP |
|---|---:|---:|
| Building plumbing (drainage + fixtures + PPR) | 151 | 1,323,337 |
| Farm water (pipe + farm-specific + fittings + valves) | 352 | 5,191,871 |
| Explicit water hose and mixed sealant | 36 | 267,354 |
| **Total** | **539** | **6,782,562** |

## Preserved ambiguity

`plumbing_unresolved.jsonl` contains **121 lines worth CLP 3,029,388**. These
are material-like candidates whose wording is insufficient; they are not part
of the apply payload and remain in review.

| Unresolved reason | Lines | CLP |
|---|---:|---:|
| Generic fitting with no named pipe/fluid system | 13 | 114,890 |
| Water-related material/parts bundle that does not name the actual item | 1 | 18,200 |
| Generic clamp with no pipe, hose, machine or job context | 42 | 306,274 |
| Generic hose or hose coupling | 49 | 1,235,249 |
| Pipe-like wording that does not settle plumbing versus refrigeration, machinery or construction | 8 | 1,235,527 |
| Fluid-filter component with no identified system | 2 | 27,463 |
| Possible flexible connector or fixture that does not distinguish water from gas/another use | 6 | 91,785 |
| **Total unresolved** | **121** | **3,029,388** |

This is where the hardware-store answer matters most. For example, a generic
`MANGUERA`, clamp, rapid coupling or unqualified copper pipe is not proposed
merely because a hardware supplier sold it. An explicit `PVC SANITARIO`, PPR,
pressure-PVC fitting or `MANGUERA JARDIN` from the same supplier is proposed
because the material wording itself settles Q2. Supplier type is neither a
positive nor a negative rule.

## Deliberately not changed

The remaining **3,751 review lines worth CLP 939,240,088** are outside the two
plumbing material outputs. They include jobs/services/places rather than
materials, construction and bale-making questions, generic non-plumbing
hardware, and lines with explicit gas, refrigeration, hydraulic-machine,
electrical-conduit or other non-water context. They remain in review; the
script cannot touch them.

The supplier prohibitions were also checked directly in the review population:
**53 bank lines worth CLP 78,308,334** and **207 GEA lines worth
CLP 50,490,949** are outside the proposal. The combined forbidden-supplier
subset is **260 lines worth CLP 128,799,283**. No new category is proposed.

The population accounting is exhaustive and disjoint:

```text
539 proposed + 121 unresolved + 3,751 outside these plumbing sets
= 4,411 review lines

CLP 6,782,562 + CLP 3,029,388 + CLP 939,240,088
= CLP 949,052,038
```

## Difference from the 2026-08-18 hint

The older measurement was 464 lines worth CLP 12,951,958, split 60 building,
178 farm and 226 hose/clamps/mixed. It is not treated as an acceptance target.
Against that hint, this backup-only result is:

| Comparable family | Current | Hint | Difference |
|---|---:|---:|---:|
| Building | 151 | 60 | +91 |
| Farm water | 352 | 178 | +174 |
| Explicit water hose/mixed | 36 | 226 | -190 |
| **Total lines** | **539** | **464** | **+75** |
| **Total CLP** | **6,782,562** | **12,951,958** | **-6,169,396** |

The line-level old set is not present in the sanctioned backup, so a row-by-row
reconciliation would be invented evidence. The differences that can be
demonstrated from the current data and instructions are:

- Building now includes 28 explicitly named fixtures as well as 78 drainage
  and 45 PPR lines; the hint described only sanitary drainage, PPR and
  Aquapluv examples.
- The current farm roll-up contains 197 evidenced threaded/compression fittings
  and 73 valves in addition to 46 pipe and 36 farm-specific lines. It is
  measured on the 2026-09-02 review predicate, not the older row set.
- Generic hose and clamps are no longer silently resolved: 49 hose/coupling
  lines and 42 clamp lines are explicitly unresolved. Only 14 lines that say
  water/garden and 22 unambiguously plumbing thread-sealant lines enter the
  comparable mixed group. That conservative boundary is the main structural
  reason the mixed count is lower.
- Only an aggregate CLP value survives for the hint, so the CLP difference can
  be measured in total but cannot honestly be attributed among its three old
  families.

## Apply script and dry-run proof

`scripts/96_apply_plumbing_agua_purines.py` defaults to a local-only dry run.
It re-reads the proposal, validates every object and exact evidence substring,
matches all item IDs against the fixed backup, verifies they still satisfy the
review predicate, and asserts that the matched count equals the proposal
length. It creates a PostgREST client only after `--apply`; the apply preflight
then requires every live target to exist and still be unresolved before a
scoped `item_id=in.(...)` patch can run.

Command run (without `--apply`):

```text
python3 scripts/96_apply_plumbing_agua_purines.py
```

Complete output:

```text
DRY RUN — local backup only; no network; nothing written
proposal rows: 539
matched rows:  539
amount:        CLP 6,782,562
set on every listed item_id:
{"decision": "auto_accept", "final_categories_id": "e083d23e-208f-4dd2-9916-70871a21e113", "final_code": "EXP-14.3", "needs_review": false, "prediction_source": "client_rule", "reviewed": true}
change set:
CHANGE 006412ac-d0a7-4cf9-8305-1b3cc24a26e4 | CLP 4,161 | item_text="Ñ-3 METRO PVC SANITARIO GRIS 40 MM -@"
CHANGE 041f7a1e-e1a3-45f2-bb0f-fcbb309f8650 | CLP 1,720 | item_text="Ñ-CODO SANITARIO GRIS 75MM -@"
CHANGE 07fd61f0-818d-403a-ad0b-6f2331f4044d | CLP 4,620 | item_text="AQ-ABRAZADERA AQUAPLUV TIGRE -@"
CHANGE 09c9ad29-c785-41a7-b2c2-9dea43e0a409 | CLP 2,842 | item_text="CODO PVC-S 75MMX45O GR CEM CUN"
CHANGE 0e1a5bf7-fc5c-4502-b41b-d340ed4ed9e4 | CLP 820 | item_text="CODO 87.5X50MM SANITARIO GRIS VNT"
CHANGE 111e989e-367e-42bb-93aa-84939e6009f1 | CLP 600 | item_text="CODO PVC-SANIT.GRIS 40MM X 90§"
CHANGE 180dd146-e0ba-43ea-a0c8-abca6b98b4c1 | CLP 8,311 | item_text="JUEGO DE FITTING PARA SANITARIO KB-AB107 FAS-@"
CHANGE 195e3708-3f47-42ff-a968-fbbddd200ebd | CLP 4,137 | item_text="Ñ-TIRA PVC SANITARIO GRIS 40 MM X 6MTS -@"
CHANGE 19f3feca-cd2a-4631-9fb3-f400920fb0fa | CLP 2,620 | item_text="AQ-SOPORTE CANAL AQUAPLUV TIGRE -@"
CHANGE 1b637feb-19f1-4986-b421-812d49d20616 | CLP 2,790 | item_text="TUBO PVC SAN REFORZADO 50X1000 GR SC"
CHANGE 1d48463b-e4bd-4ac5-8be0-553201cd3445 | CLP 31,929 | item_text="CODO HEMBRA/HEMBRA ARENA P25 - VINILIT 45º"
CHANGE 20bdf788-b0d7-4ddc-b282-e20151341ced | CLP 43,374 | item_text="Ñ-TIRA PVC SANITARIO GRIS 75 MM X 6MTS -@"
CHANGE 27b4046f-b6e9-4876-83f4-b042a13d67a7 | CLP 824 | item_text="AQ-TAPA DERECHA AQUAPLUV TIGRE -@"
CHANGE 3e26c764-45a6-42f4-85fd-eb73115c4d8f | CLP 105,070 | item_text="FOSA SEPTICA 1250 LT.POLIETILENO HORIZONTAL \"OFERTA\""
CHANGE 3f10a561-0713-45a5-8608-cecdec7fc451 | CLP 5,008 | item_text="Ñ-TEE REGISTRO 110 PVC-SANITARIO HOFFENS -@"
CHANGE 4122a670-8239-4c0a-bf30-76450154333c | CLP 1,848 | item_text="AQ-ABRAZADERA AQUAPLUV TIGRE -@"
CHANGE 45bba5b1-219b-4e45-ad46-d8ad8dd0a0e5 | CLP 2,647 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 40MM \"OFERTA\""
CHANGE 4b1ed823-03b2-4f3c-bcc4-a5be31bc9595 | CLP 29,475 | item_text="AQ-SOPORTE CANAL AQUAPLUV TIGRE -@"
CHANGE 4d0fca27-ecdc-485c-9938-5f899ef8247e | CLP 3,904 | item_text="DESAGUE TINA/RECEPTACULO E70 X S1,1/4\" 9052642 VINIL"
CHANGE 4d35e294-6a61-4e94-9248-1bec5ee9b901 | CLP 2,148 | item_text="SIFON LAVATORIO REGIO C/CODO STD 1,1/4X32 HOFFENS"
CHANGE 511f3e3d-b2c8-4286-9d71-5be7dea7dca5 | CLP 159,650 | item_text="KIT INSTALACION FOSA SEPTICA 1200 LTS"
CHANGE 52b1ce0c-4607-429a-9657-370e2cc1ba5e | CLP 194 | item_text="COPLA PVC SANITARIO 40 MM"
CHANGE 5723d4a1-5653-4da3-a899-6793049af94f | CLP 1,166 | item_text="TAPA TUBERIA SANIT.GRIS 110MM."
CHANGE 5867a6ff-4cb4-43e7-8402-ca5cad998e1a | CLP 450 | item_text="CODO PVC-SANIT.GRIS 40MM X 90§"
CHANGE 68584c09-a7a1-4dcc-b2c3-f57428aecc0b | CLP 2,686 | item_text="SIFON LAVATORIO REGIO 1 1 4 X 40MM HOFFENS 20018 -@"
CHANGE 71941dba-49d5-4d96-9d1c-5f559552c05f | CLP 6,468 | item_text="AQ-GOMA SELLO AQUAPLUV TIGRE -@"
CHANGE 7810a196-ea2b-4eb7-b129-2e5fbd32ca7f | CLP 1,274 | item_text="TAPA CANALETA P25 BLANCO UNIV"
CHANGE 790cf123-410e-4929-bb5d-14414fc1330b | CLP 4,168 | item_text="AQ-TEE BAJADA AQUAPLUV TIGRE -@"
CHANGE 7da280d9-c164-4db5-946f-ea57d8b3b37f | CLP 2,504 | item_text="Ñ-TEE REGISTRO 110 PVC-SANITARIO HOFFENS -@"
CHANGE 825fb372-ea28-40c1-8ac8-765a0e9ea3a9 | CLP 1,183 | item_text="REDUC.PVC-SANIT.GRIS 110 X 50MM."
CHANGE 85527574-1a52-4a59-a0dd-254720579d8d | CLP 2,163 | item_text="SIFON LOA S/C ENTRADA 1 1/2 Y 1 1/4 - HOFFENS"
CHANGE 8811ba17-6ba7-41b4-a9b7-67075f01f5b1 | CLP 3,353 | item_text="SIFON LOA S/R ENTR 11/2 - 11/4"
CHANGE 89fc5cb6-8c8f-4f9f-a5f5-ac42ecce195f | CLP 6,048 | item_text="AQ-CURVA 60 AQUAPLUV MARRON TIGRE -@"
CHANGE 8b020d1c-3a13-4622-ab19-1cd0c09a84b4 | CLP 657 | item_text="Ñ-Y SANITARIA GRIS 40 X 40 -@"
CHANGE 9083c3fd-d6ea-41bd-bb10-2a353bdeabc2 | CLP 824 | item_text="AQ-TAPA IZQUIERDA AQUAPLUV TIGRE -@"
CHANGE 90d89f20-d932-4d78-9c26-5131957a142c | CLP 1,549 | item_text="CODO PVC-SANIT.GRIS 40MM X 90§"
CHANGE 90e84097-37de-4c55-ac2a-fd6287c2e713 | CLP 3,900 | item_text="SIFON LOA S/C.TRANS.1.1/2"
CHANGE 9a26bf28-a8e1-42e9-9e25-6972c32efd2d | CLP 5,168 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 75MM \"OFERTA\""
CHANGE 9d976f5c-1a3d-4eaf-9040-5fd63002bb56 | CLP 8,350 | item_text="TAPA CANALETA UNIVERSAL ARENA P25 - VINILIT"
CHANGE 9e9114ae-edd1-446c-b9a3-ee0d39a52984 | CLP 870 | item_text="CODO PVC-SANIT.GRIS 110MM X 45§"
CHANGE 9ed0e5b9-9839-4f8b-b2c0-e45a2df74b65 | CLP 726 | item_text="Ñ-ABRAZADERA SANITARIA OMEGA 40MM -@"
CHANGE 9f761753-c678-41eb-b661-2175bdf30842 | CLP 9,648 | item_text="CODO HEMBRA/HEMBRA ARENA P25 -VINILIT 87.5º"
CHANGE a5793a1d-dcd7-48c5-b580-e8621b13cf59 | CLP 11,133 | item_text="ABRAZADERA TUBO BAJADA ARENA P25 - VINILIT 80 MM"
CHANGE a59ab727-d2dc-43da-a36a-317f6c7a374a | CLP 3,597 | item_text="Ñ-TIRA PVC SANITARIO GRIS 40 MM X 6MTS -@"
CHANGE aa68674d-30c9-4f09-a695-cb5c879ddca1 | CLP 10,067 | item_text="JUEGO DE FITTING PARA SANITARIO KB-AB107 FAS-@"
CHANGE aaddec2c-911c-481b-b617-f83fae37eb06 | CLP 4,948 | item_text="Ñ-CURVA SANITARIA GRIS 75 X 45 -@"
CHANGE aaf9a293-24b7-4b0c-81e9-f2a6c35ba044 | CLP 1,008 | item_text="Ñ-CODO SANITARIO GRIS 40MM -@"
CHANGE ac84b69a-5548-4fc7-98d3-d44a1156e423 | CLP 2,168 | item_text="SIFON LAVATORIO REGIO 1 1 4 X 40MM HOFFENS 20018 -@"
CHANGE af40b8ac-774b-4527-b41b-3e4b30ec9e75 | CLP 2,069 | item_text="Ñ-TIRA PVC SANITARIO GRIS 40 MM X 6MTS -@"
CHANGE b14ba140-a172-40d3-b043-30fb471ad799 | CLP 1,828 | item_text="VEE PVC-SANIT.GRIS 110MM."
CHANGE b22fcaac-494c-4314-88d1-0141ee06993d | CLP 772 | item_text="Ñ-CURVA SANITARIA GRIS 40 X 45 -@"
CHANGE b68c8aca-f02a-48c3-8df7-e5c4fda3ec84 | CLP 3,008 | item_text="SIFON LAVAPLATOS LOA HOFFENS S/CURVA -@"
CHANGE b68fd2d2-77c0-4343-b1d4-87d2785f42a2 | CLP 3,008 | item_text="SIFON LAVAPLATOS LOA HOFFENS S/CURVA -@"
CHANGE b8842627-28ef-48cb-b3a0-16855ed3a96b | CLP 74,727 | item_text="AQ-CANALETA X 4MT AQUAPLUV TIGRE -@"
CHANGE bac68ea2-6cd7-4cab-8058-86f37fb3fd28 | CLP 3,479 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 50MM \"OFERTA\""
CHANGE bb63ac21-47c3-4b1b-9e65-2e6148e5f0df | CLP 1,832 | item_text="AQ-COPLA UNION CANAL AQUAPLUV 125MM TIGRE -@"
CHANGE bb9c5948-948b-4eec-845c-7aa386911205 | CLP 462 | item_text="AQ-TAPA IZQUIERDA AQUAPLUV TIGRE -@"
CHANGE bd4b2fb2-2d37-4af9-9c9b-e65f3badb6e5 | CLP 880 | item_text="CODO 87.5X75MM SANITARIO GRIS VNT"
CHANGE be94bfb2-b771-4e49-99f8-ad745de23d03 | CLP 14,874 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 110MM NO CERTIFICADA"
CHANGE bea21332-d7c2-4bfa-8d25-fc20fb54964c | CLP 2,218 | item_text="CODO PVC-SANIT.GRIS 110MM X 90§"
CHANGE c3c52925-5b8b-495b-9335-c127fe546e41 | CLP 4,948 | item_text="UNION CANALETA ARENA P25- VINILIT"
CHANGE c43703e2-645e-4bd9-b70b-e086612d960a | CLP 2,084 | item_text="AQ-TEE BAJADA AQUAPLUV TIGRE -@"
CHANGE ca2d18be-8cec-41bd-9586-87e3b8d4ae9d | CLP 2,647 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 40MM \"OFERTA\""
CHANGE cd566204-c6bf-4f75-bbcf-1b860c2a6cab | CLP 14,656 | item_text="AQ-COPLA UNION CANAL AQUAPLUV 125MM TIGRE -@"
CHANGE cf111851-24d9-4782-b210-9bf0fa7decf2 | CLP 8,303 | item_text="AQ-CANALETA X 4MT AQUAPLUV TIGRE -@"
CHANGE d2bb7eef-553c-4aac-b578-652585171bb4 | CLP 772 | item_text="Ñ-CURVA SANITARIA GRIS 40 X 45 -@"
CHANGE d41f655a-0572-4652-a4f5-c0f0435c61c4 | CLP 77,540 | item_text="TUBO DRENAJE FLEXADREN 100 MM PETROFLEX"
CHANGE d5c3af59-81ab-494f-b8c9-b8e54d9748a7 | CLP 4,101 | item_text="DESAGUE LAVATORIO 1,1/4\" CROMADO 041006005 (S/COLA) T"
CHANGE e0e98523-de9d-4284-8644-6642f5443e79 | CLP 504 | item_text="Ñ-CODO SANITARIO GRIS 40MM -@"
CHANGE e13b41de-3c89-4698-b429-96b6a15a8031 | CLP 42,057 | item_text="CANALETA PVC ARENA P25 X 4 MTS VINILIT"
CHANGE e3d6d20e-bbd1-43d7-bbb3-d923da6a7f83 | CLP 10,080 | item_text="AQ-CURVA 60 AQUAPLUV MARRON TIGRE -@"
CHANGE e5800246-32f8-4913-8fd3-ac5aa68c1fab | CLP 2,118 | item_text="CODO PVC-SANIT.GRIS 110MM X 90§"
CHANGE e622227a-63c5-41ae-bbad-0266185ec380 | CLP 26,118 | item_text="* MT.X TIRA PVC-SANITARIO GRIS 110MM CERTIFICADA CESM"
CHANGE ef19625b-ceb6-4b8e-952d-b56e9125c73e | CLP 522 | item_text="Ñ-CODO SANITARIO GRIS 40MM -@"
CHANGE f5bda5ae-1106-4b27-87bb-e703f0746247 | CLP 992 | item_text="AQ-TAPA DERECHA AQUAPLUV TIGRE -@"
CHANGE f74cec10-6a78-4568-ae33-77dbfd794895 | CLP 1,765 | item_text="AQ-GOMA SELLO AQUAPLUV TIGRE -@"
CHANGE f983dd3e-93ff-4977-ad9f-0bee985e5c89 | CLP 1,305 | item_text="Ñ-CODO SANITARIO GRIS 40MM -@"
CHANGE f9db9ae1-c08d-4632-9107-c64dd195c507 | CLP 31,636 | item_text="TUBO BAJADA ARENA P25 - VINILIT 3 MTS"
CHANGE 16b4166a-b862-44b6-b928-9cb39aff3e17 | CLP 25,194 | item_text="COMBINACION LAVAPLATOS TIPO V BOGEN NEGRO MATE (20BO1"
CHANGE 190013ab-7811-4a90-bb40-e466cb29892a | CLP 4,233 | item_text="JUEGO DUCHA FREIBURG TAUMM 020100302 -@"
CHANGE 1d6d6d3d-5feb-415e-918d-0308d31a3c4b | CLP 5,253 | item_text="FLEXIBLE CALEFONT 1/2HI X 1/2HI X 25CM 051033211 TAUM"
CHANGE 1f5abcd6-64a9-4322-b1d4-4c76552eea91 | CLP 1,328 | item_text="FLEXIBLE AGUA HI-HI 40 CM-LINEAS VERDES-H-FULL"
CHANGE 2a917af1-3856-4aa8-8346-5b713546ba31 | CLP 8,387 | item_text="SET DUCHA TELEF. MANGO CROMO 3 LL-102 FAS -@"
CHANGE 2c65ea71-c996-4b85-a444-2ab41b5ae241 | CLP 19,319 | item_text="LAVAPLATO 100X50 IZQ 0,5MM 190502502 CONSTRUCTORA TAU"
CHANGE 38ddf02e-5caa-4cb6-89cd-36dd9006fdd5 | CLP 17,042 | item_text="MONOMANDO LAVATORIO GALIA PLUS MCLGA-1 FAS -@"
CHANGE 3e0c75d4-4871-41d5-831e-a0c8cf4f41c6 | CLP 12,336 | item_text="MONOMANDO LAVATORIO AUSTIN (20AS5003400) PLUMBER"
CHANGE 447836cd-1562-44a5-8c23-3b992a4c7f7a | CLP 7,229 | item_text="LLAVE LAVAMANOS 1001 AQUAKIT J1001 UNIDAD -@"
CHANGE 4486aee3-bbad-43d9-ace3-6cafc1707343 | CLP 5,630 | item_text="MANGO DUCHA TELEFONO CROMADO 3 FUN AIR SAFETY TEL-7 FAS -@"
CHANGE 5392a451-ec7d-4b2a-8c9a-db3621560b86 | CLP 24,277 | item_text="COMBINACION LAVAPLATOS CC7-7001 FAS -@"
CHANGE 6f16ae69-9e5b-45cc-9851-34b52bea0ee4 | CLP 3,732 | item_text="FLEXIBLE AGUA 30CM HI HE 1 2 INOXCROM -@"
CHANGE 7882bc7b-6786-4139-b8f4-f69f7b5aae30 | CLP 28,400 | item_text="LLAVE DUCHA"
CHANGE 9800c35b-b271-4c5b-9efb-14d69cf860e7 | CLP 23,101 | item_text="RECEPTACULO DUCHA 70 X 70"
CHANGE a0e87789-accb-4d0c-80b8-f42f562308d7 | CLP 18,200 | item_text="MONOM.LAVAPL.VERT.INOX"
CHANGE aa136796-7742-480d-88be-5bc990b9d7c7 | CLP 29,689 | item_text="MONOMANDO LAVAPLATO OMEGA PLUS C/JOTA MCPOP FAS"
CHANGE accf8c6a-eb43-4678-8afb-362cde187118 | CLP 3,266 | item_text="LLAVE ANGULAR 1 2 X 3 4 AQUAKIT LAN34B -@"
CHANGE ae3eb6ac-7aaa-4f1e-abd8-3fa5276ebecb | CLP 2,353 | item_text="KIT LLAVE ANGULAR 1 2 CON FLEXIBLE ACERO INOX 25CM HOFFENS-@"
CHANGE c3a0c353-3ff3-4c6f-90f2-d44362db8f26 | CLP 8,047 | item_text="JUEGO DUCHA EUROSPRAY CROMO - DUSCHY"
CHANGE c3cf9a43-fbf7-4cfb-b515-17dd835545bd | CLP 28,370 | item_text="MONOMANDO DUCHA DOMENICA TAUMM -@"
CHANGE ecf7fc9e-fbf7-4487-8258-afa00e2542ab | CLP 22,127 | item_text="MONOMANDO TINA CLE-M302 GRILEF"
CHANGE f4af71a3-35fc-46cb-a391-72797feecfa5 | CLP 3,185 | item_text="LLAVE ANGULAR C/FLEX. 1/2HI X 15/16HI 30CM HOFFENS"
CHANGE f57bf0b5-d9a9-48de-a313-fda693545212 | CLP 19,798 | item_text="LAVAPLATO 0.80 X 0.50 MT 1C/1E DER.P/MONOBLOCK"
CHANGE f8de4900-3946-418c-adbc-ee9280bf3b65 | CLP 2,176 | item_text="LLAVE ANGULAR 1/2\" HE-HE 070100320 TAUMM"
CHANGE f989fa70-a2ad-4cef-a879-d772b78623a2 | CLP 1,328 | item_text="FLEXIBLE AGUA 1 2 X 1 2 HI-HI 40CM YTS F40HI-@"
CHANGE fa61e33e-e7dc-4ede-b5ae-0e589be2f033 | CLP 3,732 | item_text="FLEXIBLE AGUA 1 2 X 1 2 HI-HI 30CM YTS F30HI-@"
CHANGE fbb46b82-6cb6-4a04-89ce-3a8635ada7a4 | CLP 8,131 | item_text="MONOMANDO LAVAPLATO VERT. PLUMBER CINCINNATI MOSAICO 20CI5603000"
CHANGE ffc22146-dd8e-4883-841e-62adfd7dc8ed | CLP 11,168 | item_text="MONOMANDO DUCHA CINCINNATI (20CI5303000) PLUMBER"
CHANGE 02bc121c-7b05-4cd4-9830-5e8fe6aa4fb7 | CLP 1,597 | item_text="ABRAZADERA TERMOFUSION AUTOLOCK 20MM"
CHANGE 09e525fb-e8e4-414e-a616-e55518757749 | CLP 399 | item_text="TEE TERMOFUSION 20MM"
CHANGE 0de13cb3-763c-4629-9b9e-65ef7ade9229 | CLP 580 | item_text="FU-CODO 20MM PPR -@"
CHANGE 13506ca4-87e9-4134-a5f3-cd29aead7e71 | CLP 188 | item_text="COPLA FUSION PPR 20 MM CUN14C"
CHANGE 26806dc5-858b-44ef-81da-2daa0cd45b1e | CLP 12,555 | item_text="FU-TUBERIA FUSION 25MM O PPR -@"
CHANGE 29360f01-eb59-421c-8317-afea1faf459b | CLP 5,748 | item_text="TUBO TERMOFUSION PN 10 20MM X 6 MT"
CHANGE 37baf82a-c97c-4c47-80ea-a62817ec3710 | CLP 3,073 | item_text="FU-TUBERIA FUSION 20MM O PPR -@"
CHANGE 3a0ef7b6-8318-4ffd-8f0c-e4d4210a6e21 | CLP 499 | item_text="TEE TERMOFUSION 20MM"
CHANGE 3d3ab709-7c3c-4ac9-a88f-ea9ad2cfa689 | CLP 2,655 | item_text="CODO SO HI P/TERMOFUSION 20 X 1/2 X 90"
CHANGE 45408a02-8072-4c6c-b595-8b2e54a617c3 | CLP 725 | item_text="FU-CODO 20MM PPR -@"
CHANGE 4cd39cea-8776-450c-8f20-88709d91ebb8 | CLP 672 | item_text="CODO TERMOFUSION 20MM X 90"
CHANGE 4e248dcc-4623-478a-a0d5-301757f4e1cb | CLP 10,740 | item_text="VALVULA BOLA SO SO 25MM CUERPO METALICO TERMOFUSION"
CHANGE 536812bc-4b12-4f2e-a3b4-2e1efd2cf51f | CLP 2,672 | item_text="FU-TUBERIA FUSION 20MM O PPR -@"
CHANGE 5768c40f-cf37-49fb-873f-e1b93ae733e4 | CLP 3,073 | item_text="FU-TUBERIA FUSION 20MM O PPR -@"
CHANGE 588b9ada-2172-4b65-9457-75c9efe0bc0e | CLP 100 | item_text="TEE TERMOFUSION 20MM"
CHANGE 5e8d1989-722c-41f1-81d6-b12755aa5a8b | CLP 268 | item_text="FU-TEE 20MM PPR -@"
CHANGE 5edcb987-53f4-4c32-be4b-03005704ce90 | CLP 16,588 | item_text="TUBO TERMOFUSION PN 20 20MM X 6 MT"
CHANGE 626fef0b-d62a-4c2f-a39a-920589faa77f | CLP 2,727 | item_text="ADAPTADOR SO HE P/TERMOFUSION 20 X 1/2"
CHANGE 64d6e835-9c38-4468-98b3-08dff84a62f3 | CLP 976 | item_text="FU-CODO 32MM PPR -@"
CHANGE 66cae1ab-78f3-4099-ad92-f8dff1521c7d | CLP 504 | item_text="FU-CODO 20MM PPR -@"
CHANGE 68667f6f-7d14-4670-8d75-ec3c065f4a67 | CLP 3,073 | item_text="FU-TUBERIA FUSION 20MM O PPR -@"
CHANGE 6c069bee-f314-4aa8-a3e3-8b7d46d2518f | CLP 798 | item_text="FU-TERMINAL HI 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE 6d18be88-e755-42d3-b237-f60577514286 | CLP 13,825 | item_text="TUBO TERMOFUSION PN 20 20MM X 6 MT"
CHANGE 791b597c-23fe-4ce1-9129-6a45ad3ca403 | CLP 1,916 | item_text="ABRAZADERA TERMOFUSION AUTOLOCK 20MM"
CHANGE 7fa49dd4-0298-456b-ac19-7e7d38a7ba14 | CLP 870 | item_text="FU-CODO 20MM PPR -@"
CHANGE 85212a9d-01fb-428b-a56e-9c0d38c40897 | CLP 672 | item_text="CODO TERMOFUSION 20MM X 90"
CHANGE 85cb5a72-956e-4faa-b8b3-d3c0808b6cfe | CLP 1,836 | item_text="FU-TERMINAL HI 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE 87a2f6f1-756b-40d9-8cf0-4f93fc3c93a1 | CLP 277 | item_text="TAPON PPR 20 MM CUN14C"
CHANGE 8e52acc4-9b5b-4a1b-8a36-ed05cd90b2bb | CLP 370 | item_text="FU-COPLA 32 MM PPR -@"
CHANGE 8eb04de4-eceb-41ff-bbaf-1819908682fb | CLP 1,237 | item_text="FU-TERMINAL HE 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE 922cfbb7-ad5d-4bb0-9a70-227a66699e85 | CLP 134 | item_text="CODO TERMOFUSION 20MM X 90"
CHANGE 9544db6b-1383-4f5b-8169-fbab9491d83a | CLP 1,896 | item_text="FU-TERMINAL HI 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE 96201e2f-3b7f-4c29-8574-b7b5053f11f2 | CLP 2,668 | item_text="FU-TERMINAL HE 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE 9f539822-722a-4fc6-8cad-411a936ffac2 | CLP 2,016 | item_text="FU-TERMINAL HE 1 2 X 25MM METALICO PEGAR PPR -@"
CHANGE 9fb5f98d-e4e8-47ff-9b33-11e3d0f54cff | CLP 3,383 | item_text="UNION AMERICANA PPR 20 MM CUN1"
CHANGE a480b051-a4de-4d9f-90e6-e5f675c5a0d1 | CLP 1,312 | item_text="FU-TEE 32MM PPR -@"
CHANGE ae6636b2-a1f1-4d9f-9638-a1b8c4389bd9 | CLP 1,160 | item_text="FU-TERMINAL HE 1 2 X 20MM METALICO PEGAR PPR -@"
CHANGE b20acdd5-0781-4cf0-8b12-24d2175e55f1 | CLP 481 | item_text="UNION AMER TERMOFUSION SO SO 20MM"
CHANGE c18b0b05-e35c-4474-b513-45bcafd78246 | CLP 8,017 | item_text="TUBO TERMOFUSION PN 20 20MM X 6 MT"
CHANGE d025213b-0b1d-4bd9-9c88-de1510db9e2f | CLP 4,120 | item_text="FU-TERMINAL HI 1 2 X 25 MM METALICO PEGAR PPR -@"
CHANGE d14d60c0-312c-48f3-97cb-483dd71a27a5 | CLP 220 | item_text="TAPON HE P/TERMOFUSION 1/2"
CHANGE db7aa883-5aa5-4bba-a1d3-ac90ecf3e14c | CLP 1,311 | item_text="ADAPTADOR SO HI P/TERMOFUSION 20 X 1/2"
CHANGE edec5b0e-1e2d-43d9-99c4-de68b31790fc | CLP 1,445 | item_text="ADAPTADOR SO HI P/TERMOFUSION 20 X 1/2"
CHANGE ee1612fa-ace8-4e4d-9d72-2f30110010e0 | CLP 136 | item_text="COPLA SO SO P/TERMOFUSION 20MM"
CHANGE fd2c52e6-af7b-4484-b0cf-dd8392a4f973 | CLP 721 | item_text="UNION AMER TERMOFUSION SO SO 20MM"
CHANGE 0dd77c5c-d5a2-4070-b488-e2cd9db61b3c | CLP 3,652 | item_text="HDPE-TEE 25MM -@"
CHANGE 0f685827-62bf-491b-a89e-095848d50242 | CLP 1,166 | item_text="COPLA PVC-H CEM 63MM."
CHANGE 13505fff-67cc-4136-92dd-5459a51e9821 | CLP 82,185 | item_text="TIRA TUBO COLECTOR 315 MM X 6MTS -@"
CHANGE 18f36673-6673-4a8d-ac85-871df9f50f90 | CLP 17,356 | item_text="HDPE-TEE COMPRESION 63MM -@"
CHANGE 196ac042-a77a-4e97-a0d7-60e89e7d5990 | CLP 27,363 | item_text="TAPON GORRO PVC-H CEM. 110MM."
CHANGE 1cb3140c-88fc-4d8c-aaab-5089ba9214f3 | CLP 2,935 | item_text="ADHESIVO VINILIT 240CC.SECADO LENTO"
CHANGE 2aed60e8-a4c0-4766-944f-cd122a2fdc76 | CLP 20,138 | item_text="CAñERIA COBRE \"M\" 1/2\" AGUA"
CHANGE 2f3873ed-3b24-4ef8-b103-5ae3535f996c | CLP 6,706 | item_text="ADHESIVO PVC LATA SECADO RAPIDO 240CC HOFFENS 50038 -@"
CHANGE 322ad4e5-22f5-4743-9c71-1637ee0da72f | CLP 2,521 | item_text="TAPA GORRO PVC HIDR HI 25X34"
CHANGE 32c3d2b0-2e5e-4f7e-b16b-7e33fb4c9207 | CLP 4,523 | item_text="ADHESIVO PVC \"HOFFENS\" SECADO RAPIDO C/APLICADOR 240CC"
CHANGE 3ced3dfd-6fdc-452b-8bff-60a9a6d274c8 | CLP 9,130 | item_text="HDPE-TEE 25MM -@"
CHANGE 41d83ead-2850-4512-8b76-a6d06082bad1 | CLP 15,075 | item_text="ADHESIVO PVC RIEGO 20MM - 140MM SECADO RAPIDO VINILIT-@"
CHANGE 44de2735-dcac-4cc0-a791-e01d4dbfbf62 | CLP 2,513 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE 5cbb558f-6e90-4194-97e0-8d936a13c6fa | CLP 80,400 | item_text="Tubería LLDPE 32mm PN4 Rollo 100 Mts"
CHANGE 5ec5e20c-8ce2-4585-bd4b-12020c0fc93b | CLP 14,450 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE 65d15b20-468b-4ef3-b526-50360471065a | CLP 200 | item_text="TEE CEM PVC PRESION 25 MM"
CHANGE 67e1dedb-1cf1-4772-b62a-964d53d9beba | CLP 150 | item_text="CODO CEM PVC PRESION 90º 25 MM"
CHANGE 6d932c24-7af8-49f0-8cbd-4ed7fc1936cf | CLP 2,513 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE 6db64031-b9e1-48cc-8617-1d345cc7d14b | CLP 2,689 | item_text="TAPA TORNILLO PVC HIDR HE 34"
CHANGE 7a3bb91a-7fb7-4b68-9eab-b0fe49519ad7 | CLP 32,756 | item_text="TIRA TUBO COLECTOR 200 MM X 6MTS -@"
CHANGE 7f1a132f-6e9e-4024-9077-9f903250963e | CLP 139,141 | item_text="TIRA TUBO COLECTOR 400 MM X 6MTS -@"
CHANGE 7f56047c-bbbc-4712-87fe-3d2f1ec6d2ee | CLP 2,200 | item_text="TUBERIA CLASE 16 20MM X 1MT PRESION VNT"
CHANGE 87660952-a526-4d94-956d-dadfdf39a172 | CLP 7,912 | item_text="CODO PVC-H CEM 110MM X 90§"
CHANGE 8cf094db-2c67-40c2-9f9b-1b77f3be90f5 | CLP 20,138 | item_text="CAñERIA COBRE \"M\" 1/2\" AGUA"
CHANGE 95e2013f-bada-49ca-beea-28a3330fd59c | CLP 1,352 | item_text="ADHESIVO PVC LATA SECADO RAPIDO 60CC HOFFENS 51647 @"
CHANGE 975937d8-4103-4fc6-bcd0-ff676b0e6fed | CLP 9,388 | item_text="MT. CANERIA POLIETILENO 1/2\" TIGRE"
CHANGE 9be82f17-5d7f-4921-a80f-efdc6476ee46 | CLP 1,591 | item_text="TUBO PVC PRESION C/16 20 MM"
CHANGE 9e1c391a-5495-451a-a3a3-a201bc12be5a | CLP 17,340 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE a2d7154f-0f8f-4187-b593-b71323f1660d | CLP 11,693 | item_text="HDPE-TEE COMPRESION 63MM -@"
CHANGE adfe5ba3-6a62-4430-a5c5-a35472ffa1e1 | CLP 52,129 | item_text="TEE HDPE 50MM"
CHANGE b308d6f1-21fb-4aa1-b87f-ccdd0b7f254a | CLP 25,130 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE b466e9d5-4167-48e6-98dd-e3ee40e46815 | CLP 37,730 | item_text="HDPE-TEE COMPRESION 63MM -@"
CHANGE b5ddf7f0-8de3-41ae-94b2-4f1e60d8fb80 | CLP 8,098 | item_text="ADHESIVO PVC TRADICIONAL 240CC VINILIT-@"
CHANGE b9ebf1d7-9658-4c4f-a8b9-7a6776e39fe9 | CLP 293 | item_text="TAPON GORRO PVC-H CEM. 50MM."
CHANGE ba7634a8-c32f-4771-bba5-2087e458b1e8 | CLP 60 | item_text="BUJE CORTO CEM PVC PRESION 25 X 20 MM"
CHANGE c1c69f98-0b33-40c2-9fd7-971ad1201518 | CLP 50,250 | item_text="HDPE-TEE COMPRESION 50 MM -@"
CHANGE c75e2736-444c-4d79-ac99-c1d798913a0d | CLP 680 | item_text="CODO 90 20MM PRESION VNT"
CHANGE cacc42e3-dcf1-405e-b704-766b9e798405 | CLP 2,513 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE d3d16dd5-c6b1-41a8-a2ff-750d0c6d3438 | CLP 2,199 | item_text="TUBO PVC PRESION C/12,5 25MM"
CHANGE e0b83fb8-8474-4c2c-bd25-f8b1f3b13699 | CLP 30,492 | item_text="ADHESIVO VINILIT 240CC.SECADO RAPIDO"
CHANGE e2f531a2-2691-4e11-8916-c8c63237755f | CLP 32,756 | item_text="TIRA TUBO COLECTOR 200 MM X 6MTS -@"
CHANGE e5866688-7de4-40b9-975d-2e1a9947a3fc | CLP 2,933 | item_text="ADHESIVO VINILIT 240CC.SECADO LENTO"
CHANGE ec73a97d-a8fd-491c-a711-466be3bd1039 | CLP 12,565 | item_text="HDPE-TEE COMPRESION 32MM -@"
CHANGE f3960aa1-9a81-45be-a81d-db60c1373701 | CLP 580 | item_text="CODO CEM PVC PRESION 90º 20 MM"
CHANGE f6c23ed7-cad2-457d-a98a-f7dfcfa84a5e | CLP 3,561 | item_text="ADHESIVO PVC VINILIT C/BROCHA TRADICIONAL 240 CC"
CHANGE fb64660b-b87f-440c-b4ad-b274423f3d13 | CLP 7,304 | item_text="HDPE-TEE 25MM -@"
CHANGE 02eaf94e-48b6-4f51-a7e9-1a6ce9c1b55f | CLP 6,470 | item_text="Conector a Kit Microtubo Hembra Terminal 5022 10 x 8"
CHANGE 05b44127-a441-49a0-8178-869786b5f89b | CLP 35,062 | item_text="VALVULA ACOPLE RAPIDO ASPERSOR 3/4\""
CHANGE 0bcf8db4-6a73-4b2d-b9c3-b0c9c5eabfd5 | CLP 12,611 | item_text="COLLAR ARRANQUE PVC P/PVC 63 X 1\""
CHANGE 12e6fa5b-b21b-418b-87a7-81184c6f7e3f | CLP 21,656 | item_text="Filtro Malla Purificacion Tipo Y 2\" Azud"
CHANGE 18d41a39-d370-4e24-a94a-178d0b1803bb | CLP 17,347 | item_text="FILTRO AGUA PVC NEGRO 2 PULG. PRAKTUS -@"
CHANGE 18d7a1b4-5e3d-4c9b-815f-4a6a752711c0 | CLP 43,250 | item_text="Collarín Arranque 32 x 1/2\" EDR"
CHANGE 1c1afa11-a835-45db-8e68-3c8381bd0331 | CLP 1,229 | item_text="COLLAR ARRANQUE PVC P/PVC 63 X 3/4\""
CHANGE 3f05d9f5-23d3-4277-8715-b702e835fa96 | CLP 2,686 | item_text="-SALIDA ESTANQUE CEM 63 X 2 -@"
CHANGE 54989897-dd8f-487b-9649-0111fac84346 | CLP 4,002 | item_text="COLLARIN POLIPROPILENO 63MMX3 4 -@"
CHANGE 56fa940f-c952-4458-9590-28c1c37da01f | CLP 25,760 | item_text="Collar Arranque Polietileno 40mm x 1\" Hi (CH)"
CHANGE 591fecef-86a3-42ea-8a31-192e0c683b2a | CLP 1,431 | item_text="COLLARIN POLIPROPILENO 50MM X 3 4 -@"
CHANGE 5a10ee5b-2390-4206-a84d-3076266e365e | CLP 10,610 | item_text="COLLAR ARRANQUE PVC P/PVC 50 X 1\""
CHANGE 6406d475-e60a-49f3-a573-dc55919fe470 | CLP 26,865 | item_text="FILTRO AGUA PVC NEGRO 2 PULG. AZUD -@"
CHANGE 70c8bea6-ec05-4897-9b82-6463d1446b9f | CLP 19,425 | item_text="-SALIDA ESTANQUE 110 X 4 -@"
CHANGE 722fa103-1ed6-4e53-b3e7-e3b7a8976d4b | CLP 155,615 | item_text="Cañeria c/Gotero 1.6 L/H 20cm Rollo 550mm"
CHANGE 742c1726-7edb-499e-b9f1-40a112a9f068 | CLP 37,441 | item_text="VALVULA ACOPLE RAPIDO ASPERSOR 1\""
CHANGE 75cb70d4-bcd3-4971-b29a-72f1d8151f0b | CLP 19,425 | item_text="-SALIDA ESTANQUE 110 X 4 -@"
CHANGE 870b0f4d-6334-4019-a6e2-ad1ff165d3c4 | CLP 1,431 | item_text="COLLARIN POLIPROPILENO 63MM X 1 -@"
CHANGE 89b04c0a-92c8-4560-927e-c812be95ece5 | CLP 428,646 | item_text="ESTANQUE AGUA ESTACION. 5000 L WENCO"
CHANGE a16fb3f1-abc1-4182-845d-cd2036803582 | CLP 21,914 | item_text="VALVULA ACOPLE RAPIDO ASPERSOR 3/4\""
CHANGE b0102abb-995b-4196-87df-d56c2ab7de7e | CLP 39,070 | item_text="Kit Microtubo 12mm c/Conectores y Salida HI de ½ ."
CHANGE b4f73bde-a1da-490b-9e51-2c7e42cb87a6 | CLP 27,002 | item_text="ASPERSOR TRUPER ME ASP-11X C/ESTACA MET. 2 SALIDA"
CHANGE bad2b51b-75fb-4528-bbc4-75d2f32efacd | CLP 2,686 | item_text="-SALIDA ESTANQUE CEM 63 X 2 -@"
CHANGE bdf6618d-7191-46aa-8cd2-517d74d87065 | CLP 11,400 | item_text="Collarín Arranque 63 x 1\" Arangül"
CHANGE c8d03e38-a36b-4c6c-a671-2e38662c2408 | CLP 45,288 | item_text="COLLAR ARRANQUE PVC P/PVC 110 X 2\""
CHANGE cfdec01c-0904-485f-8da1-5adc66d74742 | CLP 11,600 | item_text="COLLARIN POLIPROPILENO 50 MM X 1 -@"
CHANGE d444aa95-07d3-4751-af7e-e2fb92bc8c56 | CLP 23,600 | item_text="Collar Arranque Polietileno 50mm x 1\" Hi (SAB)"
CHANGE df27bcce-7d84-41ea-8966-41556fac8b16 | CLP 20,158 | item_text="COLLAR ARRANQUE PVC P/PVC 50 X 1\""
CHANGE df490257-41fe-484d-9e75-fd9abbbeb895 | CLP 7,849 | item_text="COLLAR ARRANQUE PVC P/PVC 50 X 3/4\""
CHANGE e828833a-9c05-498e-86f5-6b30a670f0b5 | CLP 3,018 | item_text="COLLAR ARRANQUE PVC P/PVC 40 X 3/4\""
CHANGE ec5e48f2-3ecb-4f1e-b43c-428122e34187 | CLP 15,740 | item_text="Estaca P/Aspersor Fibra 8mm -120cm"
CHANGE edf4c031-7add-4c0a-9ef1-1998f165b6a8 | CLP 9,828 | item_text="AP TAPON BEBEDEROS -____"
CHANGE f4ef217e-0d04-4e7f-b92d-38f358e9afe7 | CLP 4,259 | item_text="COLLAR ARRANQUE PVC P/PVC 40 X 1\""
CHANGE f627694f-8ed7-4ae3-a191-e9a96fbfacf1 | CLP 8,219 | item_text="AP TAPON BEBEDEROS -____"
CHANGE f689cdda-ecb9-43cf-a400-918bfcd6e27d | CLP 4,917 | item_text="Collarín Arranque c/Refuerzo 63 x 3/4\" Arangül"
CHANGE f87c328d-4839-4e1c-b865-c4ff1face374 | CLP 5,336 | item_text="COLLARIN POLIPROPILENO 63MMX3 4 -@"
CHANGE 00f40187-e7fe-476d-9b1c-67151c534a24 | CLP 348 | item_text="-CODO HI-HI 3 4 -@"
CHANGE 020104f2-3adf-4bdf-9176-70d873769b15 | CLP 20,000 | item_text="Codo Compresión 32mm Arangül"
CHANGE 021ad9dc-d342-42e5-bd14-8444f1002bef | CLP 4,396 | item_text="K12-CODO SO-SO 1 2 -@"
CHANGE 025ac3a2-3d45-4b7e-92f0-2f2aeb2afc80 | CLP 5,008 | item_text="-UNION AMERICANA CEM 63 MM -@"
CHANGE 0325f3b9-2509-497b-b695-ba570cfdd2f9 | CLP 218 | item_text="-CODO 20 MM CEM -@"
CHANGE 036d23e7-cbbf-4adf-b410-26741e2a8c31 | CLP 358 | item_text="TERMINAL PVC-H HE 40 X 1,1/4\""
CHANGE 03706631-2ce3-4925-8fe1-d222fd0762c9 | CLP 3,101 | item_text="TERMINAL HE PLASTICO 1,1/2\""
CHANGE 045afe7b-78d4-4f44-b8bf-880714356024 | CLP 3,334 | item_text="TERMINAL HE PLASTICO 1,1/4\""
CHANGE 06412945-0a7e-40bd-996d-ccefdea28fca | CLP 1,804 | item_text="BUSHING GALVANIZADO 2 X 1,1/2\""
CHANGE 0956187e-7b05-4ac6-b50e-e6b32560229e | CLP 1,264 | item_text="TEE GALVANIZADA 3/4\""
CHANGE 095c85cc-5b6b-469c-82da-aafbb3463f6d | CLP 696 | item_text="-CODO HI-HI 3 4 -@"
CHANGE 0b8f80df-82fd-454c-9d56-9f11c7cee403 | CLP 125 | item_text="-CODO 20 MM CEM -@"
CHANGE 0ceac410-4e0d-416a-ab87-1d700d470304 | CLP 3,768 | item_text="K12-CODO SO-SO 1 2 -@"
CHANGE 0da4ea46-4b14-48ae-945e-3f47f230aaf2 | CLP 9,506 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 63MM = 2\""
CHANGE 0ebae826-086e-4f22-8bd2-06554ede3652 | CLP 540 | item_text="-BUSHING REDUCCION HE-HI 1 X 3 4 -@"
CHANGE 10698968-442b-40d8-8e5b-781c7b0b6fe1 | CLP 5,015 | item_text="TERMINAL HE PLASTICO 2\""
CHANGE 10bf7021-0f73-4203-8604-c90053f4a1bc | CLP 9,970 | item_text="UNION HE ALUMINIO 3\""
CHANGE 1164d0f5-6ae3-41fa-85f1-f3d213cc50ac | CLP 3,943 | item_text="COPLA SOLDAR 2\""
CHANGE 11b74d31-6501-46b2-95c1-c5cc958aa5a4 | CLP 2,682 | item_text="Buje Corto PVC 63mm - 50mm"
CHANGE 1207b46f-697d-4130-87a9-552d20c7ceb5 | CLP 2,223 | item_text="TERMINAL HE PLASTICO 1,1/4\""
CHANGE 12d5a005-c60d-449a-8941-24adfd1219a9 | CLP 319 | item_text="-BUSHING REDUCCION HE-HI 1 1 2 X 1 -@"
CHANGE 15289169-2b2d-4172-ae65-178877e69587 | CLP 1,389 | item_text="k12-COPLA SO-SO 1 2 -@"
CHANGE 17a840ef-42b8-4ccc-ae7b-947cdf111554 | CLP 3,968 | item_text="PL-TERMINAL HE 1 1 2 PLANSA -@"
CHANGE 17e649f7-df85-4ea7-897f-9fea3d28f1f5 | CLP 4,249 | item_text="BUSHING PLAST.BCO.HI HE 1,1/2 X 3/4\""
CHANGE 181dc25c-e376-461e-98a3-316bc9a4a2bf | CLP 3,090 | item_text="-NIPLE HE-HE 1 -@"
CHANGE 188f50c3-c4e0-4a54-886d-8d9eb9e98e97 | CLP 938 | item_text="TEE PLAST.BCO.HI HI 1\""
CHANGE 1dbe562a-4015-43c2-ba29-6e32ba13cdba | CLP 9,420 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 32MM = 1\""
CHANGE 1f219549-bef5-46e3-8991-90c611d30c4a | CLP 864 | item_text="BUSHING GALVANIZADO 1 X 3/4\""
CHANGE 2071ccee-83a9-4a7f-8c42-c55bf705073b | CLP 9,508 | item_text="UNION HE ALUMINIO 1,1/2\""
CHANGE 22f41a42-94aa-42e1-80a7-b977c30835ba | CLP 832 | item_text="CODO 1/2"
CHANGE 246497ec-6950-4570-89e8-69da9260ae0a | CLP 43,872 | item_text="Tee Compresión HI 32mm Arangül"
CHANGE 24ab6483-635c-43ee-8fad-b5215cb88878 | CLP 607 | item_text="NIPLE PLAST.BCO.HE HE 1\""
CHANGE 27cb431d-1e26-4a9e-91d6-35fd07d585ee | CLP 11,204 | item_text="UNION PLANSA 1 1/4\"- HOFFENS"
CHANGE 27ffede8-399c-4034-8379-d9c8d554c618 | CLP 3,720 | item_text="TERMINAL HI 1"
CHANGE 28bef7ca-4b5b-4dfa-b6c3-32c730e2da55 | CLP 555 | item_text="CODO PLANSA 1/2\" - HOFFENS"
CHANGE 28f9a2e6-1ce1-4771-ba23-473f3520a37a | CLP 6,083 | item_text="COPLA GALVANIZADA 1,1/2\""
CHANGE 2917097d-c47d-4e8d-9e28-f57d94375c17 | CLP 1,316 | item_text="UNION PLANSA 1/2\" - HOFFENS"
CHANGE 2c8e50d7-dde4-4d06-b9c5-45a6a8c88d3c | CLP 309 | item_text="-NIPLE HE-HE 1 -@"
CHANGE 2dd61932-c428-4bda-bb3d-8f2c24685935 | CLP 2,970 | item_text="TERMINAL HI PLASTICO 1,1/4\""
CHANGE 34307ad6-4d3d-433c-84c9-52a801aa75c2 | CLP 8,403 | item_text="KO-COPLA SO-SO 1 1 4 -@"
CHANGE 34c4f371-990c-4e43-94e7-f758926c1b75 | CLP 7,664 | item_text="NIPLE HEXAGONO GALVANIZADO 1\""
CHANGE 355f8db7-a1d5-49f0-b3bb-3cbb27f3d97b | CLP 1,565 | item_text="NIPLE PLAST.BCO.HE HE 1,1/4\""
CHANGE 359614c0-3b24-4c29-a3e6-19fc456d2eb7 | CLP 2,030 | item_text="GG-NIPPLE HE-HE GALV 1 1 2 -@"
CHANGE 39619d38-7f3e-480a-a924-8cb0993bfd5a | CLP 1,854 | item_text="-NIPLE HE-HE 1 -@"
CHANGE 3a90fff6-1099-4fe4-b826-862365889598 | CLP 154 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE 3bda42a7-3c31-428c-b5de-ecb84a1f4b04 | CLP 1,033 | item_text="TERMINAL HI PLANSA 1/2\" - HOFFENS"
CHANGE 3ddb5cb4-ef3f-4bb6-bec7-17757831598e | CLP 1,293 | item_text="TERMINAL HE PLASTICO 3/4\""
CHANGE 3e8c50bb-99ee-4561-a088-d544e6957d59 | CLP 705 | item_text="-BUSHING REDUCCION HE-HI 1 X 3 4 -@"
CHANGE 402c02d3-a620-40f3-99f5-8abaa322add9 | CLP 1,608 | item_text="TEE PLASTICO 1\""
CHANGE 406dddbf-9c9a-44cc-93ea-7fdcc03d8de3 | CLP 21,641 | item_text="Tapón Compresión 32mm Arangül"
CHANGE 46a3fc5c-e5ae-4457-8370-57a63b2c2575 | CLP 5,792 | item_text="Tapón Compresión 63mm Poelsan GS"
CHANGE 46ed2fbd-c178-4799-b5d7-c3a63ffed837 | CLP 6,933 | item_text="GG-CODO GALV 90 MACHO HEMBRA 1 -@"
CHANGE 477f191d-2ef2-4a89-a9a9-5b1b2657fdfb | CLP 1,916 | item_text="TERMINAL HE PLASTICO 1\""
CHANGE 47a317cc-db82-456c-b470-ccd605f38654 | CLP 540 | item_text="-BUSHING REDUCCION HE-HI 1 X 3 4 -@"
CHANGE 4852fcdc-5a86-4455-98ee-210c3993daa6 | CLP 6,378 | item_text="PL-TERMINAL HI 1 1 4 PLANSA -@"
CHANGE 4aabd3b8-82e8-4a4a-8ab8-9d12a8034ceb | CLP 4,862 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 40MM = 1,1/4\""
CHANGE 4b781429-7b86-46cb-9179-32666a1e6e05 | CLP 4,710 | item_text="BUSHING GALVANIZADO 3/4 X 1/2\""
CHANGE 4bb684ba-f4e6-417e-a114-98086aa01d55 | CLP 3,860 | item_text="PL-TEE 1 2 PLANSA -@"
CHANGE 4c014a4f-9d31-4f49-a73d-9719baba4fa6 | CLP 1,818 | item_text="BUSHING GALVANIZADO 1 X 3/4\""
CHANGE 4f4d7e72-77c8-4d34-8c71-1a04b0689d72 | CLP 877 | item_text="BUSHING PLAST.BCO.HI HE 1,1/2 X 1,1/4\""
CHANGE 4f651e14-333d-4edf-a638-b57f6b319dca | CLP 3,177 | item_text="NIPLE HEXAGONO GALVANIZADO 1,1/2\""
CHANGE 5017617d-4987-428c-9b9e-43b8017b29b6 | CLP 6,609 | item_text="-CODO 75 MM CEM -@"
CHANGE 519928fa-6858-471c-af2f-021363d2a485 | CLP 3,090 | item_text="-NIPLE HE-HE 1 -@"
CHANGE 5251ee96-1dfe-42bb-95f4-0bf0ef29b035 | CLP 1,756 | item_text="TAPON GORRO PLAST.BCO.HI 1/2\""
CHANGE 53dad976-35e6-4d3b-82b2-f11890c522cc | CLP 731 | item_text="TERMINAL HE PLASTICO 1\""
CHANGE 54c85c05-05da-4267-a793-b400f264efb6 | CLP 1,431 | item_text="K12-CODO SO-HI 1 2 -@"
CHANGE 559b3103-4eda-4206-9e0a-7561601efd85 | CLP 4,870 | item_text="TERMINAL HI PLASTICO 1\""
CHANGE 56b034a3-6910-4500-b2a3-89d44ba1fccd | CLP 92 | item_text="TERMINAL PVC"
CHANGE 5c27127c-d06c-4e30-9276-c63d73c49aaf | CLP 8,860 | item_text="Terminal Compresión HI 32mm Pimtas ST"
CHANGE 5c8f693b-b984-4bf8-adf3-110c23ff234d | CLP 1,389 | item_text="k12-COPLA SO-SO 1 2 -@"
CHANGE 5e60bfd4-ce6e-4e9e-823f-5a8037cacb42 | CLP 546 | item_text="K12-CODO SO-SO 1 2 -@"
CHANGE 5eb69145-0a53-498e-ac66-b16fbea02ef1 | CLP 773 | item_text="-COPLA CEM 63 MM -@"
CHANGE 5ec24bf2-4c8c-459a-ac7b-41e71b572978 | CLP 15,966 | item_text="TEE ROSCADA PN16 32MM - IRRITEC"
CHANGE 610feb8e-6b58-4f96-ac16-3de716d5cd0b | CLP 176 | item_text="COPLA 25MM"
CHANGE 61d78103-7bb9-4616-9cac-e7f52e6bf66a | CLP 6,262 | item_text="GG-BUSHING GALV 3 X 2 1 2 -@"
CHANGE 62bb9f84-2e74-4ca4-8b96-786c3b8463f1 | CLP 1,890 | item_text="BUSHING PLAST.BCO.HI HE 2 X 1,1/2\""
CHANGE 62ef8429-c4f8-4e41-9ccf-6436e526225e | CLP 242 | item_text="-BUSHING REDUCCION HE-HI 1 X 1 2 -@"
CHANGE 637eca76-9727-4a29-842d-3f40f461a66e | CLP 14,446 | item_text="COPLA SO SO 1,1/2\""
CHANGE 65621979-ef12-49f8-94ef-9fa42cdc2d50 | CLP 918 | item_text="TERMINAL SOLDAR HI 1/2\""
CHANGE 6708de04-34dc-4f2a-b5a1-2b15391b0d03 | CLP 462 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE 697340f7-5da8-425a-b20f-6e0150dc7445 | CLP 2,071 | item_text="TEE PLANSA 1/2\" - HOFFENS"
CHANGE 6a647907-2f4c-4d9e-bc96-bc6217d912f6 | CLP 4,710 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 32MM = 1\""
CHANGE 6cb84f41-c9b7-4da3-90d6-675d0580240e | CLP 992 | item_text="CODO BRONCE 1 2 CACHIMBA -@"
CHANGE 6d4b83fd-e9fa-44cd-8455-1cea3245b965 | CLP 3,711 | item_text="-COPLA HI-HI 1 1 4 -@"
CHANGE 6d6f1d8b-f11f-45ae-87c5-6075670e5d19 | CLP 474 | item_text="-CODO HI-HI 1 -@"
CHANGE 6def6a2b-a806-47e7-84c5-63ef50cb0a46 | CLP 8,970 | item_text="CODO PVC 45 , MAC/HE, BLANCO"
CHANGE 6f016faf-1419-403b-bba4-09d28f394e3f | CLP 2,976 | item_text="PL-TERMINAL HE 1 PLANSA -@"
CHANGE 704dd07a-8cbf-497a-91df-54bdf19d8702 | CLP 2,251 | item_text="NIPLE PLAST.BCO.HE HE 1,1/2\""
CHANGE 7148a34c-f0a8-48ab-b1a4-69adf964694d | CLP 1,664 | item_text="K1-COPLA SO-SO 1 -@"
CHANGE 75cdbf50-ba20-4909-aede-8a1ce9bb12f4 | CLP 628 | item_text="-BUSHING REDUCCION HE-HI 2 X 1 1 2 -@"
CHANGE 75d82e43-f899-44bc-b356-7a7be3f9707b | CLP 24,703 | item_text="UNION AMERICANA SO SO 1,1/2\""
CHANGE 762bfd9a-9db7-420d-9b92-c4a6fa91b665 | CLP 5,332 | item_text="TERMINAL HI PLASTICO 1,1/2\""
CHANGE 76fa3127-62f3-408b-9662-108fc53bd771 | CLP 2,127 | item_text="UNION RAPIDA P/LLAVE HE 3/4\""
CHANGE 77a9bddc-8610-421c-99cc-f6c5a7769aa0 | CLP 9,279 | item_text="UNION DOBLE PLANSA 1.1 2"
CHANGE 7a9de913-100c-4f0f-8b41-db7e0575fc2b | CLP 948 | item_text="PL-TEE 1 PLANSA -@"
CHANGE 7e6d1b79-251c-47fc-a7b8-ca43b644d2f6 | CLP 1,857 | item_text="HI PLANZA 11/2"
CHANGE 7e76fb0f-ff98-4a04-800a-9101a147e43b | CLP 5,557 | item_text="GG-NIPPLE HE-HE GALV 2 1 2 -@"
CHANGE 7f5f2b7b-97a1-468e-89e5-f7c965f82fe1 | CLP 894 | item_text="BUJE RED.CORTO PVC-H 63 X 50"
CHANGE 80104196-43c5-48e8-a4b0-f7f2991ae895 | CLP 7,425 | item_text="Tee Compresión HI 63mm GS Pimtas"
CHANGE 80631eb0-27a7-48f3-aa95-578f403e53e3 | CLP 937 | item_text="-NIPLE HE-HE 2 -@"
CHANGE 80dcdc1f-2571-4df2-a2a4-0b5868616363 | CLP 244 | item_text="-BUSHING REDUCCION HE-HI 1 1 4 X 1 -@"
CHANGE 8117659e-0ad5-4b5c-86ab-d3760d55f539 | CLP 1,630 | item_text="TEE SO HI 1/2\""
CHANGE 811cb3a7-99e8-4b01-aac4-f311532789be | CLP 924 | item_text="PL-TERMINAL HI 1 1 4 PLANSA -@"
CHANGE 81b18b49-8e43-4fa9-aba5-a544804b83db | CLP 654 | item_text="TEE PLANSA 1/2\" - HOFFENS"
CHANGE 826beba1-774a-401a-9542-7f4219b0741b | CLP 773 | item_text="PL-TERMINAL HI 1 PLANSA -@"
CHANGE 83ce588e-5734-4d4d-a44d-e773d2d75edb | CLP 443 | item_text="TEE PLASTICO 3/4\""
CHANGE 84922c4f-eb18-4b2a-bc6c-2256fe8972fd | CLP 22,275 | item_text="Tee Compresión HI 63mm GS Pimtas"
CHANGE 8790b620-9b23-41ed-879f-f1894480da72 | CLP 6,410 | item_text="Copla Bronce HI-HI 1/4\""
CHANGE 886c6bb3-ea34-4eff-8822-3fa4765c80d0 | CLP 3,073 | item_text="GG-COPLA HI-HI GALV 2 -@"
CHANGE 8a5f654a-67f1-4614-a5ac-cb9193cafc85 | CLP 838 | item_text="TAPON GORRO PLAST.BCO.HI 1/2\""
CHANGE 8b787bce-7716-4ed0-8ddb-485af1cccb8c | CLP 2,309 | item_text="GG-BUSHING GALV 2 X 1 1 2 -@"
CHANGE 8bb284f9-d7ce-482d-8dce-585fa87c5aca | CLP 378 | item_text="COPLA 20MM"
CHANGE 8c1c7b83-ef2c-41af-951d-de44b38535e1 | CLP 657 | item_text="-BUSHING REDUCCION HE-HI 2 X 1-@"
CHANGE 9155a423-637c-472e-bdce-2a6488e3c8bd | CLP 420 | item_text="-COPLA REDUCCION HI-HI 1 X 3/4 -@"
CHANGE 91741cb9-968c-481c-8f95-133b7fc635be | CLP 2,672 | item_text="Terminal Compresión 40mm HI"
CHANGE 91c58ef8-7377-44cd-afd7-c794ecb068fd | CLP 3,228 | item_text="GG-NIPPLE HE-HE GALV 1 -@"
CHANGE 9219b50c-9c84-4471-b126-b26f8b7e17be | CLP 2,880 | item_text="GG-BUSHING GALV 2 X 1 -@"
CHANGE 93830f53-2785-4dee-895b-7ba256cc45d8 | CLP 1,990 | item_text="ADAPTADOR MACHO 3/4 BROCE"
CHANGE 93be7d0a-f65c-4e81-b397-ce072cb86d25 | CLP 5,710 | item_text="PL-UNION DOBLE 1 PLANSA -@"
CHANGE 94324df9-3ea4-4bf9-a814-5b0322c63f20 | CLP 19,135 | item_text="GG-CODO GALV 90 MACHO MACHO 2 1 2 -@"
CHANGE 94f534e4-964f-4d0b-8ecb-208cc5304ac2 | CLP 718 | item_text="TERMINAL HE PLASTICO 1/2\""
CHANGE 95a467fa-5e9f-40d0-b650-6beda94ada24 | CLP 1,387 | item_text="-TEE CEM 63 MM -@"
CHANGE 95b4b2a7-10ed-43af-89e6-b5f6502a57c0 | CLP 336 | item_text="PL-TERMINAL HE 1 PLANSA -@"
CHANGE 9736a7d5-4a46-4674-960e-e374fa6b77ee | CLP 339 | item_text="TAPON TORNILLO PLAST.BCO.HE 1,1/2\""
CHANGE 9750da48-fe1b-4e3f-ba2d-6158687e2cc4 | CLP 766 | item_text="ADAPTADOR LLAVE HEMBRA 1/2 A 3/4"
CHANGE 977b5713-c98a-4077-b510-3f58a347bfa5 | CLP 2,347 | item_text="BUSHING PLAST.BCO.HI HE 1 X 3/4\""
CHANGE 985841f6-1b2c-4d7f-a49a-62b39e6621a4 | CLP 756 | item_text="CODO PLANSA HI 1/2\" - HOFFENS"
CHANGE 99009995-d9e0-47b6-8b5d-50661d80d88b | CLP 1,573 | item_text="TEE GALVANIZADA 1\""
CHANGE 9b824f7b-4413-437d-9679-8ac1ac4ca9c3 | CLP 1,686 | item_text="-BUSHING REDUCCION HE-HI 1 1 4 X 1 -@"
CHANGE 9fff5360-6ef6-456a-af36-cef74ab84649 | CLP 13,980 | item_text="CODO SO SO 1 BOLSA"
CHANGE a462577f-f945-41e5-ae97-1197516f37ec | CLP 367 | item_text="-BUSHING REDUCCION HE-HI 1 1 2 X 1 -@"
CHANGE a54e62e7-f572-4b86-b9c0-cc71a7dceaad | CLP 1,589 | item_text="TEE PLAST.BCO.HI HI 1,1/2\""
CHANGE a5944f3b-d637-4296-8397-19e9a259b5fc | CLP 17,149 | item_text="UNION PLASTICA 2 X 1,1/2\""
CHANGE a637cb10-c59d-419a-b2b2-91aafb707b89 | CLP 4,260 | item_text="UNION PLASTICA 1,1/2 X 1,1/4\""
CHANGE a6b03f80-b1a0-4bf1-94d6-b5e526bef226 | CLP 4,669 | item_text="CODO COBRE 90O 1/2 SO/SO...."
CHANGE a772fd36-d22a-417e-bd8c-441791a84d97 | CLP 2,108 | item_text="UNION LLAVE HI 189202 1/2 X 3/4\""
CHANGE a94b4af4-b1d4-408e-8aad-f885ed482cd9 | CLP 4,611 | item_text="BUSHING PLAST.BCO.HI HE 2 X 1,1/2\""
CHANGE a9961809-2135-44a7-ab53-fba6138ef0c5 | CLP 308 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE ab5a2c9d-8e78-4ef1-9333-feb62de0aae3 | CLP 47,360 | item_text="Terminal Compresión HE 63mm GS"
CHANGE aca80288-f575-4dda-980a-fd80f2d98847 | CLP 17,200 | item_text="PL-REDUCCION 1 1 2 X 1 1 4 PLANSA -@"
CHANGE acf31dc4-f271-4e1a-8603-66c1fb145f48 | CLP 1,540 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE ae5527ae-95a9-42d0-8742-0b4bf647572d | CLP 937 | item_text="-NIPLE HE-HE 2 -@"
CHANGE b08ffbed-d664-4157-92a8-713360b9ff91 | CLP 992 | item_text="BUSHING GALVANIZADO 3/4 X 1/2\""
CHANGE b1165e57-2a19-464e-8182-6781a2d9d734 | CLP 269 | item_text="-NIPLE HE-HE 1 -@"
CHANGE b197f986-330a-4ade-92aa-565b64f6b7b9 | CLP 2,191 | item_text="BUSHING PLAST.BCO.HI HE 1,1/2 X 1,1/4\""
CHANGE b2f04517-3b66-4c53-87d5-1d6dfc8ed10d | CLP 114 | item_text="COPLA CEM PVC PRES 25 MM"
CHANGE b6eb470b-43ee-4dfa-9de7-e27df62dc9b8 | CLP 766 | item_text="BUSHING PLAST.BCO.HI HE 3/4 X 1/2\""
CHANGE b7ff8345-7a3c-4e33-bcdc-691fd6e95c6f | CLP 11,980 | item_text="TERMINAL SO HE 1"
CHANGE b8e7cf64-9ff7-4d67-95f1-a1cd31a1a5c5 | CLP 14,524 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 50MM = 1,1/2\""
CHANGE baa513b9-5028-403e-a881-059d5188c473 | CLP 3,952 | item_text="UNION PLASTICA 1\""
CHANGE baddc970-3627-43bc-b916-f71d32c1c310 | CLP 822 | item_text="TERMINAL SO HI 1/2\""
CHANGE bb5e113b-e85f-4e3e-a16c-2741bbb3a8c7 | CLP 5,984 | item_text="CURVA GALVANIZADA HI HE 2\""
CHANGE bf735478-a0d2-4f66-b932-1dcf6d383b80 | CLP 5,040 | item_text="Niple PP 1\" x 1\" Arangül"
CHANGE c0ac87ad-069d-4df0-8634-465a117b648c | CLP 134 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE c1db246f-80c3-4c40-8926-7d345d62fe38 | CLP 1,756 | item_text="BUSHING PLAST.BCO.HI HE 1 X 3/4\""
CHANGE c222fce9-c147-48c2-87a6-d4c295582b51 | CLP 1,159 | item_text="K12-CODO SO-HE 1 2 -@"
CHANGE c3cbd776-ad99-4ccb-9955-a955d49d3b8e | CLP 331 | item_text="BUSHING PLAST.BCO.HI HE 1,1/4 X 1\""
CHANGE c3e22887-46cb-4272-b291-7bb7f2e2de11 | CLP 5,882 | item_text="Terminal Compresión 40mm HE"
CHANGE c3f73728-3d42-492b-a535-8544e6724309 | CLP 1,389 | item_text="-BUSHING REDUCCION HE-HI 1 1 4 X 3 4 -@"
CHANGE c59a3c2e-c395-4a48-be04-a6cd7be2b2d5 | CLP 1,086 | item_text="CODO SOLDAR 1/2\""
CHANGE c5c0dc3c-fef4-489b-9eab-72b092cac82d | CLP 1,680 | item_text="PL-TERMINAL HE 1 2 PLANSA -@"
CHANGE c74b273e-b7ad-4820-abb0-4c9d0c806843 | CLP 840 | item_text="-CODO HI CEM 20 X 1 2 -@"
CHANGE c85b668e-e646-4c26-9dfd-cff1f5a21c1a | CLP 87 | item_text="-COPLA CEM 20 MM -@"
CHANGE c93a31ab-7ddd-451f-b047-c024c5367ebf | CLP 242 | item_text="-BUSHING REDUCCION HE-HI 1 X 1 2 -@"
CHANGE cef76999-e75a-4df0-bcbc-5a63a62d3f84 | CLP 1,004 | item_text="PL-TERMINAL HE 3 4 PLANSA -@"
CHANGE cfb01d51-31e5-471b-bfd4-1c02bd1dbcae | CLP 2,688 | item_text="PL-TERMINAL HE 1 PLANSA -@"
CHANGE d0bb086e-c82f-4816-8896-21c4a76d9a02 | CLP 2,036 | item_text="TERMINAL HE PLANSA 1 1/4\" - HOFFENS"
CHANGE d4358c6f-0dae-42f8-ad08-6008a9f25992 | CLP 616 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE d53d2a8e-bcef-4e59-95b4-7c2504d4631f | CLP 2,536 | item_text="Terminal Compresión HE 32mm Arangül"
CHANGE d5b8b763-9e33-44f9-b0c5-e9b6b7e12aaf | CLP 654 | item_text="-CODO 20 MM CEM -@"
CHANGE d8e5204b-6454-42d6-bbab-c660e2f94932 | CLP 3,421 | item_text="UNION AMER BR 1/2 SO/SO 1UN."
CHANGE d98efd66-fe75-4de4-a7b1-931430b0c83e | CLP 6,180 | item_text="-NIPLE HE-HE 1 -@"
CHANGE dbfd8aeb-f8a3-4f71-82b4-a232600761c1 | CLP 770 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE dcabb474-7d97-42bd-affb-bbfe87db0c4a | CLP 9,076 | item_text="COPLA ROSCADA PN16 - IRRITEC 32 X 32"
CHANGE dcac24e0-f4ca-441a-a685-6cef501e1c37 | CLP 3,169 | item_text="BUSHING GALVANIZADO 2,1/2 X 2\""
CHANGE e3b313e5-19c5-49c6-9844-46d0cc201314 | CLP 154 | item_text="-NIPLE HE-HE 3 4 -@"
CHANGE e3c7aadc-823b-449d-9bd4-dff2fa3cd2fc | CLP 12,278 | item_text="TAPON GORRO PLAST.BCO.HI 4\""
CHANGE e63df2ef-b9db-408a-8c02-1c25cda4191a | CLP 2,334 | item_text="CODO BR 90O 1/2 SO/HE 1UN..."
CHANGE e92e3012-2705-4144-9c96-4de0bd5f3931 | CLP 6,020 | item_text="Codo PP HI-HI 32 x 32mm Arangül"
CHANGE e9a2f015-dc66-434e-81c3-abe185caec76 | CLP 860 | item_text="GG-BUSHING GALV 1 X 3 4 -@"
CHANGE e9e7a39c-bf26-447e-ac76-e618aed42142 | CLP 2,756 | item_text="K34-CODO SO-SO 3 4 -@"
CHANGE ea2c427a-64c5-4b40-9ca8-5db70470e51d | CLP 1,488 | item_text="TEE PLAST.BCO.HI HI 1,1/4\""
CHANGE ec572c0c-deba-464a-ac49-1669623bf1f5 | CLP 12,278 | item_text="TAPON GORRO PLAST.BCO.HI 4\""
CHANGE eddb498a-abad-4cdb-bcbe-8041332a4ad4 | CLP 3,541 | item_text="BUSHING PLAST.BCO.HI HE 1,1/2 X 3/4\""
CHANGE efd13f40-2077-4006-a909-104b0523688a | CLP 940 | item_text="-BUSHING REDUCCION HE-HI 1 X 3 4 -@"
CHANGE efe0cfbb-dda4-4de4-b8d8-fbf3674ce6a3 | CLP 1,512 | item_text="k12-COPLA SO-SO 1 2 -@"
CHANGE f12988d1-7482-4564-a225-7fef7f14eef4 | CLP 3,027 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 32MM = 1\""
CHANGE f3ccf872-371d-4de5-a925-b7bc8a136ce9 | CLP 790 | item_text="UNION PLASTICA 1\""
CHANGE f41a98f4-8082-4536-933e-468a56d42dea | CLP 129 | item_text="TAPON TORNILLO PLAST.BCO.HE 3/4\""
CHANGE f527274b-48f6-454f-bbae-de8495170341 | CLP 7,530 | item_text="-CODO HI CEM 32 X 1 -@"
CHANGE f53cae04-72be-43bb-880d-a575a1955711 | CLP 193 | item_text="CODO 25MM"
CHANGE f563a803-c8d5-478d-ab24-b95a9fc7ce24 | CLP 1,080 | item_text="-BUSHING REDUCCION HE-HI 1 X 3 4 -@"
CHANGE f7c9e309-23bd-4080-8bd0-7e68379b995b | CLP 8,287 | item_text="TERMINAL HI PLASTICO 2\""
CHANGE f8c5320f-8f15-4da1-87d4-de19f7835eea | CLP 8,527 | item_text="TERMINAL HE PLASTICO 1,1/2\""
CHANGE fda24685-f589-4b64-bb97-771ae20e8a1a | CLP 244 | item_text="-BUSHING REDUCCION HE-HI 1 1 4 X 1 -@"
CHANGE ff43ebe8-dda6-4d0a-96e2-463f2c2ecc06 | CLP 676 | item_text="K38-COPLA RED SO-SO 1 2 X 3 8"
CHANGE ffc5c04e-524f-4b09-94e4-30d6dd886d45 | CLP 6,223 | item_text="VALVULA DE BOLA PVC-HILO S/UNION 50MM = 1,1/2\""
CHANGE 0390a7bc-8621-4571-a8df-153612348875 | CLP 1,506 | item_text="VALVULA COMPACTA HI 3/4 60893 -@"
CHANGE 039f19f9-a36e-4b5c-b437-381980c37b8e | CLP 9,480 | item_text="VALVULA BOLA COMPACTA HI 1 2 -@"
CHANGE 03cd5543-4941-4da2-bc59-901e130bda42 | CLP 212,024 | item_text="Válvula Compresión 63mm Arangül"
CHANGE 0792091c-fd7b-49c2-96c4-fb0ce7efc504 | CLP 1,431 | item_text="FU-LLAVE DE BOLA PP-R COMPLETA 20 MM 90158 -@"
CHANGE 08b13d7b-6c51-4122-9a16-ba7be4228e1d | CLP 2,512 | item_text="VALVULA COMPACTA HI 1 -@"
CHANGE 0b5ef84d-c05c-424f-b5d8-e52411562e03 | CLP 20,504 | item_text="LLAVE BOLA JARDIN PN16 DE 1 2 X 3 4 GENEBRE -@"
CHANGE 0ce4ae41-0e37-4e4a-ae6f-5bfe8e182115 | CLP 2,512 | item_text="VALVULA COMPACTA HI 1 -@"
CHANGE 0e4c0a76-2532-42e2-9823-3b768c9eb0eb | CLP 2,493 | item_text="LLAVE DE BOLA JARDIN 3/4 MANILLA ROJA H-FULL -@"
CHANGE 10851065-5d01-4a5c-8c04-03c85f0b160f | CLP 24,285 | item_text="VALVULA BOLA OTRA 1 HI-HI TAUMM 060155002 -@"
CHANGE 113132eb-5246-4c06-b77d-dbb063f894bb | CLP 97,412 | item_text="VALVULA BOLA PASO TOTAL PN25 DE 1 1 2 GENEBRE -@"
CHANGE 13c77681-9829-4e63-902f-b0dd54c3ad7f | CLP 24,474 | item_text="VALVULA DE BOLA HI ITALI 1,1/4\""
CHANGE 157bff62-47e0-4736-9c91-0a127f49e75a | CLP 7,288 | item_text="Válvula de Bola PP 32mm HI Arangül"
CHANGE 1631c5e5-0359-4058-9759-2675e1d7dd1a | CLP 50,000 | item_text="Mini Válvula Espiga-He 16mm Celeste EDR"
CHANGE 2a43da4e-cc31-4da7-8539-d83546a62e9c | CLP 9,046 | item_text="VALVULA COMPACTA HI 2 ERA-@"
CHANGE 3358fa61-48d7-493f-8871-e4c7c62c6d63 | CLP 10,883 | item_text="* VALVULA DE BOLA HI ITALI 1/2\" *OFERTA*"
CHANGE 34da1b4a-4bde-46c4-a344-1721809987e8 | CLP 95,840 | item_text="Válvula Compresión HE 32mm Arangül"
CHANGE 370d7f0b-4c96-4157-8ec1-5ca37f73790d | CLP 65,286 | item_text="VALVULA DE BOLA HI ITALI 1,1/2\""
CHANGE 375aace1-2b8d-46de-a221-92921c8ac279 | CLP 50,060 | item_text="VALVULA BOLA PASO 1 H-FULL MANILLA ROJA 5004055 -@"
CHANGE 39d672b9-927f-4b6e-8d4e-e2e674020e00 | CLP 3,847 | item_text="VALVULA BOLA COMPACTA HI 1 1 4 -@"
CHANGE 3cae63ca-e2b0-47c0-92a1-fcc09868c1db | CLP 4,605 | item_text="VALVULA BOLA PN25-1 2 GENEBRE -@"
CHANGE 3d1ddf42-4b6d-442d-9ec6-33239727691e | CLP 36,975 | item_text="LLAVE BOLA JARDIN PN16 DE 3 4 X 1 GENEBRE -@"
CHANGE 3d2d2ebc-ebe4-4072-89d6-a75181266532 | CLP 19,524 | item_text="Válvula de Bola PP 63mm HI Arangül"
CHANGE 407c0002-7f75-4b5f-946a-aaf6742c31c9 | CLP 83,950 | item_text="VALVULA BOLA OTRA HI-HI 2 TAUMM 060188002 -@"
CHANGE 419cb46f-ef00-430a-a8b6-258a646e1e0c | CLP 176,433 | item_text="Válvula Ventosa Triple 2\" GTR"
CHANGE 41aff1c0-c45b-4f32-ac06-18101f9b6706 | CLP 75,688 | item_text="VALVULA BOLA OTRA HI-HI 2 TAUMM 060188002 -@"
CHANGE 460db600-08a0-4594-b1c4-3deea709747a | CLP 2,261 | item_text="LLAVE BOLA JARDIN 1 2 H-FULL MANILLA ROJA -@"
CHANGE 468aecd7-c9f1-46aa-bb8b-0a125f05f3d9 | CLP 7,462 | item_text="LLAVE BOLA JARDIN TAUMM/STRETTO 1/2\""
CHANGE 49546d92-13b6-4f5b-9d97-2925e83ceea4 | CLP 23,898 | item_text="LLAVE BOLA JARDIN PN16 DE 3 4 X 1 GENEBRE -@"
CHANGE 49b780c9-5c71-435c-b7aa-4b2293537f7d | CLP 23,960 | item_text="Válvula Compresión HE 32mm Arangül"
CHANGE 4edafeb1-a578-49ee-9d9b-cc89f7932051 | CLP 15,378 | item_text="LLAVE BOLA JARDIN PN16 DE 1 2 X 3 4 GENEBRE -@"
CHANGE 53584732-5c05-431c-8977-ed5e408f93a4 | CLP 2,672 | item_text="LLAVE BOLA JARDIN LAVADERO 1/2 OTRA TAUMM 070200325 -@"
CHANGE 539a58c8-f905-451d-9f1c-66cf3ef26929 | CLP 3,765 | item_text="VALVULA COMPACTA HI 3/4 60893 -@"
CHANGE 576a1681-d3e2-4970-9b92-698c1c84df34 | CLP 4,233 | item_text="FU-LLAVE PASO METALICA MANILLA ROJA (20 mm) HOFFENS 90101 -@"
CHANGE 627db811-7b39-4d97-881d-5843324870b9 | CLP 26,113 | item_text="VALVULA DE BOLA HI ITALI 1,1/2\""
CHANGE 62f76120-0df9-44b5-96d1-78efab7fadba | CLP 5,798 | item_text="VALVULA BOLA HI-HI 3 4"
CHANGE 63170442-22ab-48c5-8e9c-5709713fdf53 | CLP 28,798 | item_text="VALVULA RETENCION VERTICAL 3 PESADA -@"
CHANGE 6791042d-79d7-42ca-9d19-c45f43006d0b | CLP 61,854 | item_text="Válvula Reguladora de Presión 1\" Hi EDR"
CHANGE 6dd9605d-4f19-4705-80e1-493ca38ab8e8 | CLP 3,073 | item_text="LLAVE PASO SOLDAR 1 2 BRONCE AQUAKIT LLPA12 -@"
CHANGE 6ffc1a01-5078-4bcd-88c8-36ee0cc2cf1b | CLP 49,496 | item_text="VALVULA DE BOLA HI ITALI 1\""
CHANGE 85bc03e8-0231-4922-9814-c262c5f7c963 | CLP 29,244 | item_text="VALVULA BOLA TOTAL PN25 3 4 GENEBRE -@"
CHANGE 8844ccf6-fe0e-4ae5-8a93-3c69ab4f5c5a | CLP 287,873 | item_text="VALVULA COMPTA.ITAL.C/HILO 2\""
CHANGE 89445aaf-ddfa-4382-9298-d6272276d0ee | CLP 2,843 | item_text="LLAVE BOLA JARDIN/LAVAD 1/2.."
CHANGE 89c9996e-b66c-4e9f-8acc-a9eefd1045ce | CLP 7,512 | item_text="VALVULA BOLA PASO 3 4 H-FULL -@"
CHANGE 8a265ebb-f4aa-459c-914d-8ec0d3dfddb6 | CLP 6,479 | item_text="LLAVE PASO 1/2 HE/HI.. CUN11Cp"
CHANGE 8c8382ea-d2fa-4f94-8fd4-becb023d7173 | CLP 2,259 | item_text="VALVULA COMPACTA HI 3/4 60893 -@"
CHANGE 91f3da85-3c37-493f-84ba-c1c8c75c4427 | CLP 3,269 | item_text="VALVULA DE BOLA HI ITALI 3/4\""
CHANGE 92ad18d9-e881-4bc5-a62b-f766e27a05e5 | CLP 10,571 | item_text="VALVULA BOLA OTRA HI-HI 1 1/2 060177002 TAUMM -@"
CHANGE 99f1959c-c2a3-47be-b0b5-58ccaa76a62f | CLP 56,930 | item_text="VALVULA BOLA HI-HI 1 TAUMM 060155000 -@"
CHANGE 9ecf4fcc-3342-4101-8721-9faa1da5a4b7 | CLP 2,600 | item_text="LLAVE BOLA JARDIN 1 2 H-FULL MANILLA ROJA -@"
CHANGE a774115d-98f4-4c90-bb31-cc82b7d982ce | CLP 99,693 | item_text="VALVULA DE BOLA HI ITALI 2\""
CHANGE a7d5b3f6-691e-47ab-ab28-5dbd63f5fbb7 | CLP 7,866 | item_text="VALVULA COMPACTA HI 2 ERA-@"
CHANGE a91d380a-ce0c-4d6c-ac06-bf6231909055 | CLP 2,259 | item_text="VALVULA COMPACTA HI 3/4 60893 -@"
CHANGE a96a3a12-fb33-47f6-a228-1cbf2fe07903 | CLP 6,529 | item_text="* VALVULA DE BOLA HI ITALI 1/2\" *OFERTA*"
CHANGE a9a075ee-0a16-4cba-baa2-1c88f311b00c | CLP 753 | item_text="VALVULA COMPACTA HI 3/4 60893 -@"
CHANGE b00a3c79-878d-4a5b-af04-aa97b624247e | CLP 52,228 | item_text="VALVULA DE BOLA HI ITALI 1,1/2\""
CHANGE b65b0b17-924b-42fc-97d7-36e7b098fb84 | CLP 49,496 | item_text="VALVULA DE BOLA HI ITALI 1\""
CHANGE b839d1d4-6e2f-4e8d-9cd2-123f306f04f1 | CLP 9,480 | item_text="VALVULA BOLA COMPACTA HI 1 2 -@"
CHANGE c0e7690d-92ca-4d9a-8353-1859b1f58f0e | CLP 58,572 | item_text="Válvula de Bola PP 63mm HI Arangül"
CHANGE c0f4a10a-074f-40fe-bdc1-b1915d827146 | CLP 21,142 | item_text="VALVULA BOLA OTRA HI-HI 1 1/2 060177002 TAUMM -@"
CHANGE c61bbaf3-8d83-486d-b23e-4cba34fefaaa | CLP 17,630 | item_text="VALVULA COMPTA.ITAL.C/HILO 2\""
CHANGE cda0b12f-a171-46ad-a72c-a3de741bb430 | CLP 9,540 | item_text="LLAVE PASO SOLDAR 1 2 L-522 FAS -@"
CHANGE d433eee7-90eb-4802-bd1c-1c2e15cd8e6e | CLP 2,300 | item_text="LLAVE DE BOLA 3/4 MANILLA ROJA HOFFENS 61246 -@"
CHANGE d6a35460-9513-427e-885f-1fe77c622aff | CLP 21,142 | item_text="VALVULA BOLA OTRA HI-HI 1 1/2 060177002 TAUMM -@"
CHANGE d7dd0c49-a7b3-4ab8-8928-c20c494a8b0f | CLP 5,029 | item_text="VALVULA DE BOLA HI ITALI 1\""
CHANGE dc1a353c-80c5-4149-abb5-da17caf16d65 | CLP 8,158 | item_text="VALVULA DE BOLA HI ITALI 1,1/4\""
CHANGE df006b0e-6a9d-4ace-9ea3-30d1b3a4b703 | CLP 14,571 | item_text="VALVULA BOLA OTRA 1 HI-HI TAUMM 060155002 -@"
CHANGE e763a3ef-158d-4a4d-969a-461b6475f29a | CLP 87,361 | item_text="FLOTADOR 3/4\" (20MM) C/ADAPTADOR A 1\" (25MM) AP20/25"
CHANGE ef28bd11-ffa2-4497-a0b9-35d43f341580 | CLP 4,950 | item_text="VALVULA DE BOLA HI ITALI 1\""
CHANGE f0d65886-cd62-46a7-88d7-754def4b57d9 | CLP 43,530 | item_text="VALVULA BOLA HI-HI 1 TAUMM 060155000 -@"
CHANGE fa331a99-b090-4d8d-b752-98c066add75d | CLP 1,092 | item_text="VALVULA COMPACTA HI 1 -@"
CHANGE fb8b2a8b-b662-478b-a1cc-1421e42ab89b | CLP 138,090 | item_text="VALVULA BOLA PASO TOTAL PN25 DE 1 GENEBRE 302906 -@"
CHANGE fda2d21c-fd6a-4e7a-b71a-405fa9a29c85 | CLP 11,160 | item_text="VALVULA BOLA PASO TOTAL PN25 DE 1 GENEBRE 302906 -@"
CHANGE fdaefc8e-3cd2-4525-857b-ad4869477b3b | CLP 14,400 | item_text="VALVULA BOLA PASO 3 4 H-FULL -@"
CHANGE 026e025c-c485-45a9-add2-0a8d2a2711f6 | CLP 8,989 | item_text="MANGUERA JARDIN ALEMANA C/TELA 1/2\""
CHANGE 11aad8a7-690e-4f26-94fb-e957debabe3f | CLP 8,579 | item_text="MANGUERA MALLAFLEX JARDIN 1/2\"(5 MT)"
CHANGE 3fa87e61-48fc-4824-9b96-4dcd3b5bba72 | CLP 32,800 | item_text="MANGUERA JARDIN RAYADA ECONOMICA 1 2 -@"
CHANGE 408b79df-bc52-43ed-9472-264629414cd7 | CLP 5,600 | item_text="TERMINAL CONECTOR RAPIDO 1/2-3/4 GARDTECH -@"
CHANGE 4e72bf19-f7d4-4bf5-8d53-5639092f37f9 | CLP 11,288 | item_text="MANGUERA MALLAFLEX JARDIN 1/2\"(5 MT)"
CHANGE 6b6af1ca-deb5-4d39-8a47-f78da263a22d | CLP 26,560 | item_text="MANGUERA JARDIN GOMA RAYA VERDE AMA 3 4 -@"
CHANGE 84277d00-6953-4265-8db7-1d0ba46dd136 | CLP 2,219 | item_text="CONECTOR RAPIDO 1/2 C/STOP REHAU (268133300)"
CHANGE 85c9eb87-6d10-446e-bb73-e4eab25c0bc4 | CLP 17,952 | item_text="MANGUERA JARDIN 3 4 P COLOR VERDE 19MM 24MM ROHS -@"
CHANGE a4420ab7-21c2-4a1e-8d91-eff4b0ba851c | CLP 15,558 | item_text="MAYI6 KIT MANGUERA JARDIN VERDE C ACCES 1/2 X 20MTS DVP -@"
CHANGE ba748027-c1bd-4491-9195-d1ce05da0bcc | CLP 487 | item_text="TERMINAL CONECTOR RAPIDO 1/2-3/4 GARDTECH -@"
CHANGE e75594b1-d29c-4166-a799-6fe7e99c601a | CLP 18,128 | item_text="SET MANGUERA JARDIN C ACCE Y SOPORTE X 18MT GARDTECH -@"
CHANGE e91600c9-b179-450a-957d-0188572c2e85 | CLP 21,448 | item_text="MANGUERA MALLAFLEX JARDIN 1/2\"(5 MT)"
CHANGE e98d6737-258d-4b7a-a854-e656494beffe | CLP 2,620 | item_text="CONECTOR RAPIDO 1/2 CON AUTOSTOP GARDTECH -@"
CHANGE ea13f7db-13ec-483d-9c4c-eb7e8cb80534 | CLP 22,992 | item_text="MANGUERA JARDIN ALEMANA C/TELA 3/4\""
CHANGE 043efa40-3c0b-4702-9e49-0bb67f8121e0 | CLP 5,925 | item_text="Teflon Jumbo 3/4 50mts Taumm"
CHANGE 0ca0579b-251f-45f8-809d-50bc98b3edd3 | CLP 6,619 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE 2d9283e6-904d-4a0b-a8be-d502858a33f4 | CLP 483 | item_text="CINTA TEFLON MAESTRO 3/4 041704003 TAUMM -@"
CHANGE 4152110d-e717-4bec-b515-904916e93ed1 | CLP 431 | item_text="TEFLON MAESTRO 3/4\""
CHANGE 58246e09-5220-486b-aaff-1d6397939f88 | CLP 287 | item_text="TEFLON MAESTRO 1/2\""
CHANGE 5d11ff89-dc8c-4687-981a-735b3e2d703a | CLP 6,571 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE 5e699968-139c-44b3-a014-fa63803fc9ab | CLP 300 | item_text="TEFLON 1/2 X 10MT BASIC CUN12C"
CHANGE 603c7782-edcb-4ee4-a654-fe75daf72af6 | CLP 281 | item_text="TEFLON MAESTRO 1 2 AGUA 10 MT ROJO AQUAKIT -@"
CHANGE 65865a62-c9e9-41d0-96f9-77f48474ef26 | CLP 5,529 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE 66320730-5b7b-41d0-98df-c2262353b2c1 | CLP 435 | item_text="TEFLON MAESTRO 3/4\""
CHANGE 784007fd-111d-48e6-962b-6f14eef8598c | CLP 5,529 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE 7a00445c-520d-45e7-9a04-195db8a13cbf | CLP 193 | item_text="CINTA TEFLON AGUA 1/2 X 10MT RAYUN -@"
CHANGE 81544ef5-0320-427e-bb00-31da2e42a756 | CLP 542 | item_text="TEFLON MAESTRO 1\""
CHANGE 8544bb4c-0b32-4a78-8cbb-ff3994fdeca3 | CLP 8,360 | item_text="TEFLON MAESTRO 3/4\""
CHANGE 9252abae-a0e9-49ad-8f57-ef8637d80c58 | CLP 6,571 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE 97514907-b9dc-4aeb-9e17-6d23cb92756b | CLP 6,321 | item_text="TEFLON MULTIUSO 3 4 ALTA DENSIDAD 50MT AZUL AQUAKIT-@"
CHANGE a185d68b-1b28-42f6-acb4-44a2ea9ff89b | CLP 551 | item_text="TEFLON MAESTRO 1\""
CHANGE a1f82876-9828-456e-819d-fc95f072e800 | CLP 10,535 | item_text="TEFLON MULTIUSO 3 4 ALTA DENSIDAD 50MT AZUL AQUAKIT-@"
CHANGE a900cbd7-a5e2-4e27-b5e2-3c1a75641936 | CLP 420 | item_text="CINTA TEFLON MAESTRO 3/4 041704003 TAUMM -@"
CHANGE ce398ccc-932c-4d2c-a07a-17f4db03d8ec | CLP 435 | item_text="TEFLON MAESTRO 3/4\""
CHANGE d388dfff-5313-4629-8ed3-7f272737c76f | CLP 5,529 | item_text="CINTA TEFLON GENEBRE 50 MTS X 19 MM -@"
CHANGE eb88fa0e-c1ba-41d0-94fa-cd6c5c6d20ea | CLP 287 | item_text="TEFLON MAESTRO 1/2\""
ASSERTION PASSED: rows about to change (539) == proposal length (539)
DRY RUN COMPLETE — no PostgREST client was created and nothing was written.
```
