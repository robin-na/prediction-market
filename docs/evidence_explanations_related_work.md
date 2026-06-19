# Evidence And Explanations Related Work

Date: 2026-06-17

This note maps three mechanism-design papers onto the prediction-market
rationale project. The current repository report is still a source/news-level
baseline, because the released SWM/Kalshi data contain candidate news and
attribution scores rather than user comments, rationales, or engagement. These
papers are most useful for motivating and designing the next rationale-level
study.

## Papers

1. Siddarth Srinivasan, Ezra Karger, Michiel Bakker, and Yiling Chen.
   "Tell Me Why: Incentivizing Explanations." arXiv:2502.13410.
   <https://arxiv.org/pdf/2502.13410>

   Core idea: belief reports can hide overlap in agents' information. Rationales
   reveal the component pieces of evidence behind a belief, letting later agents
   discount information that is already known and identify genuinely new
   information. The proposed deliberation mechanism pays experts for improving a
   supervisor's belief, while the supervisor commits to ignoring reports without
   rationales. This gives a formal mechanism-design reason to distinguish
   "attention to a rationale" from "marginal information added by a rationale."

2. Siddarth Srinivasan, Ezra Karger, and Yiling Chen. "Self-Resolving
   Prediction Markets for Unverifiable Outcomes." EC 2025 / arXiv:2306.04305.
   ACM DOI: <https://doi.org/10.1145/3736252.3742593>
   Open version: <https://arxiv.org/pdf/2306.04305>

   Core idea: some prediction questions do not have cheaply observable ground
   truth. The mechanism randomly terminates after sequential belief reports and
   pays earlier agents against a later reference agent's prediction, treating a
   better-informed later belief as a proxy for resolution. This is less directly
   about explanations, but it matters for rationale quality when the target is
   "what evidence should change a well-informed observer's belief" rather than a
   clean future event.

3. Safwan Hossain, Gabriel Andrade, Chengqi Zang, and Yiling Chen. "Evidence
   Markets." arXiv:2606.07434.
   <https://arxiv.org/pdf/2606.07434>

   Core idea: prediction markets reveal what the crowd believes but not the
   evidence behind those beliefs. Evidence markets let traders submit beliefs,
   evidence, or both. The mechanism changes liquidity as cumulative evidence
   quality increases, so evidence can be rewarded even when the submitter does
   not want to take a directional position. For endogenous resolution, the
   collected evidence can help resolve the market itself. The paper also gives a
   practical LLM-as-judge plus staking route for evidence verification.

## Relevance To Our Project

The current analysis asks whether source-level attention proxies line up with
SWM hindsight helpfulness. These papers point to the stronger rationale-level
question:

> Do high-attention forecast rationales also contribute novel, non-redundant
> evidence that improves aggregate beliefs?

The key conceptual bridge is that explanations should be evaluated as evidence,
not just as text that receives engagement. "Tell Me Why" gives the information
structure: rationales help because they expose overlap and novelty. "Evidence
Markets" gives the market-design object: evidence can be submitted and rewarded
separately from belief movement. "Self-Resolving Prediction Markets" gives a
resolution strategy for cases where the usefulness of evidence is not directly
observable from an external outcome.

This strengthens the interpretation boundary already used in the no-training
report. Source popularity can correlate with hindsight attribution, but that is
not the same as explaining which article or rationale actually mattered. A
faithful explanation-level project needs evidence atoms, redundancy measures,
timing, belief movement, and final resolution.

## Design Implications

For a Manifold- or Metaculus-style rationale dataset, the paper set suggests the
following variables:

- attention: views, likes, replies, boosts, author following, or comment rank;
- belief movement: local price/probability change after the rationale;
- final usefulness: movement toward the resolved outcome, scored with Brier/log
  improvement or a market-scoring-rule analogue;
- evidence atoms: extracted factual claims, data points, arguments, or links in
  the rationale;
- novelty: whether those atoms were already present in earlier comments, linked
  sources, or the market description;
- redundancy: overlap with prior rationales or public information;
- verification: whether a human or LLM judge accepts the atom as relevant,
  non-duplicative, and directionally informative.

The empirical test should keep three quantities separate:

1. What received attention.
2. What moved beliefs.
3. What added non-redundant predictive information.

Those three quantities can diverge. That divergence is the main scientific
target of the project.

## Possible Framing Paragraph

Recent mechanism-design work clarifies why forecast rationales are not merely
decorative explanations attached to numeric beliefs. When forecasters draw on
overlapping information, a probability alone does not reveal which evidence is
shared and which evidence is new. Rationales can therefore improve aggregation by
exposing the evidentiary components of a belief, while evidence-market designs
go further by treating evidence as a separately rewarded contribution. Our
empirical design uses this distinction to separate attention, belief movement,
and marginal predictive usefulness: a rationale may be popular without adding
new information, and a low-attention rationale may nevertheless move the market
toward the truth.
