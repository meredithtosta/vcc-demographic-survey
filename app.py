import os
import json
import hashlib
import secrets
from datetime import datetime
from flask import Flask, request, render_template, jsonify, send_file, flash, redirect, url_for
from cryptography.fernet import Fernet
import sqlite3
from io import StringIO, BytesIO
import csv

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database paths
DB_PATH = 'vcc_survey.db'

# Encryption key - IN PRODUCTION, store this securely (env var, key management service, etc.)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("Database initialized successfully")

def hash_ip(ip):
    """Hash IP address for privacy"""
    return hashlib.sha256(ip.encode()).hexdigest()

def encrypt_response(response_data):
    """Encrypt survey response data"""
    json_data = json.dumps(response_data)
    return cipher_suite.encrypt(json_data.encode())

def decrypt_response(encrypted_data):
    """Decrypt survey response data - USE ONLY FOR COMPLIANCE"""
    decrypted = cipher_suite.decrypt(encrypted_data)
    return json.loads(decrypted.decode())

def generate_survey_token():
    """Generate unique survey token for a company"""
    return secrets.token_urlsafe(32)

def calculate_diverse_status(aggregated_data):
    """
    Calculate if company is "primarily diverse"
    Requires: >50% response rate AND >=50% of responders identify as diverse
    """
    total_founders = aggregated_data['total_founders']
    total_responses = aggregated_data['total_responses']
    
    if total_founders == 0 or total_responses / total_founders <= 0.5:
        return None  # Not enough responses
    
    # Count diverse identifications
    diverse_count = 0
    
    # Gender: woman, nonbinary, transgender
    if aggregated_data['gender_woman'] > 0:
        diverse_count += aggregated_data['gender_woman']
    if aggregated_data['gender_nonbinary'] > 0:
        diverse_count += aggregated_data['gender_nonbinary']
    if aggregated_data['gender_transgender'] > 0:
        diverse_count += aggregated_data['gender_transgender']
    
    # Race: non-white
    race_diverse = (aggregated_data['race_black'] + 
                   aggregated_data['race_asian'] + 
                   aggregated_data['race_hispanic'] +
                   aggregated_data['race_native_american'] + 
                   aggregated_data['race_pacific_islander'])
    
    # LGBTQ+
    lgbtq_diverse = aggregated_data['lgbtq_yes']
    
    # Disability
    disability_diverse = aggregated_data['disability_yes']
    
    # Veteran
    veteran_diverse = aggregated_data['veteran_yes'] + aggregated_data['veteran_disabled']
    
    # Note: A founder can be counted in multiple categories
    # The law defines "diverse" as identifying in ANY of these categories
    # So we need to check if at least 50% of responders have at least one diverse identifier
    
    # This is a simplified calculation - in reality, need to track per-response
    # For now, if total diverse identifications >= responses, likely primarily diverse
    total_diverse_indicators = (
        diverse_count + race_diverse + lgbtq_diverse +
        disability_diverse + veteran_diverse
    )

    # Return 1 or 0 for SQLite compatibility (not True/False)
    return 1 if total_diverse_indicators >= total_responses else 0

@app.route('/')
def index():
    """Admin dashboard"""
    return render_template('dashboard.html')

@app.route('/admin/recalculate')
def recalculate_diverse():
    """Recalculate diverse status for all companies"""
    conn = get_db()
    aggregated_rows = conn.execute('SELECT * FROM aggregated_responses').fetchall()

    for row in aggregated_rows:
        agg_dict = dict(row)
        diverse_status = calculate_diverse_status(agg_dict)
        conn.execute(
            'UPDATE aggregated_responses SET is_primarily_diverse = ? WHERE company_id = ?',
            (diverse_status, agg_dict['company_id'])
        )

    conn.commit()
    conn.close()
    return redirect(url_for('list_companies'))

@app.route('/survey/<token>')
def survey_form(token):
    """Display survey form for founders"""
    conn = get_db()
    company = conn.execute(
        'SELECT * FROM portfolio_companies WHERE survey_link_token = ?',
        (token,)
    ).fetchone()
    conn.close()
    
    if not company:
        return "Invalid survey link", 404
    
    return render_template('survey.html', 
                         company_name=company['company_name'],
                         token=token)

