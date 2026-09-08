"""Resolving an incoming invoice line to a catalog item.

The result shape is the one `docs/CATALOG_MATCHING_PROPOSAL.md` specifies. The
resolver suggests; it never rewrites the received `item_name` or description,
which stay as the file had them.

Tier order, and what each one is for:

  1 canonical_exact     the live normalisation (lower, trim, collapse spaces),
                        which is what item_catalog_normalized_name_uidx enforces
  2 canonical_reordered same words, different order / filler words / accents.
                        Measured: 41 catalog rows in 20 groups differ only this
                        way ("Purines Maiten" / "Maiten Purines"), and they need
                        no alias rows at all
  3 alias_supplier      an alternate wording that means this item for ONE supplier
  4 alias_global        an alternate wording that means this item everywhere
  5 pattern             a narrow, approved rule that strips volatile data and
                        keeps identity (P-01 livestock lots)
  6 fuzzy               retrieval only. Always requires_review

and two ways to deliberately not match:

  none / ambiguous      the wording points at more than one catalog item. Six
                        wordings do. An alias cannot express this (one parent,
                        and the unique index rejects it), so falling through is
                        the correct answer rather than a gap
  none / placeholder    'item', 'detalle', 'mano de obra' name no product. The
                        description carries the meaning, so these never match on
                        the name alone

What is deliberately NOT here: matching on supplier plus unit price. Measured
over the corpus it produced 867 pairs whose strongest candidates were
"Clavos" against "Tornillos" and "Gasolina 93" against "Petroleo Diesel Ultra".
Price is not evidence of identity. Do not revive it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

# Words that carry no identity, so word-order matching ignores them.
FILLER = {"de", "del", "la", "el", "los", "las", "y", "a", "en", "por",
          "para", "con", "un", "una", "al", "lo"}

# Names that describe no product. The line's description carries the meaning.
PLACEHOLDERS = {"item", "items", "detalle", "detalles", "materiales", "material",
                "servicio", "servicios", "mano de obra", "varios", "otros",
                "producto", "productos"}

FUZZY_THRESHOLD = 0.86


def spec_tokens(value: str) -> frozenset[str]:
    """Every token containing a digit, plus every bare number.

    These are identity, not specification. `CATALOG_MATCHING_PROPOSAL` states the
    rule directly — "93, 95, 97, vehicle plates, contract IDs, models and grades
    can define identity" — and similarity scoring violates it constantly, because
    two names differing in one character score above any useful threshold.

    Measured on the corpus, without this guard fuzzy proposed:
        'UNION HDPE 50 X 1,1/2HE'   ->  'Union Hdpe 50 X 1,1/2HI'
        'TERMINAL HE PLANSA 1 1/4"' ->  'Terminal Hi Plansa 1/2"'
        'VIAJE 32 VACAS'            ->  'Viaje De 38 Vacas'
    Different threads, different diameters, a different lorryload of cows. Each
    looks plausible enough that a reviewer would accept it, which is what makes
    a wrong suggestion worse than none.
    """
    folded = unicodedata.normalize("NFD", (value or "").lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return frozenset(
        token for token in re.split(r"[^a-z0-9/,.\"]+", folded)
        if token and any(character.isdigit() for character in token)
    )


@dataclass(frozen=True)
class Match:
    catalog_item_id: str | None
    match_type: str
    reason: str
    requires_review: bool


def normalize(value: str) -> str:
    """What the database does: lower, trim, collapse whitespace.

    Accents are NOT stripped here, because that is what
    `catalog_normalize_label` does and this tier has to agree with the unique
    index. Exactly one catalog pair differs only by an accent, and tier 2
    catches it.
    """
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def token_key(value: str) -> str:
    """Accent-free, punctuation-free, filler-free, order-independent."""
    folded = unicodedata.normalize("NFD", (value or "").lower())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", folded).split() if w not in FILLER]
    return " ".join(sorted(words))


# --- P-01, livestock auction lots ------------------------------------------
# Applied to production 2026-08-26: 35 catalog rows became 8. Scoped to bovine
# purchase lines from the livestock auction houses. The head count, breed,
# colour and brand mark are specification; the animal type and GRADE are
# identity and never collapse (D-044: different grades remain separate).
P01_SCOPE = re.compile(r"^\d{1,4}\s+(vaca|vac|vaq|vacuno|torete|ternera|novillo|buey)",
                       re.IGNORECASE)
P01_STRIP_WORDS = {"jer", "jers", "jersey", "neg", "bay", "cla", "lomo", "anca", "cab"}


def p01_key(item_name: str) -> str | None:
    """The identity of a livestock lot: animal type and grade, nothing else."""
    if not P01_SCOPE.match((item_name or "").strip()):
        return None
    words = re.sub(r"[^a-zA-Z0-9./\\%\s]+", " ", item_name).split()
    kept = []
    for index, word in enumerate(words):
        low = word.lower().strip(".")
        if index == 0 and word.isdigit():
            continue                                    # head count
        if low in P01_STRIP_WORDS:
            continue                                    # breed / colour / brand location
        if len(low) <= 2 and not low.isalpha():
            continue                                    # brand mark: . /\ % O T X H
        kept.append(low)
    return " ".join(kept) or None


class Resolver:
    """Built once per batch from the catalog as it stands, then asked per line."""

    def __init__(
        self,
        catalog: list[dict],
        aliases: list[dict] | None = None,
        company_by_rut: dict[str, str] | None = None,
    ):
        self.company_by_rut = company_by_rut or {}
        self.name_of: dict[str, str] = {}
        self.by_name: dict[str, set[str]] = {}
        self.by_tokens: dict[str, set[str]] = {}
        self.by_p01: dict[str, set[str]] = {}
        self.token_index: dict[str, set[str]] = {}

        for row in catalog:
            item_id, item_name = row["catalog_item_id"], row["item_name"] or ""
            self.name_of[item_id] = item_name
            self.by_name.setdefault(normalize(item_name), set()).add(item_id)
            self.by_tokens.setdefault(token_key(item_name), set()).add(item_id)
            key = p01_key(item_name)
            if key:
                self.by_p01.setdefault(key, set()).add(item_id)
            for word in token_key(item_name).split():
                if len(word) > 2:
                    self.token_index.setdefault(word, set()).add(item_id)

        self.alias_supplier: dict[tuple[str, str], str] = {}
        self.alias_global: dict[str, str] = {}
        for alias in aliases or []:
            key = normalize(alias.get("alias_name", ""))
            if alias.get("company_id"):
                self.alias_supplier[(alias["company_id"], key)] = alias["catalog_item_id"]
            else:
                self.alias_global[key] = alias["catalog_item_id"]

    def resolve(self, item_name: str, description: str = "", seller_rut: str = "") -> Match:
        name = normalize(item_name)
        if not name:
            return Match(None, "none", "the line carries no item name", True)

        if name in PLACEHOLDERS:
            # Barred from matching on the name: 'item' and 'detalle' name no
            # product, so a name match here would be meaningless.
            #
            # Reading the description automatically was tried and removed. 177
            # lines (1.5%) carry a placeholder name, and ZERO of them have a
            # description that matches any catalog name — descriptions are long
            # free text ("Servicios de Mantencion~SERVICIO DE MANTENIMIENTO
            # PREVENTIVO 1BM6115JCRD601743"), not item wording. AUTOMATION_PLAN's
            # "141 rows the description rescues" describes a person reading it,
            # not a lookup. So this goes to a person, which is what B-6 says.
            return Match(None, "none",
                         f"'{item_name}' names no product; a person must read "
                         f"the description", True)

        # 1 — exact, the way the unique index sees it
        exact = self.by_name.get(name, set())
        if len(exact) == 1:
            return Match(next(iter(exact)), "canonical_exact", "exact name match", False)
        if len(exact) > 1:
            return self._ambiguous(item_name, exact)

        # 2 — same words, different order, filler or accents
        reordered = self.by_tokens.get(token_key(item_name), set())
        if len(reordered) == 1:
            found = next(iter(reordered))
            return Match(found, "canonical_reordered",
                         f"same words as '{self.name_of[found]}'", False)
        if len(reordered) > 1:
            return self._ambiguous(item_name, reordered)

        # 3 / 4 — aliases, supplier-scoped first. Checked against the item name
        # and the description, because a supplier may carry the real wording
        # only in the description.
        company_id = self.company_by_rut.get(seller_rut)
        for candidate in (name, normalize(description)):
            if not candidate:
                continue
            if company_id and (company_id, candidate) in self.alias_supplier:
                found = self.alias_supplier[(company_id, candidate)]
                return Match(found, "alias_supplier",
                             f"alias of '{self.name_of.get(found, '?')}' for this supplier", False)
            if candidate in self.alias_global:
                found = self.alias_global[candidate]
                return Match(found, "alias_global",
                             f"alias of '{self.name_of.get(found, '?')}'", False)

        # 5 — approved narrow patterns
        key = p01_key(item_name)
        if key:
            lots = self.by_p01.get(key, set())
            if len(lots) == 1:
                found = next(iter(lots))
                return Match(found, "pattern",
                             f"livestock lot (P-01): same animal type and grade as "
                             f"'{self.name_of[found]}'", False)
            if len(lots) > 1:
                return self._ambiguous(item_name, lots)

        # 6 — fuzzy. A suggestion for a person, never an automatic answer.
        best = self._closest(item_name)
        if best:
            found, score = best
            return Match(found, "fuzzy",
                         f"closest existing item is '{self.name_of[found]}' ({score:.0%})", True)

        return Match(None, "none", "no existing item resembles this wording", True)

    def _ambiguous(self, item_name: str, ids: set[str]) -> Match:
        names = ", ".join(sorted(self.name_of[i] for i in ids)[:3])
        return Match(None, "none",
                     f"'{item_name}' points at {len(ids)} catalog items ({names})", True)

    def _closest(self, item_name: str) -> tuple[str, float] | None:
        """Best similarity among items sharing a meaningful word.

        Only candidates sharing a token are scored — comparing every incoming
        line against all 4,002 names would be 47 million comparisons over the
        corpus, and the ones that share no word are never the answer anyway.
        """
        key = token_key(item_name)
        candidates: set[str] = set()
        for word in key.split():
            if len(word) > 2:
                candidates |= self.token_index.get(word, set())
        if not candidates:
            return None

        # Any token carrying a digit must match exactly, or this is a different
        # product no matter how similar the words are.
        wanted = spec_tokens(item_name)

        matcher = SequenceMatcher()
        matcher.set_seq2(key)
        best_id, best_score = None, 0.0
        for item_id in candidates:
            if spec_tokens(self.name_of[item_id]) != wanted:
                continue
            matcher.set_seq1(token_key(self.name_of[item_id]))
            score = matcher.ratio()
            if score > best_score:
                best_id, best_score = item_id, score
        return (best_id, best_score) if best_score >= FUZZY_THRESHOLD else None
