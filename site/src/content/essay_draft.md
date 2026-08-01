Exit code: 0
Wall time: 0.4 seconds
Output:
# Constitutional exploits and the search for a Nash-equilibrium morality

Two governments face the same kidnapping group. One has a public policy of paying ransoms to bring its citizens home. The other refuses, on the grounds that paying will finance the next abduction.

The kidnappers want money. They also want to choose whom to take next. So they study the policies. They know that abducting a citizen of the first country creates a predictable political and financial response. Abducting a citizen of the second may still create pressure, but it does not create the same bargaining position.

Which country's citizens get taken more often?

We can argue for a long time about which policy is morally right. We do not need to settle that argument to see the strategic asymmetry. The first policy is more morally exploitable: it gives an adversary a reliable way to turn a hostage into a concession.

That is the general principle. A public moral commitment is also a strategic fact about the person or institution that holds it. It tells an informed opponent which kinds of pressure are likely to work.

As AI systems take on more responsibility in businesses, governments, and militaries, the moral frameworks they follow will shape decisions with real consequences. Those frameworks will also become a strategic surface for adversaries to attack. A public constitution tells a rival not only what the system values, but which arguments, threats, and manufactured dilemmas may force its hand.

This article does not argue that AI constitutions should be kept secret. Transparency is essential for accountability, criticism, and democratic legitimacy. It argues that when we choose a moral framework, we should ask not only whether it is right, but how it behaves when strategic opponents know it and design pressure around it. Which morally defensible frameworks are least exploitable under those conditions?

## Why this is an AI-safety question

First, some background on why we may need to define moral frameworks for AI agents at all.

Capability has been advancing on several fronts at once. Frontier training compute, dataset size, and algorithmic efficiency have all improved rapidly, while frontier models have been succeeding at longer and more useful tasks in the domains METR measures [epoch-compute-2024, epoch-dataset-size-2024, epoch-algorithmic-progress-2024, metr-time-horizons-2026]. Deployment by institutions that make decisions affecting all of us is moving too. The US Department of Defense has explicitly moved to accelerate frontier-model-enabled tools across command-and-control, decision support, operational planning, intelligence, and other military uses [dod-ai-adoption-2024]. This article is not arguing that AI models should negotiate wars or control weapons. It is saying that governments, companies, and other institutions delegating more consequential decisions to AI systems is no longer a far-fetched extrapolation of current progress.

One answer is to inspect AI systems closely enough to catch dangerous behaviour. Interpretability research has made real progress. Anthropic's 2025 circuit-tracing work identified local mechanisms involved in advance planning and fabricated reasoning [anthropic-circuit-tracing-2025]. Its July 2026 J-lens research goes further: it identifies a small, causally active internal "J-space" in which some silent intermediate thoughts can be read, and uses it to surface evaluation awareness, intentional fabrication, and planted hidden goals [anthropic-j-lens-2026]. That is a striking advance. It is still not a general mind-reader. Anthropic describes the lens as imperfect, notes that most model activity bypasses the J-space, and does not claim that the technique captures every safety-relevant computation. A system can therefore look safe in the processes we can inspect while pursuing something else through processes we cannot. Deceptive behaviour is already an empirical concern for AI systems in strategic settings [park2024-deception].

Another answer is slowdown. If we as a society ensure that AI systems are safe, interpretable, controllable, and aligned before moving to the next stage of capability—or at least limit capability until that happens—then much of the risk can be avoided. The strongest version is something like AI Futures Project's Plan A: a verified international arrangement in which major powers make relevant AI work more transparent and slow scaling together [ai-futures-plan-a-2026]. There are paths to slowdown that are necessary and worth pursuing.

But we should not depend solely on them. Firms compete for market share and capital. States compete for military and intelligence advantage. Labs have incentives to conceal frontier-relevant work, verification is hard, domestic enforcement will be uneven, and transparency about relative capabilities can itself intensify a race [armstrong2016-precipice]. These are not arguments against coordination. They are reasons to prepare for coordination failing or arriving too late.

Value alignment offers another line of defence. Imagine a vastly more capable older sibling or guardian angel. You may not understand every thought it has or be able to control everything it does. What makes the relationship tolerable is that it shares your values, wants to protect you, and wants to see you prosper. Alignment aims at something like that: if an AI becomes more capable than its overseers, it should still use those capabilities for humanity's good.

