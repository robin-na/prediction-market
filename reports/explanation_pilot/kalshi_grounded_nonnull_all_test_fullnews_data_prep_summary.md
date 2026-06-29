# Explanation Pilot Data Prep Summary

No LLM calls were used. This is the candidate dataset for later explanation generation or manual review.

## Counts

- Market filter: `grounded`
- Eligible input rows after filter: `236`
- Rows: `72`
- Candidate news records: `5619`
- Candidate config: `{'top_posterior_k': 100, 'top_prior_k': 100, 'hard_negative_k': 0, 'random_k': 100}`
- Row buckets: `{'posterior_attributed_move': 72}`
- Selection reasons: `{'posterior_top_k': 3143, 'prior_top_k': 3126, 'top_posterior': 72, 'top_prior': 70, 'random_candidate': 1045}`
- Top-prior candidates posterior-positive rate: `0.800`

## Full Raw Kalshi Test Context

- Input rows: `1120`
- Posterior-positive rows: `339` (`0.303`)
- Zero-posterior rows with abs(delta) >= 0.02: `180` (`0.230` of zero-posterior rows)
- Top-prior posterior-positive rate over all rows with prior scores: `0.193`
- Top-prior exact top-posterior match rate on posterior-positive rows: `0.166`

## Largest Posterior-Attributed Moves

- `kalshi_test_0354` up +0.711, Politics: Will Gary Peters vote for the next omnibus spending bill, minibus, or government-wide contin...
  - top posterior: US Senate to Vote on Bill to Reopen Gov’t with Crypto Bill in Limbo
  - top prior: US Senate to Vote on Bill to Reopen Gov’t with Crypto Bill in Limbo
- `kalshi_test_0503` up +0.597, Elections: Who will win the next Argentine presidential election?
  - top posterior: Argentina Looks to Ease Bank Reserve Rules to Boost Liquidity
  - top prior: Argentina Central Bank Eases Reserve Rules to Boost Liquidity
- `kalshi_test_1104` up +0.539, Politics: Will Steve Scalise vote for releasing the Epstein files?
  - top posterior: Trump feuds with MAGA ally ahead of vote to release Epstein files
  - top prior: Trump finally breaks with MAGA stalwart Marjorie Taylor Greene after flood of vicious criticism, labeling her 'w...
- `kalshi_test_0002` up +0.410, Politics: Who will be elected President of Honduras in 2025?
  - top posterior: Greensboro candidates say how they would handle policing
  - top prior: Democrats test progressive vs centrist candidates ahead of elections
- `kalshi_test_1108` up +0.390, Politics: Will Mike Johnson vote for releasing the Epstein files?
  - top posterior: Trump feuds with MAGA ally ahead of vote to release Epstein files
  - top prior: Donald Trump Ends Support for Marjorie Taylor Greene, Calls Her ‘Wacky’
- `kalshi_test_0873` up +0.371, Politics: Will the EU sanction Israel before Jan 1, 2026?
  - top posterior: Amnesty International: Israel’s ongoing GENOCIDE in Gaza persists despite ceasefire
  - top prior: Shari Redstone's new media venture matches her passion for telling authentic stories about Israel
- `kalshi_test_1016` up +0.331, Companies: What will FedEx Corporation say during their next earnings call?
  - top posterior: FedEx Delivers Q2 Earnings Beat, Shares Move Higher After Hours
  - top prior: Here are the major earnings after the close Thursday
- `kalshi_test_0305` up +0.323, Companies: What will Walmart Inc. say during their next earnings call?
  - top posterior: Holiday Retail Sales to Hit $1 Trillion: Which Giant Will Win Black Friday 2025?
  - top prior: Holiday Retail Sales to Hit $1 Trillion: Which Giant Will Win Black Friday 2025?
- `kalshi_test_0013` up +0.312, Politics: Will anyone in Congress change parties?
  - top posterior: Toxic environment in Congress prompts lawmakers to resign
  - top prior: Tracking the retirement announcements of members of Congress
- `kalshi_test_0014` up +0.309, Politics: Will anyone in Congress change parties?
  - top posterior: Rep Marc Veasey announces he will run for Tarrant County Judge
  - top prior: Supreme Court questions limits on political party spending in federal elections, hearing GOP appeal

## Largest Unattributed Moves


## Examples Where Top Prior And Top Posterior Differ

- `kalshi_test_0503` up +0.597, Elections: Who will win the next Argentine presidential election?
  - top posterior: Argentina Looks to Ease Bank Reserve Rules to Boost Liquidity
  - top prior: Argentina Central Bank Eases Reserve Rules to Boost Liquidity
- `kalshi_test_1104` up +0.539, Politics: Will Steve Scalise vote for releasing the Epstein files?
  - top posterior: Trump feuds with MAGA ally ahead of vote to release Epstein files
  - top prior: Trump finally breaks with MAGA stalwart Marjorie Taylor Greene after flood of vicious criticism, labeling her 'w...
- `kalshi_test_0002` up +0.410, Politics: Who will be elected President of Honduras in 2025?
  - top posterior: Greensboro candidates say how they would handle policing
  - top prior: Democrats test progressive vs centrist candidates ahead of elections
- `kalshi_test_1108` up +0.390, Politics: Will Mike Johnson vote for releasing the Epstein files?
  - top posterior: Trump feuds with MAGA ally ahead of vote to release Epstein files
  - top prior: Donald Trump Ends Support for Marjorie Taylor Greene, Calls Her ‘Wacky’
- `kalshi_test_0873` up +0.371, Politics: Will the EU sanction Israel before Jan 1, 2026?
  - top posterior: Amnesty International: Israel’s ongoing GENOCIDE in Gaza persists despite ceasefire
  - top prior: Shari Redstone's new media venture matches her passion for telling authentic stories about Israel
- `kalshi_test_1016` up +0.331, Companies: What will FedEx Corporation say during their next earnings call?
  - top posterior: FedEx Delivers Q2 Earnings Beat, Shares Move Higher After Hours
  - top prior: Here are the major earnings after the close Thursday
- `kalshi_test_0013` up +0.312, Politics: Will anyone in Congress change parties?
  - top posterior: Toxic environment in Congress prompts lawmakers to resign
  - top prior: Tracking the retirement announcements of members of Congress
- `kalshi_test_0014` up +0.309, Politics: Will anyone in Congress change parties?
  - top posterior: Rep Marc Veasey announces he will run for Tarrant County Judge
  - top prior: Supreme Court questions limits on political party spending in federal elections, hearing GOP appeal
- `kalshi_test_1012` up +0.308, Companies: What will FedEx Corporation say during their next earnings call?
  - top posterior: FedEx Delivers Q2 Earnings Beat, Shares Move Higher After Hours
  - top prior: Here are the major earnings after the close Thursday
- `kalshi_test_1109` up +0.301, Politics: Will Mike Johnson vote for releasing the Epstein files?
  - top posterior: Co-sponsors of petition to release Epstein files foresee growing GOP support for upcoming vote
  - top prior: Epstein Files Bill Poised to Win Dozens of GOP Votes-Co-Sponsors

## Output Files

- `data/derived/explanation_pilot/kalshi_grounded_nonnull_all_test_fullnews_rows.jsonl`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_all_test_fullnews_candidates.jsonl`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_all_test_fullnews_summary.json`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_all_test_fullnews_candidate_selection_summary.csv`
