# Business Dashboard

Professional, clean, and user-friendly business dashboard built with Python and HTML.

## Badges

- Build: ![CI](https://github.com/Tahleel1611/business_dashboard/actions/workflows/ci.yml/badge.svg)
- License: MIT
- Python: 3.10+

## Overview

This repository contains a business dashboard project. It focuses on presenting business metrics and KPIs in a clear, accessible way. The project is primarily written in Python (backend logic) and HTML (front-end templates).

## Features

- Modular Python code for data processing
- Clean HTML templates for a responsive dashboard
- CI setup for tests and linting
- **AI-Powered Sales Analytics** - Predict sales trends and get improvement suggestions
- Sales tracking and reporting
- Inventory management with low stock alerts
- Product categorization and GST calculations

## Quick start

1. Clone the repo:

   ```bash
   git clone https://github.com/Tahleel1611/business_dashboard.git
   cd business_dashboard
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate  # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run database migrations:

   ```bash
   python manage.py migrate
   ```

5. Run tests:

   ```bash
   python manage.py test
   ```

6. Run the app:

   ```bash
   python manage.py runserver
   ```

7. Access the dashboard at `http://localhost:8000`

## AI Sales Analytics

The dashboard includes an AI-powered sales analytics feature that:

- **Predicts Sales Trends**: Uses machine learning (linear regression) to analyze historical data and predict future sales for the next 30 days
- **Provides AI Suggestions**: Generates actionable recommendations based on detected trends (increasing, decreasing, or stable)
- **Identifies Top Products**: Shows best-selling products to help focus inventory and marketing efforts
- **Highlights Underperforming Products**: Points out products that need attention or promotional strategies
- **Visualizes Data**: Displays interactive charts showing historical sales and future predictions

Access the AI Analytics feature from the navigation menu or visit `/sales-analytics-ai/`.

## Project structure

- `README.md` - Project overview and setup
- `.github/` - GitHub templates and workflows
- `templates/` - HTML templates
- `src/` - Python source code
- `requirements.txt` - Python dependencies

## Contributing

See `CONTRIBUTING.md` for guidelines on contributing, pull requests, and coding standards.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or support, open an issue or contact the repository owner: https://github.com/Tahleel1611
