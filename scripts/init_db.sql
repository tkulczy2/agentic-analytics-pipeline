-- Healthcare Analytics Pipeline Database Schema
-- PostgreSQL 15+

-- Members/Attribution table
CREATE TABLE IF NOT EXISTS members (
    member_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    attribution_start_date DATE NOT NULL,
    attribution_end_date DATE,
    primary_pcp_id VARCHAR(20),
    pcp_name VARCHAR(200),
    hcc_risk_score DECIMAL(6,4) NOT NULL DEFAULT 1.0,
    risk_category VARCHAR(10) CHECK (risk_category IN ('Low', 'Medium', 'High')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medical Claims table
CREATE TABLE IF NOT EXISTS medical_claims (
    claim_id VARCHAR(30) PRIMARY KEY,
    member_id VARCHAR(20) NOT NULL REFERENCES members(member_id),
    service_date DATE NOT NULL,
    paid_date DATE,
    paid_amount DECIMAL(12,2) NOT NULL,
    allowed_amount DECIMAL(12,2),
    place_of_service VARCHAR(2),
    provider_specialty VARCHAR(100),
    primary_diagnosis VARCHAR(10),
    claim_status VARCHAR(20) DEFAULT 'PAID',
    service_category VARCHAR(50),
    er_visit BOOLEAN DEFAULT FALSE,
    inpatient_admit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pharmacy Claims table
CREATE TABLE IF NOT EXISTS pharmacy_claims (
    claim_id VARCHAR(30) PRIMARY KEY,
    member_id VARCHAR(20) NOT NULL REFERENCES members(member_id),
    fill_date DATE NOT NULL,
    paid_amount DECIMAL(12,2) NOT NULL,
    drug_name VARCHAR(200) NOT NULL,
    generic_indicator BOOLEAN DEFAULT FALSE,
    days_supply INTEGER,
    therapeutic_class VARCHAR(100),
    condition_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality Measures table
CREATE TABLE IF NOT EXISTS quality_measures (
    measure_id VARCHAR(20) PRIMARY KEY,
    measure_name VARCHAR(200) NOT NULL,
    measure_category VARCHAR(50) NOT NULL,
    numerator INTEGER NOT NULL DEFAULT 0,
    denominator INTEGER NOT NULL DEFAULT 0,
    exclusions INTEGER DEFAULT 0,
    performance_rate DECIMAL(5,2),
    national_benchmark DECIMAL(5,2),
    measure_weight DECIMAL(3,2) DEFAULT 1.0,
    performance_year INTEGER NOT NULL,
    performance_month INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workflow tracking table
CREATE TABLE IF NOT EXISTS workflow_runs (
    workflow_id VARCHAR(50) PRIMARY KEY,
    contract_id VARCHAR(50) NOT NULL,
    performance_year INTEGER NOT NULL,
    performance_month INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    result_summary JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_members_risk ON members(risk_category);
CREATE INDEX IF NOT EXISTS idx_members_pcp ON members(primary_pcp_id);
CREATE INDEX IF NOT EXISTS idx_medical_claims_member ON medical_claims(member_id);
CREATE INDEX IF NOT EXISTS idx_medical_claims_service_date ON medical_claims(service_date);
CREATE INDEX IF NOT EXISTS idx_medical_claims_er ON medical_claims(er_visit) WHERE er_visit = TRUE;
CREATE INDEX IF NOT EXISTS idx_medical_claims_inpatient ON medical_claims(inpatient_admit) WHERE inpatient_admit = TRUE;
CREATE INDEX IF NOT EXISTS idx_pharmacy_claims_member ON pharmacy_claims(member_id);
CREATE INDEX IF NOT EXISTS idx_pharmacy_claims_fill_date ON pharmacy_claims(fill_date);
CREATE INDEX IF NOT EXISTS idx_quality_measures_category ON quality_measures(measure_category);
CREATE INDEX IF NOT EXISTS idx_quality_measures_year_month ON quality_measures(performance_year, performance_month);

-- Function to update timestamp on row update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE OR REPLACE TRIGGER update_members_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_medical_claims_updated_at
    BEFORE UPDATE ON medical_claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_pharmacy_claims_updated_at
    BEFORE UPDATE ON pharmacy_claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_quality_measures_updated_at
    BEFORE UPDATE ON quality_measures
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
