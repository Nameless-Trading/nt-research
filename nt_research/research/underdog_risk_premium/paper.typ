#set document(title: "Underdog Risk Premium")
#set page(margin: 1in)
#set par(justify: true)
#set text(size: 11pt)

#align(center)[
  #text(size: 17pt, weight: "bold")[Underdog Risk Premium]
]

= Background

Prediction markets have experienced rapid growth following recent regulatory changes, with platforms like Kalshi emerging as key venues for betting on real-world events. This report examines the college football prediction market for the 2025 season to identify pricing inefficiencies and potential arbitrage opportunities. Our analysis reveals systematic mispricing in the final 30 minutes before kickoff, specifically for contracts trading in the 90-100 probability range, suggesting exploitable market inefficiencies during this critical pre-game window.

= Market Calibration

To test market efficiency, we analyze the calibration of prediction market contracts at a standardized time point $t$. Our dataset comprises minute-level tick data for 728 contracts from the first five weeks of the 2025 college football season. We normalize timestamps across all contracts using "elapsed time," defined as minutes relative to kickoff (negative values indicate pre-game).

For this analysis, we filter to contracts with $t = -30$ (30 minutes before kickoff) and extract each contract's first closing ask price after this threshold. We then group contracts into 10 cent price bins and calculate the realized win rate within each bin. This approach allows us to assess whether market prices accurately reflect true outcome probabilities.

Our calibration analysis reveals significant mispricing in the extreme price bins. Contracts in the $(0, 10]$ bin show a delta of $-3.82$ percentage points, while those in the $(90, 100]$ bin exhibit a delta of $+2.32$ percentage points, both statistically significant. This indicates that low-probability contracts are systematically overpriced, while high-probability contracts are underpriced relative to their true win rates.

#figure(
  image("results/experiment_1/calibration_chart_t=-30.png"),
  caption: [Market calibration at t=-30 minutes]
)

#figure(
  image("results/experiment_1/calibration_table_t=-30.png"),
  caption: [Calibration statistics at t=-30 minutes]
)

We attribute this pattern to behavioral biases among retail traders who constitute a substantial portion of prediction market participants. Existing research shows that recreational bettors exhibit a preference for lottery-like payoffs with asymmetric returns, leading them to overvalue underdogs and undervalue favorites. This behavior creates the observed pricing distortion, with demand concentrated in low-probability contracts despite their negative expected value.

= Optimal Timing

Now that we have established the existence of mispricing in extreme price bins, we explore the optimal time to take advantage of these mispricings. We do this by taking our tick data and discretizing it into 60 minute interval time bins and 10 cent increment price bins. For every combination of bins we compute the calibration of the bin. We report the results of the $(90, 100]$ bin.

Our temporal analysis reveals that mispricing in the $(90, 100]$ bin varies systematically with proximity to kickoff. Up to 3 hours preceding game start, high-probability contracts are underpriced by approximately 4 percentage points, meaning a contract priced at 90 cents has a realized win rate of 94\%. This inefficiency diminishes rapidly after kickoff and reverses within 2 hours of game start, with the same price bin becoming overpriced by up to 2 percentage points. Importantly every time bin has a statistically significant test statistic.

#figure(
  image("results/experiment_2/calibration-over-time-top-bin.png"),
  caption: [Calibration over time for (90, 100\] price bin]
)

= Strategy Performance

Now that we have established the systematic mispricing of extreme bins and the strength of the effect over time, we explore the profitability of a trading strategy where we buy 90 to 99 cent contracts 30 minutes prior to kickoff. We do this by filtering our tick data to the 30 minute window prior to kickoff and taking the first closing mid (mean of bid and ask) price for each security. We then compute the profits as $1 - "mid_price"$ for winning contracts and $-"mid_price"$ for losing contracts. Here we report the results of this strategy:

Implementing this strategy generates 154 trades over our sample period, with 153 winners and only one loss. However, the concentration in high-probability contracts creates asymmetric risk exposure. While individual gains are modest, potential losses on any single trade are substantial. The winning trades alone achieve a Sharpe ratio of 1.40 (unannualized), but incorporating the single losing trade reduces the overall strategy Sharpe ratio to 0.36 (unannualized).

#figure(
  image("results/experiment_3/performance_table_t=-30.png"),
  caption: [Strategy performance metrics at t=-30 minutes]
)

This performance degradation highlights the strategy's vulnerability to tail risk. We propose that disciplined risk management through stop-loss orders could meaningfully improve risk-adjusted returns by capping downside exposure on losing positions while preserving the high win rate that drives profitability.

= Conclusion

This analysis demonstrates systematic and exploitable mispricing in college football prediction markets on Kalshi during the 2025 season. We document that high-probability contracts trading in the 90-100 cent range are consistently underpriced by approximately 4 percentage points in the hours leading up to kickoff, a pattern we attribute to retail traders' well-documented preference for lottery-like payoffs on longshot bets.

A simple trading strategy that exploits this inefficiency—buying high-probability contracts 30 minutes before kickoff—achieves a 99.4% win rate over 154 trades. However, the strategy's Sharpe ratio of 0.36 reveals its Achilles' heel: concentration in expensive contracts creates severe tail risk, where a single loss can erase the gains from numerous winners. This risk-return profile suggests the market inefficiency, while real, may be challenging to exploit at scale without sophisticated risk management.