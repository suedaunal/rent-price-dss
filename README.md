#  Rental Price Evaluation and Decision Support System

## Overview

This project is a data-driven rental housing analytics and decision support system designed to evaluate whether a rental listing is fairly priced, overpriced, or underpriced compared to similar properties in the market.

The system combines comparative analytics, regional benchmarking, and multi-criteria scoring methods to support more transparent and informed rental decisions.

Rather than only displaying listing data, the project aims to generate explainable pricing insights and recommendation-based evaluations for users.

---

## Problem Statement

Rental markets contain significant price inconsistencies and information asymmetry.

Users often struggle to understand:

- whether a listing reflects its actual market value
- how it compares to similar properties
- which property attributes justify higher prices

This project addresses the following question:

> “Does this property really justify its rental price?”

---

## Project Objectives

The system aims to:

- analyze rental market trends
- benchmark listings against similar properties
- evaluate rental fairness through scoring models
- generate explainable decision support outputs
- visualize regional pricing behavior

---

## System Architecture

The project consists of four main layers:

### 1. Data Collection Layer
Publicly available rental listing data is collected and structured for analysis purposes.

### 2. Data Processing Layer
Raw data is cleaned and transformed through:

- duplicate removal
- missing value handling
- feature engineering
- outlier filtering

### 3. Analytics & Scoring Engine
The system evaluates listings using:

- comparative price analysis
- m²-based pricing metrics
- regional benchmarking
- weighted multi-criteria scoring

### 4. Decision Support Layer
The final system produces interpretable outputs such as:

- Fair Price
- Overpriced
- Underpriced

and generates recommendation-based insights including:

- “Price is above district average”
- “Transportation advantage supports pricing”
- “Negotiation opportunity detected”

---

## Features

- Rental price benchmarking
- m² price analysis
- Regional market comparison
- Fair Rent Score calculation
- Explainable recommendation engine
- Comparative listing evaluation
- Dashboard-based visualization

---

## Feature Engineering

Examples of generated analytical features include:

| Feature | Description |
|---|---|
| price_per_m2 | Rental price divided by square meters |
| district_avg_price | Average district rental price |
| relative_price_index | Listing price compared to district average |
| building_age_group | Categorized building age |
| fair_rent_score | Final weighted fairness score |

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Data processing and analytics |
| Pandas | Data manipulation |
| BeautifulSoup / Selenium | Data collection |
| Excel | Data validation and reporting |
| Power BI | Dashboard visualization |
| MS Project | Project planning |
| Git & GitHub | Version control |

---

## Dashboard Content

The dashboard includes:

- district-based rental comparisons
- average rental prices
- overpriced property detection
- fair rent scoring
- pricing distribution analysis
- comparative market insights

---

## Future Improvements

Potential future developments include:

- machine learning-based rent prediction
- live data integration
- map-based analytics
- recommendation optimization
- interactive web application

---

## Data & Privacy

The dataset was created using publicly available listing information collected for educational and analytical purposes.

All data was anonymized and processed to avoid sharing personally identifiable information.

The full raw dataset is not publicly shared.

---

## Project Perspective

This project was developed not only as a data analysis study, but also as a pricing intelligence and decision support system focused on improving transparency in rental market evaluations
