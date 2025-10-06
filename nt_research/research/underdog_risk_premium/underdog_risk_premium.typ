#import "@preview/charged-ieee:0.1.4": ieee
#set document(title: "Underdog Risk Premium")
#set page(margin: 1in, columns: 2)
#set par(justify: true)
#set text(size: 11pt)

#show: ieee.with(
  title: [Underdog Risk Premium],
  abstract: [
    We document systematic mispricing in Kalshi's college football prediction markets during the 2025 season. High-probability contracts (90-99 cents) are consistently underpriced by approximately 2.29 percentage points in the hours preceding kickoff. We attribute this inefficiency to retail traders' preference for lottery-like payoffs on longshot bets. A trading strategy exploiting this pattern achieves a 98.67% win rate (148, 150 trades), though concentration risk from expensive contracts limits risk-adjusted returns to a Sharpe ratio of 0.20 (unannualized). Our findings suggest that while market inefficiencies exist and are statistically significant, their exploitation requires careful risk management due to severe tail risk exposure.
  ],
  authors: (
    (
      name: "Andrew Hall",
      department: [Quantitative Researcher],
      organization: [Silver Fund],
      location: [Provo, Utah],
      email: "andrewmartinhall2@gmail.com"
    ),
    (
      name: "Brandon Waits",
      department: [Quantitative Researcher],
      organization: [Silver Fund],
      location: [Provo, Utah],
      email: "brandonwaits12@gmail.com"
    ),
    // (
    //   name: "Justin Hill",
    //   department: [Co-Founder],
    //   organization: [Nameless Trading],
    //   location: [Newport Beach, California],
    //   email: "jrhill426@gmail.com"
    // ),
  ),
  index-terms: ("Prediction markets", "Market efficiency", "Behavioral finance", "Trading strategies"),
)

= Background

Prediction markets have experienced rapid growth following recent regulatory changes with platforms like Kalshi emerging as key venues for betting on real-world events. This report examines the college football prediction market for the 2025 season to identify pricing inefficiencies. Our analysis reveals systematic mispricing in the final hours before kickoff, specifically for contracts trading in the 90-99 probability range, suggesting exploitable market inefficiencies during this critical pre-game window.

= Market Calibration

To test market efficiency, we analyze the calibration of prediction market contracts at a standardized time point $t$. Our dataset comprises minute-level tick data for 830 contracts from the first six weeks of the 2025 college football season. We normalize timestamps across all contracts using "elapsed time," defined as minutes relative to kickoff (negative values indicate pre-game).

For this analysis, we filter to contracts with $t = -60$ (60 minutes before kickoff) and extract each contract's first closing ask price after this threshold. We then group contracts into 10 cent price bins and calculate the realized win rate within each bin. This approach allows us to assess whether market prices accurately reflect true outcome probabilities.

Our calibration analysis reveals significant mispricing in the extreme price bins. Contracts in the $(0, 10]$ bin show a delta of $-3.48$ percentage points, while those in the $(90, 99]$ bin exhibit a delta of $+2.29$ percentage points, both statistically significant. This indicates that low-probability contracts are systematically overpriced, while high-probability contracts are underpriced relative to their true win rates.

#figure(
  image("results/experiment_1/calibration_chart_t=-60.png"),
  caption: [Market calibration at t=-60 minutes]
)

#figure(
  image("results/experiment_1/calibration_table_t=-60.png"),
  caption: [Calibration statistics at t=-60 minutes]
)

We attribute this pattern to behavioral biases among retail traders who constitute a substantial portion of prediction market participants. Existing research shows that recreational bettors exhibit a preference for lottery-like payoffs with asymmetric returns, leading them to overvalue underdogs and undervalue favorites. This behavior creates the observed pricing distortion, with demand concentrated in low-probability contracts despite their negative expected value.

= Optimal Timing

Now that we have established the existence of mispricing in extreme price bins, we explore the optimal time to take advantage of these mispricings. We do this by taking our tick data and discretizing it into 60 minute interval time bins and 10 cent increment price bins. For every combination of bins we compute the calibration of the bin. We report the results of the $(90, 99]$ bin.

Our temporal analysis reveals that mispricing in the $(90, 99]$ bin varies systematically with proximity to kickoff. Up to 3 hours preceding game start, high-probability contracts are underpriced by approximately 3 percentage points, meaning a contract priced at 90 cents has a realized win rate of 93\%. This effect reverses after kickoff with the same price bin becoming overpriced by up to 3 percentage points. Importantly every time bin preceding kickoff has a statistically significant test statistic.

#figure(
  image("results/experiment_2/calibration-over-time-top-bin.png"),
  caption: [Calibration over time for (90, 99\] price bin]
)

= Strategy Performance

Now that we have established the systematic mispricing of extreme bins and the strength of the effect over time, we explore the profitability of a trading strategy where we buy 90 to 99 cent contracts 60 minutes prior to kickoff. We do this by filtering our tick data to the 60 minute window prior to kickoff and taking the first closing ask price for each security. We then compute the profits as $1 - "ask_price"$ for winning contracts and $-"ask_price"$ for losing contracts. Here we report the results of this strategy:

Implementing this strategy generates 150 trades over our sample period, with 148 winners and only 2 loss. However, the concentration in high-probability contracts creates asymmetric risk exposure. While individual gains are modest, potential losses on any single trade are substantial. The winning trades alone achieve a Sharpe ratio of 1.33 (unannualized), but incorporating the two losing trades reduces the overall strategy Sharpe ratio to 0.20 (unannualized).

#figure(
  image("results/experiment_3/performance_table_t=-60.png"),
  caption: [Strategy performance metrics at t=-60 minutes]
)

This performance degradation highlights the strategy's vulnerability to tail risk. We propose that disciplined risk management through stop-loss orders could meaningfully improve risk-adjusted returns by capping downside exposure on losing positions while preserving the high win rate that drives profitability.

= Conclusion

This analysis demonstrates systematic and exploitable mispricing in college football prediction markets on Kalshi during the 2025 season. We document that high-probability contracts trading in the 90-99 cent range are consistently underpriced by approximately 3 percentage points in the hours leading up to kickoff, a pattern we attribute to retail traders' well-documented preference for lottery-like payoffs on longshot bets.

A simple trading strategy that exploits this inefficiency—buying high-probability contracts 60 minutes before kickoff—achieves a 98.67% win rate over 150 trades. However, the strategy's Sharpe ratio of 0.20 reveals its Achilles' heel: concentration in expensive contracts creates severe tail risk, where a single loss can erase the gains from numerous winners. This risk-return profile suggests the market inefficiency, while real, may be challenging to exploit at scale without sophisticated risk management.