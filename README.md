# VCC Demographic Survey System

California-compliant system for collecting and managing founder demographic data under the Fair Investment Practices by Venture Capital Companies Law (SB 54/SB 164).

## Key Features

### Two-Tier Data Architecture
**Designed for compliance with California Corporations Code § 27501(d)**

1. **Tier 1 - Operational Data (Hot Storage)**
   - Aggregated counts only
   - No individual identifiers
   - Used for reporting and analysis
   - What you actually work with day-to-day

2. **Tier 2 - Compliance Data (Cold Storage)**
   - Encrypted individual responses
   - Access-logged for audit trail
   - 5-year retention for DFPI inspection
   - Separate permissions required

### Compliance Features

✅ **Anonymization at Collection**: Survey responses are immediately split into aggregated counts (Tier 1) and encrypted individual records (Tier 2)

✅ **No Founder Identification**: Survey links are company-specific, not founder-specific

✅ **Automatic Aggregation**: Real-time calculation of demographic statistics

✅ **Encrypted Storage**: Individual responses encrypted using Fernet (symmetric encryption)

✅ **Access Logging**: All access to individual responses is logged

✅ **DFPI Export**: One-click CSV export for state reporting

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

The database will be automatically created when you first run the app:

```bash
python app.py
```

This creates `vcc_survey.db` with the proper schema.

### 3. Access the Application

Open your browser to: `http://localhost:5000`

## Usage Workflow

### For Administrators

1. **Add a Portfolio Company**
   - Navigate to "Add Portfolio Company"
   - Enter company name, investment year, and number of founders
   - System generates unique survey link

2. **Distribute Survey Links**
   - Copy the generated survey link
   - Send to all founding team members
   - Each founder completes survey independently

3. **Monitor Responses**
   - View "Companies" list to see response rates
   - Click on company to view aggregated data
   - No individual responses are visible

4. **Generate DFPI Reports**
   - Export CSV for annual filing
   - Data is pre-aggregated per compliance requirements

### For Founders

1. Receive unique survey link from VC firm
2. Complete voluntary demographic survey
3. Submit - response is immediately anonymized
4. No way to trace response back to individual

## Security & Privacy

### Data Separation Guarantees

```
Survey Submission
       ↓
  [Split Point]
       ↓
   ┌───┴────┐
   ↓        ↓
Tier 1     Tier 2
(Counts)   (Encrypted)
   ↓
Operational  Compliance
Dashboard    Storage
```

### Encryption

Individual responses are encrypted using `cryptography.fernet`:
- Symmetric encryption (AES 128-bit)
- Each response encrypted separately
- Encryption key must be stored securely

### Production Deployment Notes

**CRITICAL**: Before deploying to production, you MUST:

1. **Set Encryption Key Securely**
   ```bash
   export ENCRYPTION_KEY="your-securely-generated-key"
   ```
   - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - Store in environment variable or key management service (AWS KMS, Azure Key Vault, etc.)
   - NEVER commit encryption key to Git

2. **Set Secret Key**
   ```bash
   export SECRET_KEY="your-flask-secret-key"
   ```

3. **Use Production Database**
   - Replace SQLite with PostgreSQL or MySQL for production
   - Update connection string in `app.py`

4. **Enable HTTPS**
   - Survey links contain sensitive data
   - Use SSL/TLS certificate (Let's Encrypt, etc.)

5. **Implement Authentication**
   - Current system has no auth (MVP)
   - Add login system for admin dashboard
   - Consider role-based access control

6. **Backup Strategy**
   - Regular backups of database
   - Encrypted backups for compliance data
   - Test restore procedures

## Database Schema

### portfolio_companies
Stores basic company information and survey tokens.

### aggregated_responses
**Tier 1**: Operational data - all aggregated counts, no PII.

### individual_responses
**Tier 2**: Compliance data - encrypted responses, access-logged.

### compliance_access_log
Audit trail for any access to individual responses.

## Legal Compliance

### California Requirements

This system implements:

- **§ 27501(d)(1)**: Collect survey response data in a manner that does not associate the survey response data with an individual founding team member ✅

- **§ 27501(d)(2)**: Report the survey response data in a manner that does not associate the survey response data with an individual founding team member ✅

- **5-year retention**: Individual responses stored for DFPI inspection ✅

- **Voluntary participation**: Survey explicitly states voluntary nature ✅

- **No adverse action**: Survey disclaims any negative consequences ✅

### DFPI Filing

Export reports via: `/admin/export_dfpi/<year>`

CSV includes all required fields:
- Aggregated demographic counts
- Primarily diverse calculation
- Response rates
- Declined-to-state tracking

## Development

### Project Structure

```
vcc-demographic-survey/
├── app.py                 # Main Flask application
├── schema.sql            # Database schema
├── requirements.txt      # Python dependencies
├── templates/
│   ├── dashboard.html    # Admin home
│   ├── survey.html       # Founder survey form
│   ├── companies.html    # Company list
│   ├── company_detail.html # Aggregated data view
│   └── add_company.html  # Add company form
└── README.md
```

### Running in Development

```bash
python app.py
```

Access at `http://localhost:5000`

Debug mode is enabled by default.

### Testing

1. Add a test company
2. Get survey link
3. Submit multiple responses
4. Verify aggregation
5. Check no individual data is visible
6. Export CSV to verify format

## Important Notes

### What You CAN'T See

- Individual founder responses
- Which founder selected what
- Any way to link response to person

### What You CAN See

- Total response counts per category
- Aggregated percentages
- Response rate metrics
- Primarily diverse calculation

### Accessing Individual Responses

**Only for DFPI Compliance**

Individual encrypted responses are stored but should ONLY be decrypted if:
1. DFPI officially requests them
2. Legal requires for compliance audit

To access (requires code modification for security):
```python
# Add compliance_access_log entry first
# Then decrypt specific response
response = decrypt_response(encrypted_data)
```

## Customization

### Adjusting "Primarily Diverse" Calculation

The law defines "primarily diverse" as:
- >50% of founding team responded
- ≥50% of responders identify as diverse

Current implementation in `calculate_diverse_status()` function.

### Modifying Survey Questions

Survey matches DFPI official form. To modify:
1. Update `templates/survey.html`
2. Update aggregation logic in `app.py`
3. Update database schema
4. Update export format

## Support

### Common Issues

**"Invalid survey link"**: Token doesn't match any company - check URL.

**"Submission failed"**: Check server logs for encryption/database errors.

**Response rate shows 0%**: Make sure to set total_founders when adding company.

### Troubleshooting

1. Check `vcc_survey.db` exists
2. Verify encryption key is set
3. Check browser console for JavaScript errors
4. Review Flask server logs

## License

Proprietary - Offline Ventures internal use only.

## Credits

Built for Offline Ventures LLC to comply with California Fair Investment Practices by Venture Capital Companies Law (SB 54/SB 164).
