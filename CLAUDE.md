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
uv run python convert.py -i input.csv -o output.csv
```

## Dependencies

- pandas - Data processing
- flask - Web framework
- Python 3.12+

## Converter Details

The converter (`convert.py`):
- Reads semicolon-separated CSV files
- Auto-detects amount column (rightmost numeric column)
- Splits amounts into Inflow/Outflow columns for YNAB
- Handles European number formatting (comma as decimal separator)
- Outputs properly quoted CSV files

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