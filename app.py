# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
import jdatetime
import json
import pandas as pd
from datetime import date, datetime
from io import BytesIO

# ایجاد یک نمونه از Flask
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# پیکربندی پایگاه داده SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ایجاد نمونه از SQLAlchemy
db = SQLAlchemy(app)

# -----------------
# مدل‌های پایگاه داده
# -----------------
class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    yearly_volume = db.Column(db.Float, nullable=False)
    repeats = db.Column(db.Integer, nullable=False)
    contract_duration = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)
    price_list_name = db.Column(db.String(255), nullable=True)
    chapter_name = db.Column(db.String(255), nullable=True)
    contract = db.relationship('Contract', backref='records_rel', lazy=True)

class Contract(db.Model):
    __tablename__ = 'contracts'
    id = db.Column(db.Integer, primary_key=True)
    contract_name = db.Column(db.String(255), nullable=False)
    employer_name = db.Column(db.String(255), nullable=False)
    contractor_name = db.Column(db.String(255), nullable=False)
    contract_date = db.Column(db.Date, nullable=False)
    contract_number = db.Column(db.String(50), nullable=False)
    initial_estimate = db.Column(db.Float, nullable=False)
    contract_amount = db.Column(db.Float, nullable=False)
    price_lists = db.Column(db.Text, nullable=True)
    chapters = db.Column(db.Text, nullable=True)
    calculation_type = db.Column(db.String(50), nullable=False)
    adjustment_included = db.Column(db.Boolean, default=False)
    survey_with_address = db.Column(db.Boolean, default=False)
    delivery_date = db.Column(db.Date, nullable=False)
    
class Survey(db.Model):
    __tablename__ = 'surveys'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255), nullable=False)
    item_title = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)
    contract = db.relationship('Contract', backref='surveys_rel', lazy=True)

# -----------------
# روت‌های Flask
# -----------------
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/record_form', methods=['GET', 'POST'])
def record_form():
    contracts = Contract.query.all()
    # Decode JSON data for display and logic
    for contract in contracts:
        contract.price_lists_json = json.loads(contract.price_lists) if contract.price_lists else []
    
    if request.method == 'POST':
        try:
            # If it's a regular form submission
            contract_id = request.form['contract_select']
            price_list_name = request.form['price_list_select']
            chapter_name = request.form['chapter_select']
            
            new_record = Record(
                code=request.form['code'],
                description=request.form['description'],
                unit=request.form['unit'],
                yearly_volume=float(request.form['yearly_volume']),
                repeats=int(request.form['repeats']),
                contract_duration=int(request.form['contract_duration']),
                unit_price=float(request.form['unit_price']),
                contract_id=contract_id,
                price_list_name=price_list_name,
                chapter_name=chapter_name
            )
            db.session.add(new_record)
            db.session.commit()
            return redirect(url_for('record_form'))
        except Exception as e:
            print(f"Error saving record: {e}")
            return "An error occurred while saving the record.", 500
    
    records = Record.query.all()
    return render_template('record_form.html', contracts=contracts, records=records, jdatetime=jdatetime)

@app.route('/upload_records_excel', methods=['POST'])
def upload_records_excel():
    file = request.files['file']
    contract_id = request.form.get('contract_id')
    price_list_name = request.form.get('price_list_name')
    chapter_name = request.form.get('chapter_name')
    
    if not file:
        return "No file selected.", 400

    try:
        df = pd.read_excel(file)
        new_records = []
        for index, row in df.iterrows():
            new_record = Record(
                code=row['کد فهرست بها'],
                description=row['شرح ردیف'],
                unit=row['واحد'],
                yearly_volume=row['حجم عملیات سالیانه'],
                repeats=row['تعداد تکرار'],
                contract_duration=row['مدت قرارداد'],
                unit_price=row['قیمت واحد'],
                contract_id=contract_id,
                price_list_name=price_list_name,
                chapter_name=chapter_name
            )
            new_records.append(new_record)
        
        db.session.bulk_save_objects(new_records)
        db.session.commit()
        return redirect(url_for('record_form'))
    
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        return "An error occurred while processing the Excel file.", 500

