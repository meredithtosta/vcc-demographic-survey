# System Architecture

## Overview

The VCC Demographic Survey System implements a strict two-tier data architecture to comply with California Corporations Code § 27501(d), which requires that survey data be collected and reported "in a manner that does not associate the survey response data with an individual founding team member."

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Founder Survey Form                   │
│                  (templates/survey.html)                 │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ↓ POST /api/submit_survey
                        │
┌───────────────────────┴─────────────────────────────────┐
│              Flask Application (app.py)                  │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Data Split Point (Anonymization)         │   │
│  │  - Extracts demographic selections               │   │
│  │  - Generates counts                              │   │
│  │  - Encrypts full response                        │   │
│  │  - Stores in separate tables                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│         ┌───────────────┴───────────────┐               │
│         ↓                               ↓               │
│   ┌─────────────┐               ┌─────────────┐        │
│   │   TIER 1    │               │   TIER 2    │        │
│   │ Operational │               │ Compliance  │        │
│   └─────────────┘               └─────────────┘        │
└───────────────────────────────────────────────────────┘
                        │
                        ↓
┌───────────────────────┴─────────────────────────────────┐
│                   SQLite Database                        │
│               (vcc_survey.db)                            │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ TIER 1: Operational Data (Hot Storage)          │   │
│  │                                                   │   │
│  │  • aggregated_responses                          │   │
│  │    - Counts only (gender_woman: 3, etc.)        │   │
│  │    - No individual identifiers                   │   │
│  │    - Used for daily operations                   │   │
│  │    - Powers admin dashboard                      │   │
│  │    - Generates DFPI reports                      │   │
│  │                                                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ TIER 2: Compliance Data (Cold Storage)          │   │
│  │                                                   │   │
│  │  • individual_responses                          │   │
│  │    - Encrypted JSON blobs                        │   │
│  │    - Company ID only (not founder ID)           │   │
│  │    - 5-year retention                            │   │
│  │    - Access logged                               │   │
│  │    - For DFPI inspection only                    │   │
│  │                                                   │   │
│  │  • compliance_access_log                         │   │
│  │    - Who accessed compliance data                │   │
│  │    - When and why                                │   │
│  │                                                   │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

## Data Flow

### Survey Submission Flow

```
Founder submits survey
    ↓
1. Browser sends JSON to /api/submit_survey
    ↓
2. Flask receives submission
    ↓
3. SPLIT POINT - Data bifurcates:
    ↓
    ├─→ Path A (Tier 1 - Operational)
    │   • Extract selections (e.g., "woman", "asian")
    │   • Increment counters in aggregated_responses
    │   • Update: gender_woman += 1, race_asian += 1
    │   • Calculate primarily_diverse status
    │   • NO individual data stored
    │
    └─→ Path B (Tier 2 - Compliance)
        • Encrypt entire response as JSON blob
        • Store in individual_responses table
        • Link to company_id only (no founder ID)
        • Hash IP for audit trail
        • Cannot decrypt without encryption key
```

### Data Access Patterns

**Daily Operations** (Tier 1):
```
Admin Dashboard → aggregated_responses → View counts
    ↓
No way to see individual responses
No way to link count to specific founder
```

**DFPI Compliance** (Tier 2):
```
DFPI requests inspection → compliance_access_log entry
    ↓
Authorized person decrypts → individual_responses
    ↓
Provides to DFPI → Re-encrypt immediately after
```

## Security Layers

### Layer 1: Survey Token Anonymization
- Survey link contains company token, not founder token
- Multiple founders use same URL
- No way to know which founder submitted which response

### Layer 2: Data Separation at Collection
- Survey submission immediately splits data
- Never stored together after split point
- Two separate database tables with no joins

### Layer 3: Encryption
- Fernet symmetric encryption (AES-128)
- Encryption key stored separately from database
- Each response encrypted independently

### Layer 4: Access Logging
- All access to Tier 2 data must be logged
- Logs include: who, when, why, what was accessed
- 7-year retention for audit trail

## Component Details

### Flask Application (`app.py`)

**Key Functions:**

- `submit_survey()`: Handles survey submissions, implements data split
- `encrypt_response()`: Encrypts individual responses for Tier 2
- `decrypt_response()`: Decrypts for compliance (logged access only)
- `calculate_diverse_status()`: Determines if >50% identify as diverse

**Routes:**

- `/` - Admin dashboard home
- `/survey/<token>` - Founder survey form
- `/api/submit_survey` - Survey submission endpoint
- `/admin/companies` - List all portfolio companies
- `/admin/company/<id>` - View aggregated data for company
- `/admin/add_company` - Add new portfolio company
- `/admin/export_dfpi/<year>` - Export DFPI report CSV

### Database Schema (`schema.sql`)

**Tier 1 Tables:**
- `portfolio_companies` - Company metadata + survey tokens
- `aggregated_responses` - Demographic counts (operational)

**Tier 2 Tables:**
- `individual_responses` - Encrypted survey data (compliance)
- `compliance_access_log` - Audit trail for Tier 2 access

### Survey Form (`templates/survey.html`)

- Matches DFPI official survey questions
- Multiple selection for gender/race
- Single selection for LGBTQ+, disability, veteran, CA resident
- "Decline all" option
- JavaScript handles form submission
- Real-time validation

### Admin Dashboard

- **dashboard.html** - Home page with quick actions
- **companies.html** - List view with response rates
- **company_detail.html** - Detailed aggregated stats
- **add_company.html** - Add portfolio company form

## Compliance Architecture

### How Anonymization is Achieved

1. **No Founder Identifiers**: Survey tokens are company-specific, not founder-specific
2. **Immediate Aggregation**: Counts are incremented immediately, response not stored with counts
3. **Encrypted Storage**: Individual data encrypted and stored separately
4. **No Join Path**: Cannot join aggregated counts back to individuals
5. **Access Separation**: Operational users never see Tier 2 data

### What Can Be Seen

**By Admin Users (Tier 1):**
- Total founders per company
- Total responses received
- Count of each demographic selection
- Response rate percentages
- Primarily diverse status

**Cannot Be Seen:**
- Which founder selected what
- Any individual's specific responses
- Link between aggregate count and person

**By DFPI (Tier 2, if requested):**
- Individual encrypted responses
- Only after logged access approval
- Must go through compliance officer

### Data Retention

- **Aggregated Data**: Permanent (Tier 1)
- **Individual Responses**: 5 years minimum (Tier 2)
- **Access Logs**: 7 years (audit compliance)

## Deployment Considerations

### Scalability

- Current: SQLite (10-100 companies)
- Medium: PostgreSQL (100-1000 companies)
- Large: PostgreSQL + read replicas (1000+ companies)

### Performance

- Survey submissions: ~100ms (includes encryption)
- Dashboard loads: ~50ms (aggregated data only)
- DFPI export: ~500ms for 50 companies

### Security Hardening

1. Use production WSGI server (gunicorn)
2. Enable HTTPS/SSL
3. Add authentication layer
4. Implement rate limiting
5. Regular security audits

## Testing

Run comprehensive tests:
```bash
python test_system.py
```

Tests verify:
- Encryption/decryption
- Data separation
- Aggregation accuracy
- No data leakage between tiers
- Diverse status calculation

## Monitoring

Key metrics to track:
- Survey submission rate
- Response completion time
- Database query performance
- Encryption/decryption latency
- Access log entries (should be rare)

## Future Enhancements

Potential additions:
- Export to Excel with charts
- Email notifications for low response rates
- Multi-year trending analysis
- API for programmatic access
- Mobile-optimized survey form
