Inputs/outputs

3.1 qualitative analysis
INPUTS
    #3 Event specific details
    #4 Matchups
OUTPUT
    Team/Player Intelligence Report
---------------------------------------------------
3.2 quantitative analysis
INPUTS
    attach: Main Market Lines
    attach: Team/Player Intelligence Report
    #3-3 markets to create prices for
OUTPUT
    True Prices Report
---------------------------------------------------
3.3 portfolio allocation
3.3a) Team Context & Intelligence Ingestion
INPUTS
    attach: Team/Player Intelligence Report
    attach: True Prices Report
3.3b) Quantitative Edge Calculation
INPUTS
    attach: Sportsbook Odds
3.3c) Final Decision-Making & Bankroll Allocation
INPUTS
    Optional: change bankroll amount
3.3d) Final Report Formatting
INPUTS
    none/contextual
OUTPUT
    Final report
