# COVID Dashboard - AI Agent Instructions

## Project Overview
This is a COVID-19 data dashboard project built with Python. The main application logic resides in `covid.py`.

## Architecture & Components

### Core Module Structure
- **`covid.py`**: Primary entry point and main application logic. Contains data processing, visualization, and dashboard rendering.

### Development Patterns

#### Data Processing
- Use pandas for COVID-19 dataset manipulation (time-series, geographic aggregation)
- Apply consistent date formatting (ISO 8601: YYYY-MM-DD)
- Handle missing/NaN values explicitly with `.fillna()` or `.dropna()` with justification

#### Dashboard Development
- Leverage a Python dashboard framework (likely Streamlit, Dash, or Flask)
- Organize metrics/visualizations as reusable components
- Cache expensive computations to avoid redundant API calls or data processing

#### Configuration Management
- Define environment-specific settings at module level or via `.env` files
- Avoid hardcoding API endpoints, file paths, or credentials in code

## Developer Workflows

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python covid.py
```

### Testing & Validation
- Test data transformations with sample COVID datasets (Johns Hopkins or similar)
- Validate date ranges and geographic filters before rendering
- Use print/logging statements for debugging data pipeline issues

## Key Files & Patterns
- **`covid.py`**: Central module for dashboard logic, data loading, and visualization
- **Dependencies** (inferred): pandas, matplotlib/plotly (visualization), requests (API calls)

## Important Notes
- COVID data is time-sensitive; ensure data refresh intervals are documented
- Geographic data (country/state names) requires careful standardization
- Timestamps and timezone handling are critical for accurate time-series analysis

## Git Workflow
- Commit changes with clear messages describing data logic or feature additions
- Keep sensitive data (API keys, credentials) out of version control
