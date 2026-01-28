-- ============================================================================
-- Dataverse 5.x to 6.x Migration: Missing JPA Tables
-- ============================================================================
-- These tables are normally created by JPA's create-tables mode when Dataverse
-- starts for the first time with a given version. However, if the database
-- schema was never properly initialized (e.g., running 5.14 WAR on 5.13 schema),
-- these tables will be missing and Flyway migrations will fail.
--
-- Run this SQL AFTER restoring production database dump but BEFORE starting
-- Payara/Dataverse 6.x.
-- ============================================================================

-- 1. storageuse (introduced in 5.14 for collection quotas)
-- Required by: V6.0.0.5__8549-collection-quotas.sql
CREATE TABLE IF NOT EXISTS storageuse (
    id SERIAL PRIMARY KEY,
    dvobjectcontainer_id BIGINT NOT NULL UNIQUE REFERENCES dvobject(id),
    sizeinbytes BIGINT
);
CREATE INDEX IF NOT EXISTS idx_storageuse_dvobjectcontainer ON storageuse(dvobjectcontainer_id);

-- 2. datasettype (introduced in 6.3 for dataset type support)
-- Required by: V6.3.0.3.sql
CREATE TABLE IF NOT EXISTS datasettype (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- 3. makedatacountprocessstate (for Make Data Count processing)
-- Required by: V6.5.0.10.sql
CREATE TABLE IF NOT EXISTS makedatacountprocessstate (
    id SERIAL PRIMARY KEY,
    yearmonth VARCHAR(255) NOT NULL,
    state INTEGER NOT NULL,
    statechangetimestamp TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_makedatacountprocessstate_yearmonth ON makedatacountprocessstate(yearmonth);

-- 4. dataversefeatureditem (for featured items on dataverse pages)
-- Required by: V6.6.0.2.sql
CREATE TABLE IF NOT EXISTS dataversefeatureditem (
    id SERIAL PRIMARY KEY,
    dataverse_id BIGINT NOT NULL REFERENCES dvobject(id),
    dvobject_id BIGINT REFERENCES dvobject(id),
    content TEXT,
    type VARCHAR(255) NOT NULL DEFAULT 'custom',
    imagefilename VARCHAR(255),
    displayorder INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_dataversefeatureditem_displayorder ON dataversefeatureditem(displayorder);

-- 5. storagequota (for storage quota limits on collections)
-- Required for search API in 6.x
CREATE TABLE IF NOT EXISTS storagequota (
    id SERIAL PRIMARY KEY,
    allocation BIGINT,
    definitionpoint_id BIGINT UNIQUE REFERENCES dvobject(id)
);

-- 6. retention (for data retention policies in 6.x)
-- Required for dataset API in 6.x
CREATE TABLE IF NOT EXISTS retention (
    id SERIAL PRIMARY KEY,
    datasetversion_id BIGINT REFERENCES datasetversion(id),
    dateunavailable TIMESTAMP,
    reason TEXT
);

-- ============================================================================
-- Verification: Check that all tables were created
-- ============================================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- AND table_name IN ('storageuse', 'datasettype', 'makedatacountprocessstate', 'dataversefeatureditem', 'storagequota', 'retention');
