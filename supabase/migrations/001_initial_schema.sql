-- SlipSense.AI Initial Schema
-- Run this in the Supabase SQL Editor to set up all tables and RLS policies.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum for finding tiers
CREATE TYPE finding_tier AS ENUM ('auto_verified', 'needs_review', 'flagged');

-- Enum for document status
CREATE TYPE document_status AS ENUM ('uploading', 'classifying', 'classified', 'needs_classification', 'extracting', 'extracted', 'error');

-- =====================
-- DOCUMENTS TABLE
-- =====================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    doc_type TEXT,  -- T4, T5, T2202, RRSP, unknown
    classification_confidence FLOAT,
    status document_status NOT NULL DEFAULT 'uploading',
    tax_year INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_session_id ON documents(session_id);

-- =====================
-- EXTRACTED DATA TABLE
-- =====================
CREATE TABLE extracted_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',
    field_confidences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_extracted_data_document_id ON extracted_data(document_id);

-- =====================
-- FINDINGS TABLE
-- =====================
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    tier finding_tier NOT NULL,
    confidence FLOAT NOT NULL,
    category TEXT NOT NULL,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    action_suggestion TEXT,
    why_it_matters TEXT,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    source TEXT NOT NULL DEFAULT 'rule_engine',  -- 'rule_engine' or 'llm'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_session_id ON findings(session_id);
CREATE INDEX idx_findings_user_id ON findings(user_id);

-- =====================
-- REPORTS TABLE
-- =====================
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    summary JSONB NOT NULL DEFAULT '{}',
    total_income FLOAT,
    total_tax_deducted FLOAT,
    document_count INTEGER NOT NULL DEFAULT 0,
    findings_auto_verified INTEGER NOT NULL DEFAULT 0,
    findings_needs_review INTEGER NOT NULL DEFAULT 0,
    findings_flagged INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reports_session_id ON reports(session_id);
CREATE INDEX idx_reports_user_id ON reports(user_id);

-- =====================
-- ROW LEVEL SECURITY
-- =====================

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Documents: users can only access their own
CREATE POLICY "Users can view own documents"
    ON documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own documents"
    ON documents FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own documents"
    ON documents FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own documents"
    ON documents FOR DELETE USING (auth.uid() = user_id);

-- Extracted data: users can only access their own
CREATE POLICY "Users can view own extracted data"
    ON extracted_data FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own extracted data"
    ON extracted_data FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own extracted data"
    ON extracted_data FOR DELETE USING (auth.uid() = user_id);

-- Findings: users can only access their own
CREATE POLICY "Users can view own findings"
    ON findings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own findings"
    ON findings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own findings"
    ON findings FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own findings"
    ON findings FOR DELETE USING (auth.uid() = user_id);

-- Reports: users can only access their own
CREATE POLICY "Users can view own reports"
    ON reports FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own reports"
    ON reports FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own reports"
    ON reports FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own reports"
    ON reports FOR DELETE USING (auth.uid() = user_id);

-- =====================
-- STORAGE BUCKET
-- =====================
-- Run this separately or via the Supabase Dashboard:
-- Create a 'tax-documents' bucket (public: false)
-- Storage RLS policies are configured via the Dashboard or:
INSERT INTO storage.buckets (id, name, public) VALUES ('tax-documents', 'tax-documents', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Users can upload to own folder"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'tax-documents'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can view own files"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'tax-documents'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can delete own files"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'tax-documents'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- =====================
-- UPDATED_AT TRIGGER
-- =====================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
