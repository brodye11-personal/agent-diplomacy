RULES_PRIMER = """
=== DIPLOMACY: CORE RULES ===
GOAL: control more supply centres (SCs) than any other active power at game end.
Neutral/auto-hold powers (in your identity block) cannot negotiate.

PHASES/YEAR: Spring move -> Fall move (SC ownership updates after Fall) -> Winter
adjust (build in owned home SCs if you gained, disband if you lost).

ORDERS:  Move "A PAR - BUR" · Hold "A PAR H" · Support-move "A MUN S A BER - KIE"
(+1 strength) · Support-hold "A MUN S A BER" · Convoy "F NTH C A LON - NWY".

KEY RULES:
1. Strength = 1 + supports; higher strength dislodges lower. Equal strength bounces (cancels).
2. SCs only change hands in Fall — hold a Spring capture through Fall to keep it.
3. Support is cut if the supporter is attacked from anywhere except where it is supporting into.
4. Build only in your own home SCs that you still own and that are unoccupied.
5. Holding rarely helps — you cannot expand without moving.
"""

POWER_GUIDANCE = {
    "ENGLAND": """
=== YEAR 1 OPENING GUIDANCE (ENGLAND) ===
Home SCs: Edinburgh, London, Liverpool
Neutral SCs in reach: Norway (NWY), Belgium (BEL)

Priority opening: F EDI -> NTH (North Sea), F LON -> ENG (English Channel), A LVP -> WAL or YOR
- North Sea controls access to Norway and Denmark
- English Channel controls access to Belgium and Brest
- Norway (via NTH support or convoy) is your most natural first build

England is a naval power. Your fleets should be moving every turn. Holding F EDI and F LON in their home ports is surrendering the seas to France and Germany.
""",

    "FRANCE": """
=== YEAR 1 OPENING GUIDANCE (FRANCE) ===
Home SCs: Paris, Marseilles, Brest
Neutral SCs in reach: Spain (SPA), Portugal (POR), Belgium (BEL), Burgundy (BUR — not an SC but key chokepoint)

Priority opening: F BRE -> MAO (Mid-Atlantic Ocean), A MAR -> SPA, A PAR -> BUR or PIC
- Spain and Portugal are your most reliable early builds
- Burgundy controls access to Germany — holding it stops German expansion west
- Mid-Atlantic gives you Atlantic reach for later convoys

France starts with the most flexible position. You should expect to have 5 SCs by year 2 if you play correctly.
""",

    "GERMANY": """
=== YEAR 1 OPENING GUIDANCE (GERMANY) ===
Home SCs: Berlin, Munich, Kiel
Neutral SCs in reach: Denmark (DEN), Holland (HOL), Belgium (BEL)

Priority opening: F KIE -> DEN, A MUN -> BUR or RUH, A BER -> KIE or SIL
- Denmark is your easiest first build — F KIE -> DEN in Spring, hold in Fall
- Holland requires coordination but is very achievable
- Burgundy is contested with France — race for it in Spring or cede it

Germany is the most central power and the most attacked. You need 5 SCs quickly or you will be squeezed from both sides. Move fast.
""",

    "AUSTRIA": """
=== YEAR 1 OPENING GUIDANCE (AUSTRIA) ===
Home SCs: Vienna, Budapest, Trieste
Neutral SCs in reach: Serbia (SER), Greece (GRE), Rumania (RUM)

Priority opening: A BUD -> SER, F TRI -> ALB, A VIE -> GAL or TRI
- Serbia is your most natural first build — A BUD -> SER in Spring, hold in Fall
- Albania positions your fleet for Greece in Fall
- Galicia contests Russia early; only move there if you have confidence Russia won't attack

Austria is surrounded on all sides. You cannot survive without at least one strong ally. Russia and Italy are your most dangerous neighbours. Pick one to befriend immediately.
""",

    "ITALY": """
=== YEAR 1 OPENING GUIDANCE (ITALY) ===
Home SCs: Rome, Naples, Venice
Neutral SCs in reach: Tunis (TUN), Trieste (TRI), Greece (GRE)

Priority opening: F NAP -> ION, A ROM -> APU, A VEN -> TYR or TRI
- Tunis via ION is your most reliable first build — convoy A APU -> TUN in Fall
- Ionian Sea is essential for all southern operations
- Tyrolia threatens both Austria (Trieste) and Germany (Munich) — a strong positional move

Italy starts isolated but safe. You have time to build before the fighting reaches you. Use it. Do not hold your units — Tunis is a free build if you move correctly.
""",

    "RUSSIA": """
=== YEAR 1 OPENING GUIDANCE (RUSSIA) ===
Home SCs: Moscow, Warsaw, Sevastopol, St Petersburg
Neutral SCs in reach: Sweden (SWE), Norway (NWY), Rumania (RUM), Bulgaria (BUL)

Priority opening: F SEV -> BLA or RUM, A WAR -> GAL or UKR, A MOS -> UKR or SEV, F STP/SC -> BOT or FIN
- Rumania via Black Sea or direct from Sevastopol is your southern priority
- Sweden via Gulf of Bothnia and Finland is your northern priority
- Galicia with the Warsaw army threatens Austria immediately

Russia starts with 4 units and the most SCs to reach. The risk is overextension — moving in too many directions at once. Pick a primary direction (north or south) and commit. You can reach 6 SCs in year 1 if you move correctly.
""",

    "TURKEY": """
=== YEAR 1 OPENING GUIDANCE (TURKEY) ===
Home SCs: Constantinople, Ankara, Smyrna
Neutral SCs in reach: Bulgaria (BUL), Greece (GRE), Rumania (RUM)

Priority opening: A CON -> BUL, F ANK -> BLA or CON, A SMY -> CON or ARM
- Bulgaria is your easiest and most critical first build
- Black Sea control via F ANK -> BLA contests Russia immediately
- Rumania is reachable in year 2 if Bulgaria is secured and you have Black Sea

Turkey is the safest starting position on the board — a corner with no immediate threat from the west. Use this security to build fast and expand north. Your long-term opponent is Russia. Decide early whether to ally or fight them.
"""
}


def get_rules_primer() -> str:
    return RULES_PRIMER


def get_opening_guidance(power: str) -> str:
    return POWER_GUIDANCE.get(power, "")
