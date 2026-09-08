"""Checks for the catalog resolver.

Every case here is one the real corpus produced. The resolver suggests; only
matches with requires_review=False are ever applied without a person.
"""

from __future__ import annotations

from yunt.catalog import Resolver, normalize, p01_key, spec_tokens, token_key

CATALOG = [
    {"catalog_item_id": "gas93",  "item_name": "Gasolina 93"},
    {"catalog_item_id": "purin",  "item_name": "Purines Maiten"},
    {"catalog_item_id": "union",  "item_name": "Union Hdpe 50 X 1,1/2HI"},
    {"catalog_item_id": "clavos", "item_name": "Clavos"},
    {"catalog_item_id": "vacas",  "item_name": "Vacas Export"},
    {"catalog_item_id": "item",   "item_name": "Item"},
    {"catalog_item_id": "fdo_a",  "item_name": "Fundo Raices"},
    {"catalog_item_id": "fdo_b",  "item_name": "fundo  RAICES"},   # duplicate wording
]
ALIASES = [
    {"catalog_item_id": "gas93", "alias_name": "G93", "company_id": None},
    {"catalog_item_id": "gas93", "alias_name": "GASOLINA NU 1203", "company_id": "copec"},
]
COMPANIES = {"111111111": "copec", "222222222": "otro"}


def resolver() -> Resolver:
    return Resolver(CATALOG, ALIASES, COMPANIES)


def test_exact_name_resolves_without_review():
    match = resolver().resolve("gasolina  93")
    assert match.catalog_item_id == "gas93"
    assert match.match_type == "canonical_exact" and not match.requires_review


def test_same_words_in_a_different_order_resolve():
    """41 catalog rows in 20 groups differ only this way. They need no aliases."""
    match = resolver().resolve("Maiten Purines")
    assert match.catalog_item_id == "purin"
    assert match.match_type == "canonical_reordered" and not match.requires_review


def test_a_global_alias_resolves():
    match = resolver().resolve("G93")
    assert match.catalog_item_id == "gas93" and match.match_type == "alias_global"


def test_a_supplier_alias_only_applies_to_that_supplier():
    r = resolver()
    assert r.resolve("GASOLINA NU 1203", seller_rut="111111111").catalog_item_id == "gas93"
    # Same wording from another supplier is not that supplier's alias.
    other = r.resolve("GASOLINA NU 1203", seller_rut="222222222")
    assert other.match_type != "alias_supplier"


def test_a_wording_pointing_at_two_items_is_refused_not_guessed():
    """Six wordings do this. An alias cannot express it — one parent, and the
    unique index rejects it — so falling through is the answer."""
    match = resolver().resolve("Fundo Raices")
    assert match.catalog_item_id is None
    assert match.requires_review and "points at 2" in match.reason


def test_a_placeholder_name_never_matches_on_the_name():
    match = resolver().resolve("Item", description="algo largo y libre")
    assert match.catalog_item_id is None and match.requires_review


def test_fuzzy_will_not_cross_a_differing_spec_token():
    """The bug this guard exists for. 'HE' and 'HI' are different fittings, and
    similarity scoring cannot tell — it proposed this match on real data."""
    match = resolver().resolve("UNION HDPE 50 X 1,1/2HE")
    assert match.catalog_item_id is None


def test_fuzzy_will_not_cross_a_differing_number():
    match = resolver().resolve("VIAJE 32 VACAS")
    assert match.catalog_item_id != "vacas" or match.requires_review


def test_spec_tokens_are_every_token_carrying_a_digit():
    assert spec_tokens("Union Hdpe 50 X 1,1/2HI") == frozenset({"50", "1,1/2hi"})
    assert spec_tokens("Clavos") == frozenset()
    # 93 vs 95 must never be treated as the same product.
    assert spec_tokens("Gasolina 93") != spec_tokens("Gasolina 95")


def test_p01_keeps_animal_type_and_grade_and_strips_the_rest():
    """D-044: different grades remain separate. The head count, breed, colour
    and brand mark are specification."""
    assert p01_key("006 Vaq(s) EXPORT. Cab . Lomo") == p01_key("012 Vaq(s) EXPORT. Jer / Anca")
    # Grade is identity and must not collapse.
    assert p01_key("006 Vacas EXPORT.") != p01_key("006 Vacas S/G")
    # Out of scope: not a livestock lot at all.
    assert p01_key("Gasolina 93") is None


def test_an_unknown_wording_is_refused_rather_than_forced():
    match = resolver().resolve("ALGO QUE NO EXISTE EN NINGUN CATALOGO")
    assert match.catalog_item_id is None and match.requires_review


def test_normalisation_matches_what_the_database_enforces():
    # lower, trim, collapse — and NOT accent stripping, because that is what
    # catalog_normalize_label does and tier 1 has to agree with the unique index.
    assert normalize("  Gasolina   93 ") == "gasolina 93"
    assert normalize("Confección") != normalize("Confeccion")
    assert token_key("Confección de bolos") == token_key("Confeccion Bolos")
