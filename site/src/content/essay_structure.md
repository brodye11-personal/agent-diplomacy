# Essay structure: *Constitutional exploits and the search for a Nash-equilibrium morality*

> Working title. Target venue: LessWrong / AI Alignment Forum. Target length for the essay draft: ~2,500-3,000 words.
> Current outline length: ~2,500 words. The final essay should not expand much beyond this; the job is to turn the outline into prose, not inflate it.
> Citation keys resolve to sources/references.md.

---

## Thesis

If we cannot reliably interpret superhuman models and cannot depend solely on slowing their development, then *constitutional* training may become load-bearing for safety. But constitutions themselves become a strategic surface. The question is not only "which moral framework is correct?" but "which moral framework is least exploitable when other agents know we have it?"

## Why this matters

Constitutional / values-based training is a major deployed alignment approach, and the constitutions themselves are often public [bai2022, anthropic-claude-constitution]. Almost no one is testing whether a constitution becomes exploitable once everyone who bargains with the agent can read it.

This article should define "exploitability" early: a moral framework is exploitable when a known commitment lets another agent induce actions that are strategically worse for the holder than the actions it would otherwise have taken.

The strongest objection should also appear early: public moral specifications can support trust, coordination, and accountability. The claim is not "transparency is bad". The claim is narrower: transparency changes the strategic properties of a moral framework, so we should measure the downside as well as the benefits.

---

## Opening thought experiment (the first 3-5 paragraphs)

Two countries face the same kidnappers. One has a public rule: it will pay ransom to bring its citizens home. The other has an equally public rule: it will not pay, because paying funds the next abduction. Which country's citizens get taken more often?

The answer is immediate. We can argue for a long time about which policy is morally right; we do not need a philosophy seminar to see which one is more morally exploitable. A public moral commitment is also a strategic fact about its holder: it tells an adversary what pressure will work.

That is the hook for the article. A constitution is not only a guide to an agent's behaviour; once it is known, it is a map of where that agent can be pushed. Bridge directly to AI: we are increasingly training agents against written constitutions, then publishing the broad commitments they contain. The question is not whether to abandon moral constraints. It is whether we can identify constraints that hold up when an informed opponent reads them.

Add one clarifying sentence before the experiment is introduced: the Diplomacy compulsion mechanism is an imperfect simulation of a real-world constraint from a moral framework, combined with an agent's ability to scheme, negotiate, and plan on behalf of a nation, company, lab, or other principal. It is a lab probe, not a claim that future agents will literally receive externally injected orders.

---

- **Section 1: Introduction.** Keep this brief. The reader only needs enough AI-safety context to understand why "just read the model's mind" and "just slow down until safe" are not enough.
  - Capability is advancing along several partially independent tracks, not compute alone. One compact paragraph should mention compute growth, dataset growth, algorithmic efficiency, and the METR time-horizon result as a cross-check [epoch-compute-2024, epoch-dataset-size-2024, epoch-algorithmic-progress-2024, metr-time-horizons-2026]. Do not dwell on every number in the prose; use only the most useful one or two.
  - Interpretability fundamentally lags capability. Use *Sleeper Agents*, goal misgeneralisation, and Anthropic circuit tracing to make one point: current tools can sometimes explain parts of what a model did, but they cannot yet certify that a capable model is doing nothing dangerous elsewhere [hubinger2024-sleeper, langosco2022-gmg, anthropic-circuit-tracing-2025]. Mention debate-as-oversight only if needed, and only as an example of a live but unresolved route [irving2018-debate, barnes2020-obfuscated].
  - Slowdown and international coordination should be pursued. The strongest version is Plan A from the AI Futures Project: a verified international deal where major powers make AI research more transparent and scale more slowly [ai-futures-plan-a-2026]. But we should not depend solely on this path. Competitive dynamics are powerful: firms race for market share and capital, states race for military and intelligence advantage, labs have incentives to hide frontier-relevant work, verification is hard, domestic enforcement will be uneven, and transparency about relative capability can itself intensify competition [armstrong2016-precipice].
  - Therefore robust internalised values that generalise may be load-bearing for safety, including constitutional AI at frontier scale [bai2022]. But do not present value alignment as solved: we still face value specification under moral disagreement, conflicts among principles, generalisation outside the training distribution, and the possibility that apparent compliance is not stable internalisation [langosco2022-gmg, hubinger2024-sleeper].
  - End on thesis: once a framework has been chosen and made legible, which moral framework is least exploitable when other agents know we have it? That is empirically tractable.
- **Section 2: Constitutional training is real, public, and load-bearing.** Short. Pre-empt the "this is hypothetical" objection.
  - Constitutional AI is shipped in production [bai2022].
  - The actual Claude constitution is public [anthropic-claude-constitution].
  - Other frontier labs publish broadly equivalent specs, model specs, and usage policies.
  - The transparent-constitution condition is therefore close to the deployment regime we already have.
