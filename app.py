#!/usr/bin/env python3
import os
import tempfile
from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from convert import convert
import pandas as pd
import csv

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as temp_input:
                file.save(temp_input.name)
                input_path = temp_input.name
            
            # Convert using existing converter
            converted_df = convert(input_path)
            
            # Save converted data to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_output:
                converted_df.to_csv(temp_output, index=False, quoting=csv.QUOTE_ALL)
                output_path = temp_output.name
            
            # Clean up input file
            os.unlink(input_path)
            
            # Generate download filename
            original_name = secure_filename(file.filename)
            name_without_ext = os.path.splitext(original_name)[0]
            download_filename = f"{name_without_ext}_ynab.csv"
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=download_filename,
                mimetype='text/csv'
            )
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}')
            return redirect(url_for('index'))
    else:
        flash('Please upload a CSV file')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)