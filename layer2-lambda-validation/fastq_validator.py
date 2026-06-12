import boto3
import json
import urllib.parse

s3 = boto3.client('s3', region_name='ap-south-2')

def validate_fastq(content):
    lines = [l for l in content.strip().split('\n') if l.strip()]
    if len(lines) % 4 != 0:
        return False, f"Line count {len(lines)} is not a multiple of 4"
    for i in range(0, len(lines), 4):
        if not lines[i].startswith('@'):
            return False, f"Read {i//4 + 1}: ID line must start with @"
        if not all(c in 'ATGCNatgcn' for c in lines[i+1]):
            return False, f"Read {i//4 + 1}: Invalid DNA characters"
        if not lines[i+2].startswith('+'):
            return False, f"Read {i//4 + 1}: Separator line must start with +"
        if len(lines[i+1]) != len(lines[i+3]):
            return False, f"Read {i//4 + 1}: Sequence and quality length mismatch"
    read_count = len(lines) // 4
    return True, f"Valid FASTQ: {read_count} reads"

def validate_filename(key):
    parts = key.split('/')
    if len(parts) != 4:
        return False, f"Expected 4 path parts, got {len(parts)}"
    if parts[0] != 'raw':
        return False, "File must be in raw/ prefix"
    if not key.endswith('.fastq') and not key.endswith('.fastq.gz'):
        return False, "File must end in .fastq or .fastq.gz"
    return True, "Filename convention valid"

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key    = urllib.parse.unquote_plus(record['s3']['object']['key'])
    size   = record['s3']['object']['size']

    print(f"New file detected: s3://{bucket}/{key} ({size} bytes)")

    # Check 1: Filename convention (cheap — no S3 read)
    fname_valid, fname_msg = validate_filename(key)
    if not fname_valid:
        print(f"FAIL - Filename: {fname_msg}")
        move_to_quarantine(bucket, key, fname_msg)
        raise Exception(f"FAIL - Filename: {fname_msg}")

    # Check 2: FASTQ format (read first 8KB only — safe for large files)
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read(8192).decode('utf-8')
    except UnicodeDecodeError:
        msg = "Binary or gzipped file - cannot decode as text"
        move_to_quarantine(bucket, key, msg)
        raise Exception(msg)
    except Exception as e:
        print(f"ERROR reading file: {str(e)}")
        raise

    fastq_valid, fastq_msg = validate_fastq(content)
    if not fastq_valid:
        print(f"FAIL - Format: {fastq_msg}")
        move_to_quarantine(bucket, key, fastq_msg)
        raise Exception(f"FAIL - Format: {fastq_msg}")

    tag_as_validated(bucket, key)
    print(f"PASS - {fastq_msg}")
    # NOTE: raise Exception on failure so Step Functions Catch block triggers
    # return statusCode 200 on success
    return {'statusCode': 200, 'result': 'PASS', 'message': fastq_msg}

def move_to_quarantine(bucket, key, reason):
    quarantine_key = key.replace('raw/', 'quarantine/', 1)
    s3.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': key},
        Key=quarantine_key
    )
    s3.delete_object(Bucket=bucket, Key=key)
    print(f"Moved to quarantine: {quarantine_key} | Reason: {reason}")

def tag_as_validated(bucket, key):
    s3.put_object_tagging(
        Bucket=bucket,
        Key=key,
        Tagging={'TagSet': [
            {'Key': 'validated',  'Value': 'true'},
            {'Key': 'validator',  'Value': 'fastq-lambda-v1'}
        ]}
    )
    print(f"Tagged as validated: {key}")