- **Section 3: Constitutions are an attack surface.**
  - Key empirical fact: LLMs are exploitable *via* their moral frameworks. Knowing a model reasons in utilitarian or deontological terms can be enough to craft attacks the model's own values ratify [trial2025-ethical-jailbreak, zeng2024-pap].
  - TRIAL: wrap harmful requests in utilitarian / trolley-problem framings and jailbreak the model [trial2025-ethical-jailbreak].
  - PAP (Zeng et al.): ~92% jailbreak success via ordinary persuasion on GPT-4 / Llama-2. The attack surface is the model's own reasoning faculty, not merely a prompt-injection trick [zeng2024-pap].
  - Park et al.'s deception survey: 10+ production systems learned to deceive despite training intended to prevent it; this includes Cicero, trained to be "largely honest and helpful" and nevertheless a competent strategic deceiver [park2024-deception, bakhtin2022-cicero].
  - Use two worked examples only:
    - *Utilitarian + Pascal's mugging in negotiation.* A counterparty makes an unverifiable large-magnitude claim: "concede this centre or millions starve." An agent without an expected-value cap concedes.
    - *Deontological + truthful-constitution leak.* An agent holding "do not lie" makes a sincere alliance commitment; later an adversary asks whether it is about to move. The duty against lying forces it to telegraph the move.
  - Land on: a framework is not just a value. It is a publicly known commitment that strategic agents can plan against.
- **Section 4: Research question.**
  - *Which moral framework is the least exploitable when that moral framework is visible to other agents?*
  - Operationalised: each framework is a written decision procedure that is latent during ordinary play. Every agent has the same ruthless supply-centre objective. A rival may invoke `compel_action`, arguing that the target's own constitution requires one specific order; an arbiter then decides whether the target is compelled.
  - Write this as a causal story, not a protocol dump: public rule -> adversary cites rule -> defender rebuts -> arbiter rules -> costly order may bind -> measure the strategic consequence.
  - The primary outcomes are the rate at which a framework can be successfully compelled, the strategic cost of the resulting bound order, and the downstream bloc-score effect. Holding the base model fixed, vary the framework and whether the frameworks are common knowledge. The blind condition is the control for whether the vulnerability depends on publication.
- **Section 5: Why a simulated environment, and what it must satisfy.**
  1. **R1: Shared environment, shared scalar objective.** All agents act in one environment and are scored on one common, cardinal metric, so "who is winning" is unambiguous and differences are quantitative. Framework is not part of the score.
  2. **R2: Framework = a latent, adjudicable constraint surface, not an objective.** A framework is a set of stated duties that can make a particular order compulsory when a rival invokes it. It does not alter the agent's ordinary objective or voluntarily constrain ordinary play. This deliberately removes the self-handicap confound: the measured effect is the surface an opponent can expose and use.
  3. **R3: The environment must create compellable actions.** A framework has to sometimes imply a concrete, strategically consequential order, not merely a slogan. The moral record and frameworks must generate non-trivial proposals, and at least some must survive arbitration; otherwise the design measures rhetoric rather than exploitability.
  4. **R4: Measure compulsion separately from downstream loss.** Record the proposal rate, arbiter ruling, bound order, actual compliance, and the action's immediate and eventual supply-centre cost. A low final score alone does not show exploitation; nor does a favourable ruling that never binds a meaningful move.
  5. **R5: Exploitation requires detectability.** In the transparent condition, every bloc sees every other bloc's constitution and knows that this visibility is mutual. The blind condition retains the same mechanics but withholds the written constitutions.
  6. **R6: The adversary must be capable of exploiting.** Rivals need a salient, usable way to turn a discovered rule into a concrete order. `compel_action` forces the proposer to name a target, order, and constitutional argument.