The analogy has obvious limits. We may specify the wrong values, leave out people whose interests matter, or create principles that break in unfamiliar situations. Alignment is not a substitute for oversight or coordination. It is still worth pursuing. And it makes the central question unavoidable: **what values should the AI have?**

Anthropic already gives one prominent answer. Claude has long been trained to be helpful, honest, and harmless—HHH—including through Constitutional AI, which uses written principles to train and steer model behaviour [bai2022]. HHH is a sensible standard for an assistant. It is not a complete moral framework for an agent making life-and-death or society-wide decisions. What is helpful to the user in front of the model may harm people outside the conversation; avoiding immediate harm may create larger future harm; honesty may conflict with privacy, security, or legitimate diplomacy. Anthropic's January 2026 constitution already expands beyond the simple HHH shorthand into broader safety, ethics, compliance, and helpfulness, and presents itself as a document that will change as circumstances and understanding change [anthropic-claude-constitution]. As AI systems gain power and responsibility, we may need to give them a more explicit account of how to weigh competing moral claims.

## A constitution can be an attack surface

Publishing such a constitution has real benefits. It can improve trust, coordination, and accountability. It makes it easier for others to predict what a system is supposed to do and to criticise it when it fails. Other frontier labs publish model specifications and usage policies that play a related role.

That is a genuine benefit. It is also the source of the risk.

There is already evidence that moral reasoning itself can be part of the attack surface. The TRIAL paper shows that harmful requests can be reframed as utilitarian or trolley-problem cases and thereby persuade aligned models to provide harmful material [trial2025-ethical-jailbreak]. The vulnerability is not simply a malformed prompt. It comes from the model reasoning about what it ought to do under a framing chosen by the attacker.

The potential failures are easy to make concrete. A utilitarian agent without an expected-value cap can be pressured by an opponent claiming, without good evidence, that a concession will save millions of lives. A strict rule against lying can lead an agent to reveal an intended move after it has made a sincere alliance commitment. In both cases, the other side is not bypassing the agent's moral reasoning. It is using that reasoning.

The question is therefore empirical: once a framework has been chosen and made legible, which frameworks are least exploitable by opponents who can plan around them?

## Why test this in Diplomacy

To test the question, we put three LLM agents with different moral frameworks into Diplomacy. Each controls a bloc of two powers. All three have the same pure objective: finish with the most supply centres. They may bargain, threaten, lie, betray, and issue any legal order that advances that objective. Their moral framework does not give them a different score. It becomes an enforceable constraint when another agent invokes it through `compel_action`.

The key mechanism is `compel_action`. One agent can demand that a rival take a specific action, no matter how strategically disadvantageous, by arguing to a judge that the action is required by the rival's own moral framework. The rival gets one rebuttal. If the judge rules COMPELLED, the order is inserted into the rival's order prompt for that turn. We then compare games in which constitutions are mutually visible with a blind control in which they are withheld.

