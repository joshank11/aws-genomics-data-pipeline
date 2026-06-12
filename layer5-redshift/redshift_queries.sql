-- ============================================================
-- Layer 5: Redshift Warehousing
-- NOTE: Redshift Serverless requires account opt-in
-- These queries are reference implementations
-- ============================================================

-- 1. Create external schema pointing to Glue Data Catalog
CREATE EXTERNAL SCHEMA genomics_lake
FROM DATA CATALOG
DATABASE 'clovertex_genomics'
IAM_ROLE 'arn:aws:iam::ACCOUNT_ID:role/clovertex-genomics-lambda-role';

-- 2. Query S3 Parquet via Redshift Spectrum (no data loading needed)
SELECT sample_id,
       COUNT(*)        AS total_reads,
       AVG(gc_content) AS avg_gc,
       AVG(read_length) AS avg_length
FROM genomics_lake.genomics
GROUP BY sample_id
ORDER BY sample_id;

-- 3. Create summary table in Redshift with optimized keys
CREATE TABLE genomics_summary (
    sample_id     VARCHAR(50),
    total_reads   INT,
    avg_gc        FLOAT,
    avg_length    FLOAT,
    gc_category   VARCHAR(10),
    run_date      DATE
)
DISTKEY(sample_id)   -- queries on sample_id hit same compute node
SORTKEY(run_date);   -- range queries on date skip irrelevant blocks

-- 4. Bulk load from S3 Parquet into Redshift
COPY genomics_summary
FROM 's3://clovertex-genomics-prod-shashank/curated/genomics/'
IAM_ROLE 'arn:aws:iam::ACCOUNT_ID:role/clovertex-genomics-lambda-role'
FORMAT AS PARQUET;

-- 5. Cross-layer join — Redshift table + S3 data lake in one query
SELECT r.sample_id,
       r.run_date,
       s.avg_gc,
       s.total_reads
FROM genomics_summary r
JOIN genomics_lake.genomics s ON r.sample_id = s.sample_id
WHERE s.gc_content > 50.0;