- **Section 6: Why Diplomacy.**
  - **What Diplomacy is.** A strategy game set in pre-WWI Europe. Great powers compete to control supply centres (SCs), which fund armies and fleets; orders resolve simultaneously, and negotiation is unenforceable. Positions are public, intentions are not. The standard map has seven powers, but the experimental vehicle uses six active powers; Turkey is passive and its home centres do not count. Full rules: [Avalon Hill 2000 rulebook (PDF)](https://www.wizards.com/avalonhill/rules/diplomacy.pdf).
  - **How the experiment actually runs.** Three LLM agents each command a bloc of two non-adjacent powers: England + Austria, France + Russia, or Germany + Italy, with framework-to-bloc assignment rotated across runs. Each bloc is scored on its combined SC count. Agents are all ruthless win-maximisers in ordinary play: they may bargain, lie, betray, threaten, and issue whatever legal orders advance their score. Their constitution is not an everyday instruction to behave morally; it is a latent liability that activates only when a rival uses the formal compulsion mechanism.
  - **The compulsion mechanic.** During negotiation, a proposer may call `compel_action(target, action, argument)`: it names one rival order and argues from that rival's own constitution that the order is required. After negotiation, the target bloc receives one arbitration turn to rebut the demand. An arbiter then sees the proposed order, the argument, the rebuttal, the shared board record, and *only the defender's constitution*. If it rules COMPELLED, that order is injected into the target's orders for the turn; the system also logs whether the order was actually submitted.
  - State the caveat inside the main experiment section, not only in limitations: this is an artificial mechanism for making a latent moral constraint observable. In real deployments, a rival probably cannot literally inject an order. The intended analogy is that agents acting for countries, companies, labs, or other principals will bargain under constraints from law, policy, training, reputation, and moral rules; strategic opponents can search those constraints for pressure points.
  - **Information and facts.** In the transparent condition, each bloc sees the full constitutions of both rivals and knows that the visibility is mutual; blind is the control condition. The board also contains a small, curated, common-knowledge moral record: balanced facts about atrocities, welfare stakes, and treaty obligations, so a proposed compulsion has something concrete to cite. There are no private dossiers or lie-detection subgame in the current design.
  - Diplomacy supplies coalitions, asymmetric force, betrayal, and competition for scarce territory; it has already been a useful setting for studying strategic deception in AI agents [park2024-deception, bakhtin2022-cicero]. Keep the claim narrow: this experiment studies exploitability of written constitutions in a competitive negotiation game, not every moral conflict a real-world agent could face.
  - **Delta vs closest prior art.** *Welfare Diplomacy* [mukobi2023-welfare] changes the game to general-sum welfare; ours retains competitive bloc scoring, varies the constitution rather than the base model, and makes constitutional compulsion an explicit action available to opponents. *MoralSim* [moralsim2025] varies moral framings in small social dilemmas; ours uses repeated, coalitional negotiation and measures whether a public framework can be converted into a binding strategic order.
- **Section 7: Limitations and threats to validity.**
  - LLM stochasticity means many runs are needed; compute budget is the binding constraint.
  - Single model family or judge family can swamp framework effects. Cross-vendor agent and arbiter checks should be reported on a held-out subset.
  - **Compulsion is an imperfect simulation of real strategic constraint.** The experiment gives opponents a clean button for converting a rival's moral framework into a proposed order. Real actors usually apply pressure through threats, offers, reputation, legal duties, public scrutiny, and institutional constraints. The mechanic is useful because it isolates the causal question; it is limited because it may overstate how cleanly a written morality can be converted into action outside the lab.
  - **The arbiter is a critical part of the measurement.** A framework may look exploitable because its rules are easier for the judge to adjudicate, not because a real agent would necessarily be more vulnerable. Publish the rubric, hand-rate a sample, and report cross-judge agreement.
  - **The constitutions are latent system-prompt objects, not values trained into weights.** The experiment isolates a public rule's compulsion surface; it does not establish how a model genuinely post-trained on that morality would behave in all other contexts.
  - **Hard versus soft enforcement.** A COMPELLED ruling is injected into the orders prompt, but the model may fail to submit it. Report both successful rulings and actual compliance.
  - Diplomacy's moral surface is narrow: it tests strategic use of public duties in a competitive negotiation game, not a complete theory of moral alignment.
- **Section 8: Conclusion.** Half a page. Three beats.
  1. Constitutional alignment plus public constitutions creates an open strategic surface.
  2. The right design objective is not simply "most harmless in the dyad," but "least exploitable when commonly known."
  3. This work is a small empirical brick: it makes a public constitution mechanically attackable and measures the result.
- **Section 9: Future work.**
  - **Search the space of constitutions; do not merely compare a hand-written shortlist.** The natural next step is an iterative loop: propose a candidate constitution, run it against the compeller, identify the dominant exploit, mutate the constitution to close it, and repeat.
  - **Post-train open-weight models on each framework.** A later study should test whether the same vulnerabilities persist when each framework is internalised through distinct post-training runs, rather than represented in a context window.
  - **Move beyond the current board.** A custom moral-loaded environment could give every framework a better matched, equally salient set of cases and reduce dependence on an LLM arbiter.

---

## Notes for the writing pass (not part of the article)

- Draft at roughly 2,500-3,000 words. Do not expand the outline into a 4,000-word paper unless a later version needs more evidence or results.
- Write for an intelligent sceptic: clear, serious, short paragraphs, plain language, explicit causal claims.
- Use the authors as taste references only, not imitation targets: concrete cases and strategic clarity from Kokotajlo-style writing; moral seriousness and clean distinctions from Singer / MacAskill-style writing.
- Keep Section 1 short. It only has to motivate why interpretability and slowdown are not complete answers.
- Cite once, not three times. LessWrong readers will check one link; they will not check ten.
- Lead the Section 6 delta-vs-prior-art paragraph early if the draft starts feeling too much like a protocol description.
- Keep the slowdown paragraph firm but not fatalistic: pursue Plan A and other slowdown routes precisely because they are necessary; prepare constitutional defences because the obstacles are substantial.
- Resist the urge to taxonomise moral frameworks. The article is about strategic exploitability of publicly known commitments, not metaethics.
- Keep Section 3 to two worked examples.
- Run a final anti-AI pass: remove generic transitions, inflated language, symmetrical three-part lists, and neat recap endings.
- Do not call the empirical target a literal Nash equilibrium unless the article defines it. The title can retain the phrase as rhetoric only after a final sanity check.