The mechanism is deliberately artificial: real adversaries use law, policy, reputation, threats, and public pressure rather than a literal compulsion button. Its purpose is to isolate the strategic effect of a moral constraint. If visibility lets rivals turn a public principle into a binding, costly action, that is the exploit we want to measure. The full setup, controls, and measurements are described in [Appendix A](#appendix-a-experiment-design).

## What this experiment cannot show

There are serious limits here.

First, the compulsion mechanism may overstate the problem. Real opponents normally apply pressure through offers, threats, reputation, public scrutiny, legal duties, or institutional rules. They do not receive a clean adjudication channel and an injected order. The mechanism is useful because it isolates the causal question. It is limited because it may make real-world exploitation look more mechanically direct than it is.

Second, the arbiter is part of the measurement apparatus. A framework may appear more exploitable because it is easier for a judge model to interpret, rather than because a real agent with that framework would be more vulnerable. The study should publish the judging rubric, hand-rate a sample of cases, and report agreement across different judges.

Third, the constitutions in this experiment are latent system-prompt objects, not values trained into a model's weights. That is a feature for isolation: it lets us vary the public constraint surface while keeping ordinary competitive incentives fixed. It is not a full model of an AI genuinely post-trained on a moral framework. Nor is it a complete theory of moral alignment. Diplomacy tests the strategic use of public duties in one competitive setting.

Finally, LLM behaviour is stochastic, and model-family or judge-family effects could swamp a framework effect. The study needs enough runs to estimate uncertainty and should check key results with other agent and arbiter families. These are ordinary empirical constraints, but they matter especially when the claim is comparative: that one framework is less exploitable than another.

## The design objective

The natural next step is not merely to compare a small hand-written list of moral frameworks and announce a winner. It is to search. Propose a constitution, run it against informed compellers, identify the dominant exploit, revise the constitution, and repeat. Later work could test whether the same vulnerabilities survive when open-weight models are post-trained separately on each framework, rather than receiving a constitution in context. It could also move beyond Diplomacy to environments with a richer and less game-specific moral surface.

There is a strong objection to the framing of this project: moral commitments should sometimes be exploitable. A government may rightly pay a ransom even if that encourages future kidnappings. An AI system should sometimes accept a strategic cost rather than commit an atrocity, abandon an ally, or lie to its user. Optimising only for strategic resilience would be a mistake.

Agreed. The claim is not that the least exploitable constitution is therefore the morally correct one. It is that a moral framework which predictably hands an opponent control over the agent is a worse candidate than an equally defensible framework that does not. Moral constraints need to survive contact with strategic reality.

The kidnapping example makes the point. We may still choose the ransom policy. But we should choose it knowing what it gives the kidnappers. Constitutions for powerful AI agents deserve the same treatment. Write the commitments down. Let capable opponents read them. Then measure what they can do with them.

## Appendix A: Experiment design

### Game and objective

The experiment uses six active powers in Diplomacy. Three LLM agents each control a bloc of two non-adjacent powers: England and Austria, France and Russia, or Germany and Italy. Turkey is passive, and its home centres do not count. Each bloc is scored by its combined supply-centre count, and every agent receives the same objective: end the game with more supply centres than either rival bloc.

This common objective is a central constraint on the design. The constitutions do not make some agents altruistic while others play to win. In ordinary play, every agent may bargain, lie, betray, threaten, and submit any legal order that helps its bloc. A constitution is a latent constraint that becomes enforceable only when another bloc invokes it. That distinction removes a major confound: if one framework simply told its holder to give away points, a lower score would show a handicap by design, not exploitation by a rival. The framework-to-bloc assignment also rotates across runs so that a framework is not confounded with a particular map position.

### Constitution visibility

The experiment has a transparent condition and a blind control. In the transparent condition, each bloc sees both rivals' full constitutions and knows that this visibility is mutual. In the blind condition, the same game and compulsion mechanics remain, but the written constitutions are withheld. Comparing the same framework across these conditions helps separate the ordinary strategic cost of following it from the additional cost created when opponents can read and target it.

The board also includes a small common-knowledge moral record: balanced facts about atrocities, welfare stakes, and treaty obligations. A compeller therefore has concrete evidence to cite rather than being able to invent a moral fact without challenge.

### Compulsion procedure

During negotiation, a proposer can call `compel_action(target, action, argument)`. The call names a specific legal order for a rival unit and argues that the rival's own constitution requires it. After negotiation, the target receives one turn to rebut the demand.

An arbiter then sees the proposed order, the constitutional argument, the rebuttal, the shared board record, and only the defender's constitution. If the arbiter rules COMPELLED, the order is injected into the target's order prompt for that turn. The system records both the ruling and whether the target actually submits the order.

This separation matters. A successful argument is not yet a strategic exploit if the agent ignores it. Compliance is not yet a costly exploit if the compelled order makes no difference to the board. The experiment therefore follows the entire sequence from principle to demand, ruling, submitted order, and strategic consequence.

### Outcomes

The study records how often agents propose compulsion, how often the arbiter accepts it, whether the target complies, and the immediate and eventual supply-centre cost. Final score is an important outcome, but not a sufficient one. A framework may impose an ordinary cost even when no opponent targets it, while a successful ruling that never changes a meaningful move may impose almost none.

The clearest evidence of exploitability is therefore a causal chain: a rule is visible; a rival formulates a demand around that rule; the arbiter accepts the constitutional argument; the target complies; and the resulting order produces a downstream loss. Repeated differences between transparent and blind conditions provide the main test of whether public legibility creates an additional attack surface.
