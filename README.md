# 5G Cluster Dashboard

A Streamlit application for monitoring 5G cluster KPIs using ClickHouse.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure ClickHouse credentials in `.env`

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Project Structure

- `app.py`: Main Streamlit application
- `config/`: Configuration files
- `data/`: Data access and processing
- `ui/`: UI components
- `utils/`: Utility functions
