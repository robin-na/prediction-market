# Market For Explanations Research Design

Date: 2026-06-29

This document records the current research framing, references, concerns, and
intended contribution for the market-for-explanations project. It is meant to be
the handoff document a collaborator can read before looking at scripts or pilot
outputs.

## One-Sentence Thesis

Prediction markets aggregate beliefs, but they usually do not reveal the
evidence-selection and belief-update models behind those beliefs. We study
whether explanations can be modeled as competing evidence-to-posterior update
rules, then scored by both market adoption and eventual correctness.

## Core Definition

Our working definition:

```text
explanation = a model that maps prior belief state and evidence features to a
posterior belief update

prior market state + selected evidence + update rule -> posterior belief shift
```

The explanation is not just a paragraph attached to a forecast. It contains at
least three pieces:

- evidence selection: which evidence was treated as relevant and which evidence
  was ignored;
- evidence weighting: why some evidence should matter more than other evidence;
- update calibration: how much the prior should move after seeing the evidence.

This definition is intentionally broader than "the posterior moved from X to Y."
If an explanation is defined only as "update from 0.32 to 0.47," it can overfit
the specific market transition and stop being transferable. The empirical object
should therefore be separated into levels:

```text
explanation class:
  e.g. source credibility weighting, base-rate correction, resolution-rule reasoning

update rule:
  e.g. discount this source because it has weak direct access to the target event

parameterized update policy:
  e.g. this kind of evidence should move the prior upward, but only slightly

posterior instance:
  e.g. in this market, move from 0.32 to 0.38
```

An important empirical question is whether the same explanation class leads to
similar posterior updates across markets, or whether the class is too broad to
carry stable quantitative signal. We should not assume transferability. We
should measure it.

## Core Research Question

The current central question is:

> Which explanation classes predict market belief updates, which predict final
> outcomes, and can learning this distinction improve forecasting agents?

This splits explanation value into two targets:

```text
market-update value:
  Does the explanation-implied posterior predict the next market price movement?

outcome value:
  Does the explanation-implied posterior improve payoff or scoring-rule accuracy
  after the event resolves?
```

The divergence between these two targets is the core market-specific insight:

```text
market-predictive and outcome-correct      consensus learning
market-predictive but outcome-wrong        persuasive error
market-contrarian but outcome-correct      potential trader edge
market-contrarian and outcome-wrong        bad contrarian update
```

## Why Prediction Markets Are A Good Setting

Prediction markets give us an unusually useful dual-label structure.

First, the price path provides a revealed-preference proxy for social belief
updates. If an explanation implies that probability should rise and the market
does rise afterward, the explanation is market-aligned. This is not democratic
popularity in the sense of counting how many people liked the explanation. It is
capital-weighted market adoption.

Second, the final resolution provides a separate truth or payoff target when the
market resolves. This lets us distinguish explanations that other traders seem
to adopt from explanations that were actually useful.

In short:

```text
future price movement = social adoption target
final outcome/payoff = world correctness target
```

## Relationship To Prior Work

### Hypothesis Generation With LLMs

Zhou et al. (2024), "Hypothesis Generation with Large Language Models":
<https://arxiv.org/abs/2404.04326>

HypoGeniC generates natural-language hypotheses from labeled examples and uses
them to improve classification. The closest shared idea is that language models
can generate many candidate hypotheses and those hypotheses can be evaluated
empirically.

Our distinction:

```text
HypoGeniC:
  features -> label

This project:
  prior belief + selected evidence + update rule -> posterior belief shift
```

We are not mainly studying whether LLMs can generate hypotheses. We use LLMs as
cheap proposal generators for update rules, then study which update rules are
market-adopted, outcome-correct, or transferable.

### HypoBench And Scientific Discovery Benchmarks

Liu et al. (2025), "HypoBench: Towards Systematic and Principled Benchmarking
for Hypothesis Generation": <https://arxiv.org/abs/2504.11524>

ResearchBench and related scientific-discovery benchmarks study whether LLMs can
generate plausible, useful, novel, or generalizable hypotheses. Their evaluation
is mostly about explanatory power, discovery rate, practical utility, and
interestingness.

Our distinction:

- the object is a temporal belief update rather than a static explanation of
  labeled observations;
- the evaluation has two naturally occurring targets, market movement and final
  resolution;
- the payoff interpretation is direct because a posterior can be traded against
  a market price.

### Social World Models

Yu et al. (2026), "Building Social World Models with Large Language Models":
<https://arxiv.org/abs/2606.11482>

SWM models how social beliefs evolve in response to events. It learns event
attribution and transition dynamics using prediction-market data. The released
Kalshi data give us candidate news, prior attribution scores, posterior
attribution scores, price histories, next prices, and future paths.

Important distinction:

```text
SWM:
  candidate news -> attribution score
  candidate news + market state -> predicted price shift

This project:
  candidate news + market state -> explanation/update rule -> posterior shift
```

SWM does not ask LLMs to emit written explanations in its main prompts. The
appendix prompts explicitly request numeric outputs without explanations. That
makes SWM a strong starting point: it gives the scalar skeleton of belief
movement, while our project studies the missing explanatory layer.

