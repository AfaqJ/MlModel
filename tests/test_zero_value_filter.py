from app.inference.line_filters import zero_value_junk_reason


def reason(item: str, description: str = "", amount=0, unit_price=None):
    return zero_value_junk_reason(
        item,
        description,
        amount=amount,
        unit_price=unit_price,
    )


def test_zero_is_not_itself_a_junk_reason():
    assert reason("Decodificadores Adicionales") is None
    assert reason("Peaje Autopista Vespucio Norte") is None
    assert reason("VENTA CAMIONETA", 'DONDE DICE "Patente" DEBE DECIR "Patente"') is None
    assert reason("CONFECCION DE BUJE DE BRONCE") is None


def test_audited_zero_value_scaffolding_is_removed():
    assert reason("--------------------------------------------------------------------------------") == "separator"
    assert reason("CODIGO DESCRIPCION", "A@CODIGO DESCRIPCION") == "printed_column_header"
    assert reason("Fecha-Guía", "04.04.25-29771090*") == "fuel_delivery_reference"
    assert reason("Total", "GASOLINA SP 93 OCTANOS NU 1203| 94,146|Litro") == "zero_fuel_summary"
    assert reason("OBSERVACIONES", "PAGO TRANSFERENCIA") == "observations_note"


def test_same_text_with_nonzero_amount_is_never_removed_by_zero_audit():
    assert reason("OBSERVACIONES", "PAGO TRANSFERENCIA", amount=1000) is None
    assert reason("Total", "GASOLINA", amount=None, unit_price=None) is None
    assert reason("61891841", "27054", amount=27054) is None


def test_zero_price_also_enables_audited_filter():
    assert reason("Comentarios:", amount=None, unit_price=0) == "comments_header"
