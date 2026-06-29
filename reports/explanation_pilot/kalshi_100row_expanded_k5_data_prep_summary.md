# Explanation Pilot Data Prep Summary

No LLM calls were used. This is the candidate dataset for later explanation generation or manual review.

## Counts

- Rows: `100`
- Candidate news records: `1100`
- Candidate config: `{'top_posterior_k': 5, 'top_prior_k': 5, 'hard_negative_k': 3, 'random_k': 2}`
- Row buckets: `{'posterior_attributed_move': 50, 'unattributed_moved': 25, 'stable_no_attribution': 25}`
- Selection reasons: `{'lexical_hard_negative_k': 269, 'lexical_hard_negative': 92, 'prior_top_k': 477, 'random_candidate': 178, 'posterior_top_k': 220, 'top_posterior': 50, 'top_prior': 98}`
- Top-prior candidates posterior-positive rate: `0.265`

## Full Raw Kalshi Test Context

- Input rows: `1120`
- Posterior-positive rows: `339` (`0.303`)
- Zero-posterior rows with abs(delta) >= 0.02: `180` (`0.230` of zero-posterior rows)
- Top-prior posterior-positive rate over all rows with prior scores: `0.193`
- Top-prior exact top-posterior match rate on posterior-positive rows: `0.166`

## Largest Posterior-Attributed Moves

- `kalshi_test_0800` up +0.860, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Leaders arrive for historic G20 summit overshadowed by rift between South Africa and U.S.
  - top prior: What are the issues of contention in the US peace plan for ending the war in Ukraine?
- `kalshi_test_0801` up +0.828, Crypto: How many countries will create crypto reserves this year?
  - top posterior: UN climate talks end with deal for more money to countries hit by climate change
  - top prior: Space Race With China Drives Antenna-Building Boom in Arctic
- `kalshi_test_0575` up +0.821, Entertainment: Will Death by Lightning be on the list of nominees for Best Television Series - Limited Seri...
  - top posterior: 12 TV Shows Like Netflix's Death By Lightning
  - top prior: Nick Offerman joins Geoff Bennett for our ‘Settle In’ podcast
- `kalshi_test_1003` up +0.779, Entertainment: TIME's Person of the Year for 2025 be a woman?
  - top posterior: One Of 2025's Best Films Gets Some Renewed Oscars Hope Thanks To The Golden Globes
  - top prior: Video shows train smashing into SUV, driver suffers minor injuries
- `kalshi_test_0444` up +0.777, Mentions: Will Trump say "Crooked Hillary" before Jan 1, 2026?
  - top posterior: US Rare Earth Firms Still See China Curbs Despite Trump Deal (1)
  - top prior: What's open on the day after Christmas? Here's what's open, from the stock market to stores.
- `kalshi_test_0327` up +0.718, Entertainment: Will Sam Altman be Time Person of the Year in 2025?
  - top posterior: Top Startup and Tech Funding News - December 9, 2025
  - top prior: Knicks vs. Raptors prediction, odds, spread: 2025 NBA Cup picks from proven model
- `kalshi_test_0354` up +0.711, Politics: Will Gary Peters vote for the next omnibus spending bill, minibus, or government-wide contin...
  - top posterior: US Senate to Vote on Bill to Reopen Gov’t with Crypto Bill in Limbo
  - top prior: US Senate to Vote on Bill to Reopen Gov’t with Crypto Bill in Limbo
- `kalshi_test_0804` up +0.702, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Regime change is back. MAGA is getting comfortable with it.
  - top prior: Kristi Noem calls for 'full travel ban' after National Guard shooting
- `kalshi_test_0805` up +0.642, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Former Signature Bank executives launch N3XT, a blockchain bank built for 24/7 real
  - top prior: How Donald Trump’s immigration message is colliding with his welcome to World Cup fans
- `kalshi_test_0468` up +0.612, Social: Will Deaths in 2025 be the most popular Wikipedia article in 2025?
  - top posterior: Moderna stock falls after FDA promises new vaccine requirements
  - top prior: Congo declares its latest Ebola outbreak over

## Largest Unattributed Moves

- `kalshi_test_0271` up +0.453, Politics: Who will win the Bucharest mayoral election?
  - top posterior: none
  - top prior: Late heartbreak for Arsenal at Villa Park
- `kalshi_test_0150` up +0.450, Entertainment: 2026 Best Director Oscar nominations?
  - top posterior: none
  - top prior: 10 Major Laws Taking Effect In California In 2026
- `kalshi_test_0003` up +0.330, Politics: Who will be elected President of Honduras in 2025?
  - top posterior: none
  - top prior: Toms River Mayor Daniel Rodrick could lose control in 2025 election
