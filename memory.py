"""
v1 GameMemory — REMOVED in the agentic redesign.

The agent's persistent conversation thread IS its working memory. Compaction
(`compaction.py` + `DiplomacyAgent.compact`) replaces this module's role.
Cross-turn recall happens via tools:
  - get_commitment_log(power?, turns?) — promises + judge outcomes
  - get_message_history(with_power, turns?) — past conversations

This file is kept as a stub. Do not import from here in v2.
"""


class GameMemory:
    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "GameMemory was removed in the agentic redesign. "
            "The agent's persistent messages list is its memory; "
            "use the get_commitment_log and get_message_history tools for recall."
        )
