-- Migration: Add contributed sensor support
-- Adds fields for user-contributed sensors and coordinates to readings

-- First, backup existing table data
-- SQLite doesn't support ALTER COLUMN, so we need to recreate community_sensors table

-- Step 1: Create new community_sensors table with updated schema
CREATE TABLE community_sensors_new (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    latitude FLOAT,  -- Now nullable
    longitude FLOAT,  -- Now nullable
    sensor_type VARCHAR(20) NOT NULL DEFAULT 'virtual',
    auth_token_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    source VARCHAR(20) NOT NULL DEFAULT 'seed',  -- NEW
    hardware_id VARCHAR(80),  -- NEW
    hardware_model VARCHAR(120),  -- NEW
    contributor_name VARCHAR(160),  -- NEW
    created_at TIMESTAMP NOT NULL,
    last_seen TIMESTAMP
);

-- Step 2: Copy data from old table to new table
INSERT INTO community_sensors_new (
    id, name, latitude, longitude, sensor_type, auth_token_hash, 
    status, source, hardware_id, hardware_model, contributor_name, 
    created_at, last_seen
)
SELECT 
    id, name, latitude, longitude, sensor_type, auth_token_hash,
    status, 'seed' as source, NULL as hardware_id, NULL as hardware_model, 
    NULL as contributor_name, created_at, last_seen
FROM community_sensors;

-- Step 3: Drop old table
DROP TABLE community_sensors;

-- Step 4: Rename new table
ALTER TABLE community_sensors_new RENAME TO community_sensors;

-- Step 5: Recreate index
CREATE INDEX ix_community_sensors_status ON community_sensors(status);

-- Step 6: Add coordinate columns to community_sensor_readings
ALTER TABLE community_sensor_readings ADD COLUMN latitude FLOAT;
ALTER TABLE community_sensor_readings ADD COLUMN longitude FLOAT;