@app.route('/download_records_excel')
def download_records_excel():
    # Fetch all records from the database
    records = Record.query.all()
    
    # Prepare data for DataFrame
    data = [{
        'شرح ردیف': r.description,
        'کد فهرست بها': r.code,
        'واحد': r.unit,
        'حجم عملیات سالیانه': r.yearly_volume,
        'تعداد تکرار': r.repeats,
        'مدت قرارداد': r.contract_duration,
        'قیمت واحد': r.unit_price,
        'نام پیمان': r.contract.contract_name if r.contract else '',
        'فهرست بها': r.price_list_name,
        'فصل': r.chapter_name
    } for r in records]
    
    # Create a DataFrame from the data
    df = pd.DataFrame(data)
    
    # Create an in-memory buffer for the Excel file
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    
    # Send the file to the user
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='فهرست_بها.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/download_excel_template')
def download_excel_template():
    columns = ['کد فهرست بها', 'شرح ردیف', 'واحد', 'حجم عملیات سالیانه', 'تعداد تکرار', 'مدت قرارداد', 'قیمت واحد']
    df = pd.DataFrame(columns=columns)
    
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='فهرست_بها_نمونه.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/contract_form', methods=['GET', 'POST'])
def contract_form():
    if request.method == 'POST':
        try:
            # دریافت اطلاعات از فرم و تبدیل تاریخ شمسی به میلادی
            contract_date_gregorian = jdatetime.datetime.strptime(request.form['contract_date'], '%Y/%m/%d').togregorian()
            delivery_date_gregorian = jdatetime.datetime.strptime(request.form['delivery_date'], '%Y/%m/%d').togregorian()
            
            # دریافت داده‌های JSON از فیلدهای مخفی
            price_lists_data_json = request.form.get('price_lists_data', '[]')
            
            new_contract = Contract(
                contract_name=request.form['contract_name'],
                employer_name=request.form['employer_name'],
                contractor_name=request.form['contractor_name'],
                contract_date=contract_date_gregorian,
                contract_number=request.form['contract_number'],
                initial_estimate=float(request.form['initial_estimate']),
                contract_amount=float(request.form['contract_amount']),
                price_lists=price_lists_data_json,
                chapters='{}',
                calculation_type=request.form['calculation_type'],
                adjustment_included='adjustment_included' in request.form,
                survey_with_address='survey_with_address' in request.form,
                delivery_date=delivery_date_gregorian
            )
            db.session.add(new_contract)
            db.session.commit()
            return redirect(url_for('contract_form'))
        except Exception as e:
            print(f"Error saving contract: {e}")
            return "An error occurred while saving the contract.", 500
    
    contracts = Contract.query.all()
    # تبدیل رشته‌های JSON به دیکشنری برای نمایش در صفحه
    for contract in contracts:
        contract.price_lists_json = json.loads(contract.price_lists) if contract.price_lists else []

    return render_template('contract_form.html', contracts=contracts, jdatetime=jdatetime)

@app.route('/survey_form', methods=['GET', 'POST'])
def survey_form():
    contracts = Contract.query.all()
    if request.method == 'POST':
        try:
            contract_id = request.form['contract_select']
            
            new_survey = Survey(
                location=request.form['location'],
                item_title=request.form['item_title'],
                quantity=float(request.form['quantity']),
                unit=request.form['unit'],
                contract_id=contract_id
            )
            db.session.add(new_survey)
            db.session.commit()
            return redirect(url_for('survey_form'))
        except Exception as e:
            print(f"Error saving survey: {e}")
            return "An error occurred while saving the survey record.", 500
    
    surveys = Survey.query.all()
    # برای نمایش نام پیمان در جدول، پیمان مربوطه را نیز واکشی می‌کنیم
    for survey in surveys:
        survey.contract_name = survey.contract.contract_name if survey.contract else 'N/A'
    
    return render_template('survey_form.html', surveys=surveys, contracts=contracts, jdatetime=jdatetime)

@app.route('/upload_surveys_excel', methods=['POST'])
def upload_surveys_excel():
    file = request.files['file']
    contract_id = request.form.get('contract_id')

    if not file:
        return "No file selected.", 400
        
    try:
        df = pd.read_excel(file)
        new_surveys = []
        for index, row in df.iterrows():
            new_survey = Survey(
                location=row['محل'],
                item_title=row['عنوان موجودی متره'],
                quantity=row['مقدار'],
                unit=row['واحد'],
                contract_id=contract_id
            )
            new_surveys.append(new_survey)
            
        db.session.bulk_save_objects(new_surveys)
        db.session.commit()
        return redirect(url_for('survey_form'))
    
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        return "An error occurred while processing the Excel file.", 500

@app.route('/download_survey_template')
def download_survey_template():
    columns = ['محل', 'عنوان موجودی متره', 'مقدار', 'واحد']
    df = pd.DataFrame(columns=columns)
    
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name='متره_نمونه.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
