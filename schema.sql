-- TIER 1: AGGREGATED DATA (Operational - what you actually use)
-- No PII, no way to trace back to individuals

CREATE TABLE portfolio_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    investment_year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    survey_link_token TEXT UNIQUE NOT NULL
);

CREATE TABLE aggregated_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    
    -- Response tracking
    total_founders INTEGER NOT NULL DEFAULT 0,
    total_responses INTEGER NOT NULL DEFAULT 0,
    total_declined_all INTEGER NOT NULL DEFAULT 0,
    
    -- Gender counts
    gender_woman INTEGER NOT NULL DEFAULT 0,
    gender_man INTEGER NOT NULL DEFAULT 0,
    gender_nonbinary INTEGER NOT NULL DEFAULT 0,
    gender_transgender INTEGER NOT NULL DEFAULT 0,
    gender_other INTEGER NOT NULL DEFAULT 0,
    gender_declined INTEGER NOT NULL DEFAULT 0,
    
    -- Race/Ethnicity counts
    race_black INTEGER NOT NULL DEFAULT 0,
    race_asian INTEGER NOT NULL DEFAULT 0,
    race_hispanic INTEGER NOT NULL DEFAULT 0,
    race_native_american INTEGER NOT NULL DEFAULT 0,
    race_pacific_islander INTEGER NOT NULL DEFAULT 0,
    race_white INTEGER NOT NULL DEFAULT 0,
    race_other INTEGER NOT NULL DEFAULT 0,
    race_declined INTEGER NOT NULL DEFAULT 0,
    
    -- LGBTQ+ counts
    lgbtq_yes INTEGER NOT NULL DEFAULT 0,
    lgbtq_no INTEGER NOT NULL DEFAULT 0,
    lgbtq_declined INTEGER NOT NULL DEFAULT 0,
    
    -- Disability counts
    disability_yes INTEGER NOT NULL DEFAULT 0,
    disability_no INTEGER NOT NULL DEFAULT 0,
    disability_declined INTEGER NOT NULL DEFAULT 0,
    
    -- Veteran counts
    veteran_yes INTEGER NOT NULL DEFAULT 0,
    veteran_disabled INTEGER NOT NULL DEFAULT 0,
    veteran_no INTEGER NOT NULL DEFAULT 0,
    veteran_declined INTEGER NOT NULL DEFAULT 0,
    
    -- California residency counts
    ca_resident_yes INTEGER NOT NULL DEFAULT 0,
    ca_resident_no INTEGER NOT NULL DEFAULT 0,
    ca_resident_declined INTEGER NOT NULL DEFAULT 0,
    
    -- Calculated flags
    is_primarily_diverse BOOLEAN,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES portfolio_companies(id)
);

-- TIER 2: INDIVIDUAL RESPONSES (Cold storage - compliance only)
-- Encrypted, access-logged, separate permissions

CREATE TABLE individual_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    response_data_encrypted BLOB NOT NULL,  -- Encrypted JSON of survey responses
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_hash TEXT,  -- Hashed IP for audit trail
    FOREIGN KEY (company_id) REFERENCES portfolio_companies(id)
);

-- Access log for compliance
CREATE TABLE compliance_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accessed_by TEXT NOT NULL,
    access_reason TEXT NOT NULL,
    company_id INTEGER,
    response_id INTEGER,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_company_year ON portfolio_companies(investment_year);
CREATE INDEX idx_aggregated_company ON aggregated_responses(company_id);
CREATE INDEX idx_individual_company ON individual_responses(company_id);
CREATE INDEX idx_access_log_time ON compliance_access_log(accessed_at);