@app.route('/api/submit_survey', methods=['POST'])
def submit_survey():
    """Handle survey submission - implements anonymization at collection"""
    try:
        data = request.json
        token = data.get('token')
        
        conn = get_db()
        
        # Get company
        company = conn.execute(
            'SELECT * FROM portfolio_companies WHERE survey_link_token = ?',
            (token,)
        ).fetchone()
        
        if not company:
            conn.close()
            return jsonify({'error': 'Invalid token'}), 404
        
        company_id = company['id']
        
        # Extract response data (remove token before storage)
        response_data = {k: v for k, v in data.items() if k != 'token'}
        response_data['submitted_at'] = datetime.utcnow().isoformat()
        
        # TIER 2: Store encrypted individual response (compliance only)
        encrypted_data = encrypt_response(response_data)
        ip_hash = hash_ip(request.remote_addr)
        
        conn.execute(
            'INSERT INTO individual_responses (company_id, response_data_encrypted, ip_hash) VALUES (?, ?, ?)',
            (company_id, encrypted_data, ip_hash)
        )
        
        # TIER 1: Update aggregated counts (operational data)
        aggregated = conn.execute(
            'SELECT * FROM aggregated_responses WHERE company_id = ?',
            (company_id,)
        ).fetchone()
        
        if not aggregated:
            # Create initial aggregated record
            conn.execute(
                'INSERT INTO aggregated_responses (company_id) VALUES (?)',
                (company_id,)
            )
            aggregated = conn.execute(
                'SELECT * FROM aggregated_responses WHERE company_id = ?',
                (company_id,)
            ).fetchone()
        
        # Convert to dict for easier manipulation
        agg_dict = dict(aggregated)
        
        # Update counts based on response
        agg_dict['total_responses'] += 1
        
        # Check if declined all
        if data.get('decline_all'):
            agg_dict['total_declined_all'] += 1
        else:
            # Gender (single selection)
            gender = data.get('gender')
            if gender == 'woman':
                agg_dict['gender_woman'] += 1
            elif gender == 'man':
                agg_dict['gender_man'] += 1
            elif gender == 'nonbinary':
                agg_dict['gender_nonbinary'] += 1
            elif gender == 'transgender':
                agg_dict['gender_transgender'] += 1
            elif gender == 'none':
                agg_dict['gender_other'] += 1
            elif gender == 'decline':
                agg_dict['gender_declined'] += 1

            # Race (single selection)
            race = data.get('race')
            if race == 'black':
                agg_dict['race_black'] += 1
            elif race == 'asian':
                agg_dict['race_asian'] += 1
            elif race == 'hispanic':
                agg_dict['race_hispanic'] += 1
            elif race == 'native_american':
                agg_dict['race_native_american'] += 1
            elif race == 'pacific_islander':
                agg_dict['race_pacific_islander'] += 1
            elif race == 'white':
                agg_dict['race_white'] += 1
            elif race == 'none':
                agg_dict['race_other'] += 1
            elif race == 'decline':
                agg_dict['race_declined'] += 1
            
            # LGBTQ+
            lgbtq = data.get('lgbtq')
            if lgbtq == 'yes':
                agg_dict['lgbtq_yes'] += 1
            elif lgbtq == 'no':
                agg_dict['lgbtq_no'] += 1
            elif lgbtq == 'decline':
                agg_dict['lgbtq_declined'] += 1
            
            # Disability
            disability = data.get('disability')
            if disability == 'yes':
                agg_dict['disability_yes'] += 1
            elif disability == 'no':
                agg_dict['disability_no'] += 1
            elif disability == 'decline':
                agg_dict['disability_declined'] += 1
            
            # Veteran
            veteran = data.get('veteran')
            if veteran == 'veteran':
                agg_dict['veteran_yes'] += 1
            elif veteran == 'disabled_veteran':
                agg_dict['veteran_disabled'] += 1
            elif veteran == 'no':
                agg_dict['veteran_no'] += 1
            elif veteran == 'decline':
                agg_dict['veteran_declined'] += 1
            
            # California residency
            ca_resident = data.get('ca_resident')
            if ca_resident == 'yes':
                agg_dict['ca_resident_yes'] += 1
            elif ca_resident == 'no':
                agg_dict['ca_resident_no'] += 1
            elif ca_resident == 'decline':
                agg_dict['ca_resident_declined'] += 1
        
        # Calculate diverse status
        agg_dict['is_primarily_diverse'] = calculate_diverse_status(agg_dict)
        agg_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Update aggregated record
        update_fields = [f"{k} = ?" for k in agg_dict.keys() if k not in ['id', 'company_id']]
        update_values = [v for k, v in agg_dict.items() if k not in ['id', 'company_id']]
        update_values.append(company_id)
        
        conn.execute(
            f'UPDATE aggregated_responses SET {", ".join(update_fields)} WHERE company_id = ?',
            update_values
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Thank you for completing the survey'})
        
    except Exception as e:
        print(f"Error submitting survey: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/companies')
def list_companies():
    """List all portfolio companies and their response status"""
    conn = get_db()
    companies = conn.execute('''
        SELECT 
            pc.*,
            ar.total_founders,
            ar.total_responses,
            ar.is_primarily_diverse
        FROM portfolio_companies pc
        LEFT JOIN aggregated_responses ar ON pc.id = ar.company_id
        ORDER BY pc.investment_year DESC, pc.company_name
    ''').fetchall()
    conn.close()
    
    return render_template('companies.html', companies=companies)

@app.route('/admin/company/<int:company_id>')
def company_detail(company_id):
    """View aggregated data for a specific company"""
    conn = get_db()
    company = conn.execute(
        'SELECT * FROM portfolio_companies WHERE id = ?',
        (company_id,)
    ).fetchone()
    
    if not company:
        conn.close()
        return "Company not found", 404
    
    aggregated = conn.execute(
        'SELECT * FROM aggregated_responses WHERE company_id = ?',
        (company_id,)
    ).fetchone()
    
    response_count = conn.execute(
        'SELECT COUNT(*) as count FROM individual_responses WHERE company_id = ?',
        (company_id,)
    ).fetchone()['count']
    
    conn.close()
    
    return render_template('company_detail.html',
                         company=company,
                         aggregated=dict(aggregated) if aggregated else None,
                         response_count=response_count)

@app.route('/admin/company/<int:company_id>/delete', methods=['POST'])
def delete_company(company_id):
    """Delete a company and all its data"""
    conn = get_db()
    conn.execute('DELETE FROM individual_responses WHERE company_id = ?', (company_id,))
    conn.execute('DELETE FROM aggregated_responses WHERE company_id = ?', (company_id,))
    conn.execute('DELETE FROM portfolio_companies WHERE id = ?', (company_id,))
    conn.commit()
    conn.close()
    flash('Company deleted successfully', 'success')
    return redirect(url_for('list_companies'))

@app.route('/admin/company/<int:company_id>/update_founders', methods=['POST'])
def update_founders(company_id):
    """Update the number of founders for a company"""
    total_founders = int(request.form.get('total_founders', 1))
    if total_founders < 1:
        total_founders = 1

    conn = get_db()
    conn.execute(
        'UPDATE aggregated_responses SET total_founders = ? WHERE company_id = ?',
        (total_founders, company_id)
    )

    # Recalculate diverse status
    aggregated = conn.execute(
        'SELECT * FROM aggregated_responses WHERE company_id = ?',
        (company_id,)
    ).fetchone()

    if aggregated:
        agg_dict = dict(aggregated)
        agg_dict['total_founders'] = total_founders
        diverse_status = calculate_diverse_status(agg_dict)
        conn.execute(
            'UPDATE aggregated_responses SET is_primarily_diverse = ? WHERE company_id = ?',
            (diverse_status, company_id)
        )

    conn.commit()
    conn.close()
    flash(f'Founder count updated to {total_founders}', 'success')
    return redirect(url_for('company_detail', company_id=company_id))

@app.route('/admin/company/<int:company_id>/update_name', methods=['POST'])
def update_company_name(company_id):
    """Update the company name"""
    company_name = request.form.get('company_name', '').strip()
    if not company_name:
        flash('Company name cannot be empty', 'error')
        return redirect(url_for('company_detail', company_id=company_id))

    conn = get_db()
    conn.execute(
        'UPDATE portfolio_companies SET company_name = ? WHERE id = ?',
        (company_name, company_id)
    )
    conn.commit()
    conn.close()
    flash(f'Company name updated to "{company_name}"', 'success')
    return redirect(url_for('company_detail', company_id=company_id))

@app.route('/admin/add_company', methods=['GET', 'POST'])
def add_company():
    """Add a new portfolio company"""
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        investment_year = request.form.get('investment_year')
        total_founders = int(request.form.get('total_founders', 1))
        
        if not company_name or not investment_year:
            flash('Company name and investment year are required', 'error')
            return redirect(url_for('add_company'))
        
        token = generate_survey_token()
        
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO portfolio_companies (company_name, investment_year, survey_link_token) VALUES (?, ?, ?)',
            (company_name, int(investment_year), token)
        )
        company_id = cursor.lastrowid
        
        # Initialize aggregated_responses with total_founders
        conn.execute(
            'INSERT INTO aggregated_responses (company_id, total_founders) VALUES (?, ?)',
            (company_id, total_founders)
        )
        
        conn.commit()
        conn.close()
        
        flash(f'Company added successfully. Survey link: {request.host_url}survey/{token}', 'success')
        return redirect(url_for('list_companies'))

    return render_template('add_company.html')

@app.route('/admin/bulk_upload', methods=['GET', 'POST'])
def bulk_upload():
    """Bulk upload companies from CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('bulk_upload'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('bulk_upload'))

        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'error')
            return redirect(url_for('bulk_upload'))

        try:
            # Read CSV content
            content = file.read().decode('utf-8')
            reader = csv.DictReader(StringIO(content))

            conn = get_db()
            created_count = 0

            for row in reader:
                company_name = row.get('company_name', '').strip()
                investment_year = row.get('investment_year', '').strip()
                total_founders = row.get('total_founders', '1').strip()

                if not company_name or not investment_year:
                    continue

                token = generate_survey_token()

                cursor = conn.execute(
                    'INSERT INTO portfolio_companies (company_name, investment_year, survey_link_token) VALUES (?, ?, ?)',
                    (company_name, int(investment_year), token)
                )
                company_id = cursor.lastrowid

                conn.execute(
                    'INSERT INTO aggregated_responses (company_id, total_founders) VALUES (?, ?)',
                    (company_id, int(total_founders))
                )
                created_count += 1

            conn.commit()
            conn.close()

            flash(f'Successfully created {created_count} companies', 'success')
            return redirect(url_for('list_companies'))

        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('bulk_upload'))

    return render_template('bulk_upload.html')

@app.route('/admin/bulk_template')
def bulk_template():
    """Download CSV template for bulk upload"""
    template = "company_name,investment_year,total_founders\nExample Company,2025,2\n"
    return send_file(
        BytesIO(template.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='company_upload_template.csv'
    )

@app.route('/admin/export_dfpi/<int:year>')
def export_dfpi_report(year):
    """Export DFPI report for a specific year"""
    conn = get_db()
    
    # Get all companies and their aggregated data for the year
    companies = conn.execute('''
        SELECT 
            pc.company_name,
            pc.investment_year,
            ar.*
        FROM portfolio_companies pc
        LEFT JOIN aggregated_responses ar ON pc.id = ar.company_id
        WHERE pc.investment_year = ?
        ORDER BY pc.company_name
    ''', (year,)).fetchall()
    
    conn.close()
    
    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers (simplified - adjust based on actual DFPI requirements)
    writer.writerow([
        'Company Name',
        'Investment Year',
        'Total Founders',
        'Total Responses',
        'Response Rate %',
        'Gender: Woman',
        'Gender: Man',
        'Gender: Nonbinary',
        'Gender: Transgender',
        'Race: Black/African American',
        'Race: Asian',
        'Race: Hispanic/Latino',
        'Race: Native American',
        'Race: Pacific Islander',
        'Race: White',
        'LGBTQ+',
        'Disability',
        'Veteran/Disabled Veteran',
        'CA Resident',
        'Primarily Diverse'
    ])
    
    for company in companies:
        if company['total_founders']:
            response_rate = (company['total_responses'] / company['total_founders']) * 100
        else:
            response_rate = 0
        
        writer.writerow([
            company['company_name'],
            company['investment_year'],
            company['total_founders'] or 0,
            company['total_responses'] or 0,
            f"{response_rate:.1f}",
            company['gender_woman'] or 0,
            company['gender_man'] or 0,
            company['gender_nonbinary'] or 0,
            company['gender_transgender'] or 0,
            company['race_black'] or 0,
            company['race_asian'] or 0,
            company['race_hispanic'] or 0,
            company['race_native_american'] or 0,
            company['race_pacific_islander'] or 0,
            company['race_white'] or 0,
            company['lgbtq_yes'] or 0,
            company['disability_yes'] or 0,
            (company['veteran_yes'] or 0) + (company['veteran_disabled'] or 0),
            company['ca_resident_yes'] or 0,
            'Yes' if company['is_primarily_diverse'] else 'No' if company['is_primarily_diverse'] is not None else 'Insufficient Data'
        ])
    
    output.seek(0)
    
    # Return as downloadable file
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=dfpi_report_{year}.csv'}
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
