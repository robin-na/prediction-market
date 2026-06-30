---
name: market-explanation-feedback-deck
description: Build early-stage feedback decks for the market-for-explanations project.
---

# Market Explanation Feedback Deck

Use this skill when creating or revising a short feedback deck for collaborators who are new to the project and may have limited LLM background.

## Audience

- Assume readers know basic forecasting or markets, but not this project.
- Avoid unexplained LLM jargon. When LLMs appear, describe them as generators of candidate explanations and posterior forecasts.
- The purpose is feedback on framing and research design, not a polished final-result talk.

## Visual Style

- Match the project reference deck style: white background, Trebuchet MS, sparse black/dark-gray text, and restrained maroon accent.
- Keep slides simple: one idea per slide, light diagrams, no decorative graphics.
- Use small diagrams for process and definitions. Do not overbuild visuals.
- Prefer rendered thumbnail QA before delivery, because Google Slides text placement can differ from object coordinates.

## Core Narrative

1. Prediction markets reveal beliefs about future states through prices, but not the reasons behind belief changes.
2. Define explanation as a belief-update model: prior belief + selected evidence + update rule -> posterior belief.
3. Position the work relative to:
   - SWM / SWV-style market forecasting: uses evidence and market transitions, but does not make written explanation the object of study.
   - Tell Me Why: rationales reveal information sources and reduce double-counting, but are not the same as reusable belief-update rules.
   - Evidence Markets: rewards evidence provision; this project evaluates the mapping from evidence to posterior updates.
   - LLM hypothesis-generation work: LLMs can cheaply generate candidate rules, but the novelty here is market-based evaluation of update rules.
4. State the central question: which explanation classes predict market belief updates, which predict final outcomes, and can learning this distinction improve forecasting agents?
5. Show the empirical setup: market question, price history, candidate news, prior price, hidden next price, multiple LLM explanations, posterior scores, selector/agent.
6. Present preliminary Gemma pilot results as evidence of promise and remaining gaps.
7. End with the research plan and specific feedback asks.

## Result Numbers To Cite Carefully

- Freeform held-out pilot: 62 prompts.
- Oracle-best candidate beats persistence in 64.5% of prompts.
- Mean absolute market-price error: persistence 0.181, oracle-best candidate 0.140.
- Only 21.0% of oracle-best candidates are within 5 percentage points of the next price.
- Candidate pools often underreact; the target market price was not bracketed by generated candidate ranges in the held-out audit.
- Calibration-diverse stress test on overlapping rows: freeform had 13/14 helpful and 0/14 all-flat; named calibration profiles had 3/14 helpful and 10/14 all-flat.

## Guardrails

- Treat next market price as the market-update target, not ground-truth correctness.
- Distinguish market alignment from eventual outcome correctness whenever possible.
- Do not claim stable explanation classes yet; that is an empirical question.
- Do not claim the current selector is reliable. The current result mainly shows a generation-versus-selection gap.
- Do not overinterpret failures from irrelevant or sparse evidence packets; retrieval policy is part of the research design.
- Note when final resolution labels are not yet available for a benchmark subset.

## Current Feedback Deck

- Google Slides: https://docs.google.com/presentation/d/1e8qWeCNtWWxYjiH-e7tkuS9pWCH0b5-slVoEALCV_lQ/edit
- Title: Market for Explanations - Early Research Feedback
- Created from the reference deck style on 2026-06-29.