### Tell Me Why

Srinivasan et al. (2025), "Tell Me Why: Incentivizing Explanations":
<https://arxiv.org/abs/2502.13410>

This paper gives a mechanism-design foundation for why rationales matter. Their
rationales expose the structure of agents' private information, especially when
agents have overlapping information. The point is to identify what is shared and
what is new so later agents do not double-count evidence.

Our distinction:

- their rationale is mainly an explanation of private information;
- our explanation is a reusable model of how public or retrieved evidence should
  update a prior;
- their main question is incentive compatibility for eliciting rationales;
- our main question is empirical: which rationale/update types predict market
  movements and outcomes?

### Evidence Markets

Hossain et al. (2026), "Evidence Markets":
<https://arxiv.org/abs/2606.07434>

Evidence Markets generalize prediction markets by rewarding submitted evidence,
not just directional trades. This is close to our motivation because standard
prediction markets reveal crowd belief but not the evidence or reasoning behind
beliefs.

Our distinction:

- they design a mechanism for submitting and rewarding evidence;
- we empirically score explanation/update rules using existing market histories;
- our object is not only evidence, but the mapping from evidence to posterior.

### LLM Forecasting And Trading Benchmarks

Relevant examples include:

- Halawi et al. (2024), "Approaching Human-Level Forecasting with Language
  Models": <https://arxiv.org/abs/2402.18563>
- "ForecastBench": <https://arxiv.org/abs/2409.19839>
- "LLM-as-a-Prophet": <https://arxiv.org/abs/2510.17638>
- "Prediction Arena": <https://arxiv.org/abs/2604.07355>

These papers benchmark models or agents as forecasters and traders. Our unit of
analysis is different. We study the explanation candidate, not only the model
that generated it.

## Intended Contributions

1. Define explanations in prediction markets as belief-update models, not just
   text rationales.
2. Build an explanation ensemble for each market transition, using multiple
   models, prompts, and evidence regimes.
3. Score explanations on two separable axes: market-update accuracy and
   outcome/payoff accuracy.
4. Measure the gap between popular explanations and correct explanations.
5. Test whether explanation-level features improve prediction beyond market
   prices, raw news, and SWM-style attribution scores.
6. Produce an interpretable taxonomy of explanation classes only after showing
   that the classes carry predictive signal.

## Main Concerns And Design Safeguards

### Same Explanation, Different Posterior

The same high-level explanation class may imply different posterior magnitudes
in different markets. For example, "source credibility weighting" may move a
market by two points in one setting and twenty points in another.

Safeguard: do not collapse explanation identity into exact posterior value. Keep
separate fields for explanation class, qualitative direction, magnitude,
calibration rule, and numeric posterior. Then measure how stable the class is
across markets.

### Overfitting To The Observed Move

If we let the LLM see the after price, it can generate post-hoc rationalizations
instead of prospective update rules.

Safeguard: hide `after_p`, `price_delta`, posterior attribution scores, and
selection reasons from generation prompts. Use SWM posterior attribution only as
an oracle evidence-selection regime for taxonomy building, not as a deployable
forecasting regime.

### Information Overload

We cannot feed every piece of news into every prompt. Evidence selection is part
of the explanatory process.

Safeguard: begin with small evidence packets from existing SWM candidates. Use
three regimes: deployable prior-selected evidence, oracle posterior-selected
evidence, and mixed candidate packets with distractors. Later, make retrieval
policy itself part of the explanation.

### Market Movement Is Not Pure Popularity

Price movement is a capital-weighted, marginal signal. It is not the same as
counting how many agents found an explanation persuasive.

Safeguard: call the first metric market-update accuracy or market adoption, not
generic popularity. Add volume, persistence, cross-market agreement, comments,
likes, or social reuse only if those data become available.

### Outcome Labels May Be Incomplete

Some SWM rows may not have final resolved outcomes joined cleanly. Short-horizon
future price paths are available earlier than final event resolution.

Safeguard: separate market-update scoring from outcome scoring. Start with
one-step and future-path scoring, then add final-resolution scoring where
available.

### LLM Explanations Can Be Plausible But Empty

LLMs can generate persuasive narratives with weak evidentiary grounding.

Safeguard: require structured outputs: selected evidence IDs, ignored evidence
IDs, direction, magnitude, posterior, update rule, mechanism class, and
calibration rationale. Audit a sample manually before scaling.

## Empirical Claim We Need To Prove

The project is strong only if explanation-level features contain reusable signal
beyond simpler baselines:

```text
market prior
price history
raw news text
SWM prior attribution
SWM posterior attribution, in oracle analyses only
generic LLM forecast without structured explanation
```

If explanation features do not improve prediction, the contribution is still a
descriptive map of explanation types, but it is weaker. The strongest result
would show that learned explanation classes improve forecast calibration,
directional accuracy, payoff, or event attribution in held-out markets.

## Current Next Step

Run the explanation-ensemble pilot described in
`docs/explanation_pilot_design.md` using the existing 100-row Kalshi/SWM pilot
dataset.
