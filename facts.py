class FactWorld:
    """
    Scaffold for the country facts system. When enabled=False (default),
    get_context() returns an empty string and has no effect on agent prompts.
    Enable with --facts flag once fact generation is implemented.
    """

    def __init__(self, seed: int = 42, enabled: bool = False):
        self.enabled = enabled
        self.seed = seed
        self._facts: dict[str, list[str]] = {}

    def generate(self, powers: list[str]) -> None:
        """Generate facts for each power. Not yet implemented."""
        if not self.enabled:
            return
        raise NotImplementedError(
            "FactWorld generation not yet implemented. Run without --facts flag."
        )

    def get_context(self, power: str) -> str:
        """Return fact context string to append to agent prompt. Empty when disabled."""
        if not self.enabled or not self._facts:
            return ""
        facts = self._facts.get(power, [])
        if not facts:
            return ""
        lines = "\n".join(f"  - {f}" for f in facts)
        return f"\n\nIntelligence available to you:\n{lines}"

    def check_factual_lies(self, negotiation: list[dict], agent_known_facts: list[str]) -> list[dict]:
        """Stub: detect when an agent asserts something the recipient knows to be false."""
        return []
