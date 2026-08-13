"""Guards that survive into v1.3.3.

The v1.3.2 build carried ten Spanish word-list rules here, each tuned to one
batch of invoices. They were removed: batch-specific corrections belong in the
batch data, not the deployed decision path. What remains is one structural rule
plus the pre-existing v1.3.1 guards.
"""
import pytest

from app.inference.ambiguity_guard import model_review_guard_reason as guard


@pytest.mark.parametrize(
    "item_text, description, predicted",
    [
        # Rows the replay auto-accepted on the provider alone, because the item
        # name carries no word a text model could read.
        ("61891841", "27054", "EXP-13.1"),
        ("G93", "G93", "EXP-14.2"),
        ("000370017", "", "ADM-2.1"),
        (".", "", "EXP-14.4"),
    ],
)
def test_unreadable_item_names_are_reviewed(item_text, description, predicted):
    assert guard(item_text, description, predicted) == "item_name_carries_no_classifiable_text"


def test_a_real_description_carries_a_coded_item_name():
    """A bare code is fine when the description says what was bought."""
    assert guard("DETALLE", "GASOLINA NU 1203| 94.146|L", "ADM-1.4") is None


@pytest.mark.parametrize(
    "item_text, description, predicted, expected",
    [
        ("REVISION TECNICA CAMIONETA", "", "EXP-13.3", "ambiguous_vehicle_vs_machinery_inspection"),
        ("servicio", "", "EXP-15.5", "generic_item_name_requires_review"),
        ("APLICACION FERTILIZANTE MAITEN", "", "EXP-6.5", "fertilizer_type_requires_review"),
        ("GUANTES NITRILO L", "", "EXP-16.1", "client_examples_conflict_with_glove_taxonomy"),
        ("R.N.PIBOTE RIEGO R 24", "", "EXP-13.2", "irrigation_context_conflicts_with_prediction"),
        ("Electricidad consumida 8640 KwH", "", "EXP-11.1", "electricity_requires_exact_meter_or_lookup"),
    ],
)
def test_v1_3_1_guards_still_apply(item_text, description, predicted, expected):
    assert guard(item_text, description, predicted) == expected


@pytest.mark.parametrize(
    "item_text, predicted",
    [
        # Every one of these was gated by a removed word list. They must now
        # reach the normal confidence policy like any other row.
        ("Arriendo Televía", "EXP-15.4"),
        ("WD-40 226 GRS", "EXP-7.0"),
        ("TORNILLO VOLCANITA ZINCADO ( 100 UNID.)", "EXP-7.0"),
        ("LAVAPARABRISAS, 5LT", "EXP-7.0"),
        ("TRASL.VACAS PREÑADAS", "EXP-2.3"),
        ("SERVICIO DE TRASLADO", "EXP-14.1"),
        ("GALLETA COSTA DONUTS LECHE 100 GR", "EXP-10.1"),
        ("Nitrogeno liquido", "EXP-16.2"),
        ("Renta de Arrendamiento Nº7 del contrato Nº3435", "ADM-1.7"),
        ("Periodo de Cobertura enero 2025", "ADM-2.2"),
        ("Comisión por Transferencia Electrónica de Fondos", "ADM-1.8"),
        ("Disco SSD KNG 500GB M.2 2280 NVMe PCIe", "EXP-13.3"),
        ("dias trabajados", "EXP-14.2"),
    ],
)
def test_removed_word_lists_no_longer_gate(item_text, predicted):
    assert guard(item_text, "", predicted) is None


def test_guard_tolerates_a_missing_prediction():
    assert guard("GASOLINA 93", "", None) is None


def test_no_product_vocabulary_remains_in_the_module():
    """Regression: keep batch vocabulary out of the deployed decision path."""
    from pathlib import Path

    import app.inference.ambiguity_guard as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]  # skip the module docstring's explanation
    for banned in ("galleta", "tornillo", "televia", "nitrogeno", "wd40", "arrendamiento", "ssd"):
        assert banned not in body.lower(), f"batch vocabulary leaked back in: {banned}"
