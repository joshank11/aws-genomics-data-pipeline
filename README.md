# AWS Genomics Data Pipeline
> Production-grade genomics data pipeline built on AWS — 6 layers from raw FASTQ to SQL-queryable analytics.

## Architecture
![Pipeline](docs/architecture.md)
FASTQ → S3 → Lambda Validation → Glue ETL → Parquet → Athena SQL

└── Step Functions Orchestration
## Stack
| Layer | Technology | What It Does |
|-------|-----------|--------------|
| 1 | S3 + Lifecycle | Medallion storage — raw/processed/curated |
| 2 | Lambda + CloudWatch | Event-driven FASTQ validation + quarantine |
| 3 | Glue Crawler + Athena | Auto-catalog schema + SQL on S3 |
| 4 | Glue ETL + PySpark | CSV → Parquet, 100x cheaper Athena queries |
| 5 | Redshift + Spectrum | Warehouse + data lake bridge |
| 6 | Step Functions | Full orchestration with retry + error handling |

## Region
`ap-south-2` (Hyderabad) — opt-in region, all services verified available.

## Key Design Decisions

### Why Parquet over CSV?
CSV scans entire rows — Athena charges per TB scanned. Parquet is columnar — `SELECT gc_content` reads only that column. ~100x cost reduction on large genomics datasets.

### Why Lambda chaining instead of two S3 triggers?
S3 does not allow two triggers with identical prefix + suffix — throws `InvalidArgument: Configuration is ambiguously defined`. Validator invokes converter asynchronously via `InvocationType='Event'`. Later replaced by Step Functions.

### Why raise Exception in Lambda instead of return 400?
Step Functions detects failures via exceptions, not HTTP status codes. Returning `{'statusCode': 400}` looks like success to Step Functions — it moves to the next state. `raise Exception(msg)` triggers the Catch block correctly.

### Why ResultPath in Step Functions?
Without ResultPath, each state's output replaces the entire input — next state loses the original S3 event and crashes with `KeyError: 'Records'`. ResultPath stores output at `$.validationResult` while preserving the original S3 event at `$`.

## Bugs Encountered & Fixed

### Bug 1 — CloudShell Unavailable in ap-south-2
**Symptom:** `Unable to create the environment` error in ap-south-2 CloudShell.  
**Cause:** CloudShell only launched in ap-south-2 on May 2025, had provisioning issues.  
**Fix:** Switched to ap-south-1 CloudShell temporarily. Scripts run fine since boto3 region is hardcoded.

### Bug 2 — S3 Lambda Trigger Ambiguous Configuration
**Symptom:** `InvalidArgument: Configuration is ambiguously defined` when adding second Lambda trigger.  
**Cause:** S3 does not allow two rules with identical prefix + suffix + event type.  
**Fix:** Lambda chaining — validator invokes converter via `lambda_client.invoke(InvocationType='Event')`. Later moved to Step Functions orchestration.

### Bug 3 — Step Functions KeyError Records
**Symptom:** `KeyError: 'Records'` in fastq_to_csv Lambda when invoked by Step Functions.  
**Cause:** Without `ResultPath`, each state's output replaces the input entirely. Converter received `{'statusCode': 200, 'result': 'PASS'}` instead of the S3 event.  
**Fix:** Added `"ResultPath": "$.validationResult"` to ValidateFASTQ state — preserves original S3 event at `$`.

### Bug 4 — Lambda returns 400 but Step Functions moves to next state
**Symptom:** Invalid FASTQ file not caught by Step Functions Catch block.  
**Cause:** `return {'statusCode': 400}` is treated as successful execution by Step Functions.  
**Fix:** Changed to `raise Exception(msg)` on failure — Step Functions Catch block now triggers correctly.

### Bug 5 — ConcurrentRunsExceededException on Glue ETL
**Symptom:** `Glue.ConcurrentRunsExceededException` on Step Functions RunGlueETL state.  
**Cause:** Step Functions Retry block fired two simultaneous Glue job attempts while first was still running.  
**Fix:** Removed Retry from RunGlueETL state. Increased `MaxConcurrentRuns` to 3 on the Glue job.

### Bug 6 — Glue crawler trust policy error
**Symptom:** `InvalidInputException: Service is unable to assume provided role` when creating Glue crawler.  
**Cause:** IAM role trust policy only allowed `lambda.amazonaws.com`. Glue needs its own trust entry.  
**Fix:** Updated trust policy to include `glue.amazonaws.com` and `states.amazonaws.com`.

## Sample Data
Located in `layer2-lambda-validation/test-data/`:

| File | GC Content | gc_category | Description |
|------|-----------|-------------|-------------|
| `sample_003.fastq` | 50.0% | MEDIUM | Normal human genome range |
| `sample_004.fastq` | 65.0% | HIGH | High GC organism (e.g. M. tuberculosis) |
| `sample_005.fastq` | 35.0% | LOW | Low GC organism (e.g. P. falciparum) |
| `sample_006.fastq` | 55.0% | MEDIUM | Slightly high normal range |
| `sample_valid.fastq` | 50.0% | MEDIUM | Generic valid FASTQ — passes all checks |
| `sample_invalid.fastq` | — | — | Sequence/quality length mismatch — triggers quarantine |

## Results
```sql
SELECT sample_id, COUNT(*) as reads, AVG(gc_content) as avg_gc
FROM genomics
GROUP BY sample_id ORDER BY sample_id;

-- sample_003 | 3 reads | 50.0% GC  | MEDIUM  (normal)
-- sample_004 | 3 reads | 65.0% GC  | HIGH    (high GC organism)
-- sample_005 | 3 reads | 35.0% GC  | LOW     (low GC organism)
-- sample_006 | 3 reads | 55.0% GC  | MEDIUM  (Step Functions orchestrated run)
```





## Setup
See each layer's folder for deployment commands.  
Replace `ACCOUNT_ID` in ARNs with your AWS account ID.
