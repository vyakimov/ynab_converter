# YNAB CSV Converter

A web application that converts eksport.csv files to YNAB-compatible CSV format.

## Project Structure

- `convert.py` - Core converter logic (command-line tool)
- `app.py` - Flask web application 
- `templates/index.html` - Web interface
- `pyproject.toml` - Python project configuration

## How to Run

### Web App
```bash
uv run python app.py
```
Access at `http://localhost:5000`

### Command Line
```bash
uv run python convert.py input.csv              # writes ynab_data_YYYYMMDD.csv next to the input
uv run python convert.py -i input.csv -o output.csv
```
The input may be given positionally or with `-i`. Without `-o`, the output lands
in the input's folder as `ynab_data_{date}.csv`.

## Dependencies

- pandas - Data processing
- flask - Web framework
- Python 3.12+

## Converter Details

The converter (`convert.py`):
- Reads semicolon-separated CSV files
- Auto-detects the date, payee, and amount columns rather than relying on their
  position, so extra columns in a bank export don't break it
- Ignores running-balance columns (detected by checking whether a numeric column
  is the running total of another one) — these otherwise look like huge inflows
- Splits amounts into Inflow/Outflow columns for YNAB
- Handles European number formatting (comma as decimal separator)
- Skips header rows and any row without a usable amount
- Outputs properly quoted CSV files

Known bank export layouts, both supported:
- `date;text;amount;currency`
- `date;text;amount;balance;currency`

## Web Interface

Simple upload/download interface that:
- Accepts CSV files only
- Uses temporary files for processing
- Automatically downloads converted files
- Shows error messages for invalid files

## Testing Commands

Run linting/type checking:
```bash
# Add appropriate commands when available
```