- `kalshi_test_0921` up +0.267, Science and Technology: Which nuclear power companies will achieve criticality before Aug 2026?
  - top posterior: none
  - top prior: Ilia Topuria opens up on UFC 324 interim clash and sends clear signal to Paddy Pimblett
- `kalshi_test_1011` up +0.235, Companies: What will FedEx Corporation say during their next earnings call?
  - top posterior: none
  - top prior: What's Going On With Navan Stock Tuesday?
- `kalshi_test_0237` up +0.180, Entertainment: Who will perform at the 68th Grammy Awards?
  - top posterior: none
  - top prior: Canucks To Activate Elias Pettersson Off Injured Reserve
- `kalshi_test_1015` up +0.173, Companies: What will FedEx Corporation say during their next earnings call?
  - top posterior: none
  - top prior: What's Going On With Navan Stock Tuesday?
- `kalshi_test_0376` up +0.145, Entertainment: WIll GTA6 be released by May 26, 2026?
  - top posterior: none
  - top prior: Gayle King Clarifies Whether She's Leaving 'CBS Mornings' amid Conflicting Reports
- `kalshi_test_1081` up +0.141, Elections: Will Virginia Attorney General election have the smallest margin of victory in 2025 U.S. Ele...
  - top posterior: none
  - top prior: none
- `kalshi_test_1082` up +0.134, Elections: Will Virginia Attorney General election have the smallest margin of victory in 2025 U.S. Ele...
  - top posterior: none
  - top prior: none

## Examples Where Top Prior And Top Posterior Differ

- `kalshi_test_0800` up +0.860, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Leaders arrive for historic G20 summit overshadowed by rift between South Africa and U.S.
  - top prior: What are the issues of contention in the US peace plan for ending the war in Ukraine?
- `kalshi_test_0801` up +0.828, Crypto: How many countries will create crypto reserves this year?
  - top posterior: UN climate talks end with deal for more money to countries hit by climate change
  - top prior: Space Race With China Drives Antenna-Building Boom in Arctic
- `kalshi_test_0575` up +0.821, Entertainment: Will Death by Lightning be on the list of nominees for Best Television Series - Limited Seri...
  - top posterior: 12 TV Shows Like Netflix's Death By Lightning
  - top prior: Nick Offerman joins Geoff Bennett for our ‘Settle In’ podcast
- `kalshi_test_1003` up +0.779, Entertainment: TIME's Person of the Year for 2025 be a woman?
  - top posterior: One Of 2025's Best Films Gets Some Renewed Oscars Hope Thanks To The Golden Globes
  - top prior: Video shows train smashing into SUV, driver suffers minor injuries
- `kalshi_test_0444` up +0.777, Mentions: Will Trump say "Crooked Hillary" before Jan 1, 2026?
  - top posterior: US Rare Earth Firms Still See China Curbs Despite Trump Deal (1)
  - top prior: What's open on the day after Christmas? Here's what's open, from the stock market to stores.
- `kalshi_test_0327` up +0.718, Entertainment: Will Sam Altman be Time Person of the Year in 2025?
  - top posterior: Top Startup and Tech Funding News - December 9, 2025
  - top prior: Knicks vs. Raptors prediction, odds, spread: 2025 NBA Cup picks from proven model
- `kalshi_test_0804` up +0.702, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Regime change is back. MAGA is getting comfortable with it.
  - top prior: Kristi Noem calls for 'full travel ban' after National Guard shooting
- `kalshi_test_0805` up +0.642, Crypto: How many countries will create crypto reserves this year?
  - top posterior: Former Signature Bank executives launch N3XT, a blockchain bank built for 24/7 real
  - top prior: How Donald Trump’s immigration message is colliding with his welcome to World Cup fans
- `kalshi_test_0468` up +0.612, Social: Will Deaths in 2025 be the most popular Wikipedia article in 2025?
  - top posterior: Moderna stock falls after FDA promises new vaccine requirements
  - top prior: Congo declares its latest Ebola outbreak over
- `kalshi_test_0503` up +0.597, Elections: Who will win the next Argentine presidential election?
  - top posterior: Argentina Looks to Ease Bank Reserve Rules to Boost Liquidity
  - top prior: Argentina Central Bank Eases Reserve Rules to Boost Liquidity

## Output Files

- `data/derived/explanation_pilot/kalshi_100row_expanded_k5_rows.jsonl`
- `data/derived/explanation_pilot/kalshi_100row_expanded_k5_candidates.jsonl`
- `data/derived/explanation_pilot/kalshi_100row_expanded_k5_summary.json`
- `data/derived/explanation_pilot/kalshi_100row_expanded_k5_candidate_selection_summary.csv`
