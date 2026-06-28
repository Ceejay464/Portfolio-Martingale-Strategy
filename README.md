# Portfolio Martingale Strategy

## Overview

This strategy implements a **diversified Martingale approach** across a broad portfolio of ETFs. Rather than applying Martingale to a single asset (which carries significant tail risk), the strategy allocates capital equally across 100+ ETFs and runs independent Martingale strategies on each. A **tiered profit-taking mechanism** locks in gains while allowing winners to run.

The backtest is conducted using the **`PortfolioStrategy`** module of **vn.py**.

---

## Strategy Logic

### 1. Core Concept

Traditional Martingale doubles down on losing positions, which can lead to catastrophic drawdowns during prolonged adverse trends. This strategy mitigates that risk through:

- **Deep diversification**: Capital spread across 100+ ETFs spanning multiple asset classes
- **Independent position management**: Each ETF runs its own Martingale logic
- **Capital allocation**: Total capital divided equally among all assets in the pool

---

### 2. Asset Pool

The strategy trades **100+ ETFs** across diverse asset classes, including but not limited to:

| Asset Class | Examples |
|-------------|----------|
| **Domestic Equity** | CSI 300 ETF, CSI 500 ETF, ChiNext ETF, STAR 50 ETF |
| **Sector ETFs** | Technology, Financials, Healthcare, Consumer, Energy |
| **Bonds** | Treasury ETFs, Corporate Bond ETFs |
| **Commodities** | Gold ETF, Silver ETF, Agricultural ETFs, Industrial Metal ETFs |
| **Global Exposure** | NASDAQ ETF, S&P 500 ETF, Hang Seng ETF, Japan ETF, Europe ETF |
| **REITs** | Real Estate Investment Trust ETFs |
| **Factor ETFs** | Low Volatility, Dividend, Value, Growth, Quality |
| **Thematic ETFs** | New Energy, AI, Semiconductor, Biotech, ESG |

> *Full asset list available in `config.yaml`*

---

### 3. Position Management

#### Initial Setup

Each ETF receives an equal capital allocation. Each position operates independently with its own:

- Entry price
- Grid levels
- Position sizing
- Take-profit targets

#### Martingale Grid Logic

For each ETF, the strategy establishes a price grid:

| Grid Level | Action |
|------------|--------|
| Level 0 (Initial) | Buy base position at current price |
| Level -1 | Buy additional position if price drops X% |
| Level -2 | Buy additional position if price drops 2X% |
| Level -3 | Buy additional position if price drops 3X% |

Each grid level increases position size to reduce average entry cost.

---

### 4. Exit Logic: Tiered Profit-Taking

Rather than a single take-profit target, the strategy employs **graduated profit targets** to lock in gains while allowing further upside:

| Tier | Profit Level | Action |
|------|--------------|--------|
| Tier 1 | +5% | Close 20% of position |
| Tier 2 | +10% | Close 20% of position |
| Tier 3 | +15% | Close 20% of position |
| Tier 4 | +20% | Close 20% of position |
| Tier 5 | +25%+ | Close remaining 20% |

This approach ensures profits are realized incrementally while maintaining exposure to continued upward moves.

---

### 5. Risk Controls

| Control | Description |
|---------|-------------|
| **Max Grid Levels** | Maximum 5 grid levels per asset (prevents unlimited doubling) |
| **Per-Asset Stop-Loss** | Absolute -30% stop-loss per position |
| **Portfolio Stop-Loss** | -15% total portfolio drawdown triggers partial de-risking |
| **Position Sizing Cap** | Maximum position size per asset limited to 2× initial allocation |

---

## Backtest Results

**Period:** 2015-2026

| Year | Annualized Return | Total Return | Max Drawdown | Sharpe Ratio |
|------|-------------------|--------------|--------------|--------------|
| 2015 | 7.99% | 7.40% | -3.76% | 1.23 |
| 2016 | 8.72% | 8.43% | -7.39% | 1.51 |
| 2017 | -3.73% | -3.61% | -8.15% | -0.49 |
| 2018 | 12.79% | 12.31% | -9.34% | 0.89 |
| 2019 | 35.46% | 34.16% | -4.15% | 3.14 |
| 2020 | 16.57% | 15.93% | -6.88% | 1.53 |
| 2021 | 12.55% | 12.07% | -4.33% | 1.45 |
| 2022 | 10.92% | 10.46% | -7.81% | 0.75 |
| 2023 | 19.84% | 18.99% | -2.74% | 2.41 |
| 2024 | 17.80% | 17.04% | -3.02% | 2.81 |
| 2025 | 8.37% | 8.06% | -3.85% | 1.49 |
| 2026* | 20.09% | 7.15% | -2.99% | 2.28 |

> *2026 data partial year (as of backtest end date)*

---

## Performance Summary

| Metric | Value |
|--------|-------|
| **Total Period Return** | ~180%+ |
| **Average Annual Return** | ~14.5% |
| **Worst Year (2017)** | -3.73% |
| **Best Year (2019)** | +35.46% |
| **Maximum Drawdown** | -9.34% (2018) |
| **Average Sharpe Ratio** | ~1.65 |
| **Positive Years** | 11 out of 12 |

---

## Results Analysis

### Key Observations

1. **Strong Risk-Adjusted Returns**
   - Sharpe ratios above 1.0 in 10 of 12 years
   - Exceptional performance in 2019 (Sharpe 3.14) and 2024 (Sharpe 2.81)

2. **Downside Protection**
   - Maximum annual drawdown of -9.34% (2018)
   - Only one negative year (2017: -3.73%)
   - Diversification effectively mitigates Martingale tail risk

3. **Consistency**
   - Positive returns in 11 of 12 years
   - Returns remain positive even during market downturns (2018, 2022)

4. **Compounding Effect**
   - Tiered profit-taking captures gains while maintaining upside
   - Reinvestment of profits amplifies long-term returns

---

## Backtest Framework

- **Platform**: vn.py (`PortfolioStrategy` module)
- **Data Frequency**: Daily
- **Universe**: 100+ ETFs across multiple asset classes
- **Period**: 2015-01-01 to 2026-06-01
