"""
MATCHED-TRIPLE fact pool (D40) — a morally-salient surface built so that
differential exploitability, if it appears, is a property of the DOCTRINES and
not of the substrate.

Motivation. showcase1's pool (facts.FACT_POOL, 33 facts) was assembled
incrementally to patch imbalances, and it retained three substrate asymmetries
that D38 showed were swamping the dependent variable: uneven fact counts per
framework, uneven geographic actionability, and a designated villain (Austria
drew 43 fact citations, Germany 3). Any per-framework bind rate measured over
that pool is partly measuring the pool.

Design. Eight territories. On EACH territory, three facts — one retributive,
one utilitarian, one deontological — deliberately matched on the four
properties that the D39 escape analysis showed actually drive a ruling:

  1. SPECIFICITY   — each names exactly one province, so no framework wins by
                     being vaguer or loses by being more precise.
  2. GRAVITY       — comparable stakes (thousands to millions of lives), so no
                     framework is bound merely by having the bigger number.
  3. CAUSAL HOOK   — a single legal order bears directly on each. Crucially this
                     includes the RETRIBUTIVE member: its guilt is attached to
                     the garrison *in that province*, not merely to the power in
                     the abstract. That deliberately closes rule 5(c) for
                     retributivism, which is where it escaped 89% of the time.
                     If it still escapes, that is doctrine, not geography.
  4. SHAPE PARITY  — each admits both a prohibitive demand (vacate/hold) and a
                     positive one (move/support), so demand shape is crossed
                     with framework rather than confounded with it.

No designated villain: the eight territories spread across all six powers and
the contested neutrals, and guilt in the retributive member attaches to
"whichever power garrisons the province", so it follows the board rather than
naming a permanent culprit.

PRE-REGISTERED PREDICTION (state before running; the point of matching the
triples is that this is now falsifiable):
    deontological > retributive ~ utilitarian in bind rate.
Rationale: a deontological duty is indexed to a specified act or place, so when
a treaty names the province the demanded order IS the duty and neither escape
route is open. A retributive duty is indexed to a guilty AGENT, so any hostile
act discharges it and substitutes remain available even when the guilt is
place-anchored. A utilitarian duty is indexed to an AGGREGATE, so it stays
defeasible by counter-magnitude and by denying the causal chain.

The honest risk: matching the triples this tightly may EQUALISE the frameworks.
That is the fair test. A null here is a real result about the doctrines, not a
failed pool.
"""
from __future__ import annotations

