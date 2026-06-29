# Explanation Pilot Data Prep Summary

No LLM calls were used. This is the candidate dataset for later explanation generation or manual review.

## Counts

- Market filter: `grounded`
- Eligible input rows after filter: `836`
- Rows: `340`
- Candidate news records: `22571`
- Candidate config: `{'top_posterior_k': 100, 'top_prior_k': 100, 'hard_negative_k': 0, 'random_k': 100}`
- Row buckets: `{'posterior_attributed_move': 340}`
- Selection reasons: `{'posterior_top_k': 13725, 'prior_top_k': 13137, 'top_posterior': 340, 'top_prior': 334, 'random_candidate': 3774}`
- Top-prior candidates posterior-positive rate: `0.760`

## Full Raw Kalshi Test Context

- Input rows: `2779`
- Posterior-positive rows: `1174` (`0.422`)
- Zero-posterior rows with abs(delta) >= 0.02: `397` (`0.247` of zero-posterior rows)
- Top-prior posterior-positive rate over all rows with prior scores: `0.318`
- Top-prior exact top-posterior match rate on posterior-positive rows: `0.225`

## Largest Posterior-Attributed Moves

- `kalshi_train_0165` up +0.737, Politics: How many Senators vote to confirm as Secretary of State?
  - top posterior: Trump meets with GOP senators as supporters cheer his return on eve of inauguration
  - top prior: "Bobby’s f**king smart, dude": Anti-vax QB Rodgers gives glowing endorsement of RFK Jr.
- `kalshi_train_0809` up +0.601, Companies: What will Starbucks Corporation say during their next earnings call?
  - top posterior: S&P 500 Rises as Traders Await Earnings Show
  - top prior: Artea Bank Invitation to Q3 2025 Financial Results webinar
- `kalshi_train_2712` up +0.591, Politics: Will the popular vote margin of victory for Donald Trump in Georgia be 2.00-2.99%?
  - top posterior: Trump wins key battleground states and claims victory in historic campaign
  - top prior: Election 2024 live updates: Trump wins Georgia, Harris’ chances fade
- `kalshi_train_2403` up +0.572, Companies: What will Tesla, Inc. say during their next earnings call?
  - top posterior: GM to end production of its Chevy Brightdrop electric vans
  - top prior: RTX Q3 FY2025 Earnings Call Transcript
- `kalshi_train_0342` up +0.571, Companies: What will Coinbase Global, Inc. say during their next earnings call?
  - top posterior: Coinbase Q3 Preview: Product Diversification, Acquisitions Create 'A Compelling Opportunity'
  - top prior: Coinbase Q3 Preview: Product Diversification, Acquisitions Create 'A Compelling Opportunity'
- `kalshi_train_1568` up +0.531, Politics: Will the electoral college margin of victory be between -65 and -104 for Republican?
  - top posterior: 2024 presidential election results and live Electoral College map
  - top prior: The Home Depot Co-Founder Bernard Marcus Dead at 95
- `kalshi_train_1939` up +0.528, Politics: Will Dana White visit the White House before Apr 1, 2025?
  - top posterior: Trump White House plans to shake up briefing room seating, flexing power over press corps
  - top prior: Mike Waltz's Venmo account showed his contacts - even after bombshell report on secret Signal chat
- `kalshi_train_1180` up +0.518, Elections: Who will win the next Argentine presidential election?
  - top posterior: Argentina elections: Javier Milei’s party wins midterm vote seen as test for his libertarian mandate and US support
  - top prior: Argentina's midterm election hands decisive win to Milei's libertarian overhaul
- `kalshi_train_1095` up +0.503, Politics: Will Kamala Harris run for California Governor?
  - top posterior: Donald Trump Calls for Beyoncé to Be Prosecuted for Baseless Claim
  - top prior: Donald Trump Calls for Beyoncé to Be Prosecuted for Baseless Claim
- `kalshi_train_2320` up +0.457, Politics: Will Republicans win the Senate race in Wisconsin?
  - top posterior: Kamala Harris congratulates Donald Trump
  - top prior: Donald Trump wins 2024 presidential election, defying the odds again

## Largest Unattributed Moves


## Examples Where Top Prior And Top Posterior Differ

- `kalshi_train_0165` up +0.737, Politics: How many Senators vote to confirm as Secretary of State?
  - top posterior: Trump meets with GOP senators as supporters cheer his return on eve of inauguration
  - top prior: "Bobby’s f**king smart, dude": Anti-vax QB Rodgers gives glowing endorsement of RFK Jr.
- `kalshi_train_0809` up +0.601, Companies: What will Starbucks Corporation say during their next earnings call?
  - top posterior: S&P 500 Rises as Traders Await Earnings Show
  - top prior: Artea Bank Invitation to Q3 2025 Financial Results webinar
- `kalshi_train_2712` up +0.591, Politics: Will the popular vote margin of victory for Donald Trump in Georgia be 2.00-2.99%?
  - top posterior: Trump wins key battleground states and claims victory in historic campaign
  - top prior: Election 2024 live updates: Trump wins Georgia, Harris’ chances fade
- `kalshi_train_2403` up +0.572, Companies: What will Tesla, Inc. say during their next earnings call?
  - top posterior: GM to end production of its Chevy Brightdrop electric vans
  - top prior: RTX Q3 FY2025 Earnings Call Transcript
- `kalshi_train_1568` up +0.531, Politics: Will the electoral college margin of victory be between -65 and -104 for Republican?
  - top posterior: 2024 presidential election results and live Electoral College map
  - top prior: The Home Depot Co-Founder Bernard Marcus Dead at 95
- `kalshi_train_1939` up +0.528, Politics: Will Dana White visit the White House before Apr 1, 2025?
  - top posterior: Trump White House plans to shake up briefing room seating, flexing power over press corps
  - top prior: Mike Waltz's Venmo account showed his contacts - even after bombshell report on secret Signal chat
- `kalshi_train_1180` up +0.518, Elections: Who will win the next Argentine presidential election?
  - top posterior: Argentina elections: Javier Milei’s party wins midterm vote seen as test for his libertarian mandate and US support
  - top prior: Argentina's midterm election hands decisive win to Milei's libertarian overhaul
- `kalshi_train_2320` up +0.457, Politics: Will Republicans win the Senate race in Wisconsin?
  - top posterior: Kamala Harris congratulates Donald Trump
  - top prior: Donald Trump wins 2024 presidential election, defying the odds again
- `kalshi_train_0820` up +0.448, Politics: Will Democratics win the Senate race in Pennsylvania?
  - top posterior: Stock futures, bitcoin and dollar rise as Trump poised to win
  - top prior: Donald Trump to Win Pennsylvania, Fox News Projects
- `kalshi_train_2406` up +0.439, Companies: What will Tesla, Inc. say during their next earnings call?
  - top posterior: GM to end production of its Chevy Brightdrop electric vans
  - top prior: RTX Q3 FY2025 Earnings Call Transcript

## Output Files

- `data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_rows.jsonl`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_candidates.jsonl`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_summary.json`
- `data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_candidate_selection_summary.csv`
