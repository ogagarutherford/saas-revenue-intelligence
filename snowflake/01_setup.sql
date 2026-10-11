-- =====================================================================
-- Lumora SaaS Revenue Intelligence — Snowflake environment setup
-- Run in a Snowsight worksheet. Re-runnable (IF NOT EXISTS everywhere).
-- =====================================================================

-- 1) Protect your trial credits (requires ACCOUNTADMIN)
USE ROLE ACCOUNTADMIN;
CREATE RESOURCE MONITOR IF NOT EXISTS LUMORA_MONITOR
  WITH CREDIT_QUOTA = 20
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND;

-- 2) Compute: smallest warehouse, suspends after 60s idle
USE ROLE SYSADMIN;
CREATE WAREHOUSE IF NOT EXISTS LUMORA_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

USE ROLE ACCOUNTADMIN;
ALTER WAREHOUSE LUMORA_WH SET RESOURCE_MONITOR = LUMORA_MONITOR;
USE ROLE SYSADMIN;

-- 3) Storage: one database, one schema per layer
CREATE DATABASE IF NOT EXISTS LUMORA;
CREATE SCHEMA IF NOT EXISTS LUMORA.RAW;           -- as-landed CSVs (strings), never edited
CREATE SCHEMA IF NOT EXISTS LUMORA.STAGING;       -- dbt: typed, renamed, 1:1 with sources
CREATE SCHEMA IF NOT EXISTS LUMORA.INTERMEDIATE;  -- dbt: business logic (MRR movements etc.)
CREATE SCHEMA IF NOT EXISTS LUMORA.MARTS;         -- dbt: star schema facts + dims for BI

-- 4) Sanity check after loading (run once load_to_snowflake.py has finished)
-- SELECT table_name, row_count
-- FROM LUMORA.INFORMATION_SCHEMA.TABLES
-- WHERE table_schema = 'RAW' ORDER BY table_name;