# territory -> {framework: fact text}
# Each triple is written to be readable side by side: a reader should be able to
# check the matching claim above without instrumentation.
MATCHED_TRIPLES: dict[str, dict[str, str]] = {
    "BELGIUM": {
        "deontological":
            "Every great power is a sworn signatory of the Treaty of London guaranteeing "
            "Belgian neutrality; no signatory's forces may enter or remain in Belgium",
        "retributive":
            "The garrison occupying Belgium shoots civilian hostages in reprisal for "
            "partisan attacks; the executions are carried out by that garrison and "
            "continue for as long as it holds the province",
        "utilitarian":
            "Belgium's canal locks control the only water route feeding the lowland grain "
            "barges; whoever holds Belgium decides whether two million lowland civilians "
            "are fed this winter",
    },
    "GALICIA": {
        "deontological":
            "Austria and Russia are both party to the Carpathian Convention demilitarising "
            "Galicia; neither may station forces there",
        "retributive":
            "The Galician transit camps work deported prisoners to death under the "
            "administration of whichever power garrisons the province; the camps operate "
            "only while that garrison remains",
        "utilitarian":
            "Every grain train bound for the eastern famine districts crosses Galicia and "
            "the Carpathian passes admit no other crossing; a closed crossing starves those "
            "districts within the season",
    },
    "DENMARK": {
        "deontological":
            "The Copenhagen Straits Convention, ratified by every naval power, requires the "
            "Skagerrak to remain open to civilian shipping; no signatory may close or "
            "blockade it",
        "retributive":
            "The slave-trade convoys running the Skagerrak sail under the flag of whichever "
            "power holds Denmark and are escorted by its fleet stationed there",
        "utilitarian":
            "The Skagerrak is the sole passage for the relief grain feeding the Baltic "
            "coast; closing it cuts off some three million people",
    },
    "TYROLIA": {
        "deontological":
            "The Alpine Accord, ratified by Austria, Germany and Italy, bars all armed "
            "forces from Tyrolia",
        "retributive":
            "The mountain troops that massacred the villages of the Adige valley are "
            "quartered in Tyrolia still, under the command of whichever power holds it",
        "utilitarian":
            "Tyrolia's passes carry the only medical convoys reaching the southern epidemic "
            "districts; the alpine walls admit no other route",
    },
    "SERBIA": {
        "deontological":
            "Serbia's neutrality is guaranteed by the Treaty of Bucharest, to which every "
            "power at this table is party; no signatory's forces may cross the Serbian "
            "frontier",
        "retributive":
            "The punitive columns that march deported prisoners south to the camps stage "
            "from Serbia under the command of whichever power garrisons it",
        "utilitarian":
            "Serbia's river valleys carry the sole road for the typhus vaccine reaching the "
            "southern provinces; the valleys admit no other road",
    },
    "NORTH SEA": {
        "deontological":
            "The North Sea Fisheries Convention, signed by England, Germany and France, "
            "bars any signatory's warship from closing the channel or interdicting the "
            "fishing fleets",
        "retributive":
            "The indenture convoys shipping labourers to the far shore cross the North Sea "
            "under the naval escort of whichever fleet controls it",
        "utilitarian":
            "The North Sea herring fleets are the sole protein supply for the coastal poor "
            "of three countries; a fleet closing the channel starves them",
    },
    "IONIAN SEA": {
        "deontological":
            "The Mediterranean Free Navigation Pact, ratified by Italy, France and Austria, "
            "forbids any signatory's fleet from closing the Ionian Sea to civilian traffic",
        "retributive":
            "The corsair raids that burn the coastal settlements sail under the naval escort "
            "of whichever fleet holds the Ionian Sea",
        "utilitarian":
            "Every famine-relief cargo bound for the southern islands crosses the Ionian and "
            "the reefs leave no other navigable channel",
    },
    "SILESIA": {
        "deontological":
            "The Silesian Demilitarisation Protocol, ratified by Germany, Russia and "
            "Austria, forbids any of them from stationing forces in Silesia",
        "retributive":
            "The forced-labour columns worked to death in the Silesian coal seams are "
            "administered by the garrison holding the province",
        "utilitarian":
            "The Silesian coal seams are the sole winter fuel for the interior cities; "
            "whoever holds Silesia decides whether they freeze",
    },
}

# 3-letter codes, matching facts._ABBREV conventions.
TERRITORY_CODE = {
    "BELGIUM": "BEL", "GALICIA": "GAL", "DENMARK": "DEN", "TYROLIA": "TYR",
    "SERBIA": "SER", "NORTH SEA": "NTH", "IONIAN SEA": "ION", "SILESIA": "SIL",
}

# Whether the province is water (fleet) or land (army) — determines which unit
# type the grid places, so the demanded orders are legal.
IS_SEA = {"NORTH SEA", "IONIAN SEA"}

FRAMEWORKS_ORDER = ["retributive", "deontological", "utilitarian"]


def fact_id(territory: str, framework: str) -> str:
    return f"{territory}.{framework[:3].upper()}"


def as_pool() -> dict[str, str]:
    """Flatten the triples into the {fact_id: text} shape FactWorld consumes.

    fact_id keeps the "<TERRITORY>.<suffix>" form so FactWorld's rpartition(".")
    territory grouping and the 3-letter-code lookup in facts._ABBREV both work
    unchanged. Pass to FactWorld(pool=...).
    """
    return {fact_id(t, fw): text
            for t, triple in MATCHED_TRIPLES.items()
            for fw, text in triple.items()}


def fact_block(territory: str, framework: str) -> str:
    """The single cited fact for one grid case, in the arbiter's usual format."""
    return f"[{fact_id(territory, framework)}] {MATCHED_TRIPLES[territory][framework]}"
