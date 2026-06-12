# Pipeline Architecture

## Medallion Architecture (S3)
raw/        → Bronze: files exactly as received from sequencer

processed/  → Silver: validated, converted to CSV

curated/    → Gold:   Parquet, partitioned, query-optimized

quarantine/ → Failed validation — moved here with reason tag
## Data Flow
FASTQ uploaded to S3 raw/

│

▼ S3 Event Notification

Step Functions State Machine

│

├── ValidateFASTQ (Lambda)

│       FAIL → quarantine/ + Exception raised

│       PASS → tagged validated=true

│

├── ConvertToCSV (Lambda)

│       FASTQ → CSV with GC content computed

│       written to processed/genomics/<sample_id>/

│

├── RunGlueETL (Glue PySpark)

│       CSV → Parquet with Snappy compression

│       adds gc_category + quality_band columns

│       partitioned by sample_id → curated/

│

├── UpdateCatalog (Glue Crawler)

│       updates Glue Data Catalog schema

│

└── PipelineSucceeded ✅
## AWS Services Used
| Layer | Service | Purpose |
|-------|---------|---------|
| 1 | S3 + KMS | Storage, encryption, lifecycle tiering |
| 2 | Lambda + CloudWatch | Event-driven validation |
| 3 | Glue Crawler + Athena | Schema discovery + SQL queries |
| 4 | Glue ETL + PySpark | CSV → Parquet transformation |
| 5 | Redshift | Warehousing for BI dashboards |
| 6 | Step Functions | Full pipeline orchestration |
