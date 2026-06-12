import boto3
import csv
import io
import json
import urllib.parse

s3 = boto3.client('s3', region_name='ap-south-2')

def parse_fastq(content):
    """Parse FASTQ content into list of read dicts"""
    reads = []
    lines = [l for l in content.strip().split('\n') if l.strip()]
    for i in range(0, len(lines), 4):
        read_id = lines[i][1:]  # strip leading @
        sequence = lines[i+1]
        quality = lines[i+3]
        reads.append({
            'read_id': read_id,
            'sequence': sequence,
            'quality_scores': quality,
            'read_length': len(sequence),
            'gc_content': round(
                (sequence.upper().count('G') + sequence.upper().count('C'))
                / len(sequence) * 100, 2
            )
        })
    return reads

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key    = urllib.parse.unquote_plus(record['s3']['object']['key'])

    # Extract sample_id from path: raw/genomics/sample_002/sample_002.fastq
    sample_id = key.split('/')[2]

    print(f"Converting: s3://{bucket}/{key} | sample: {sample_id}")

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return build_response(500, 'ERROR', str(e))

    reads = parse_fastq(content)
    if not reads:
        return build_response(400, 'FAIL', 'No reads parsed from file')

    output = io.StringIO()
    fieldnames = ['read_id', 'sequence', 'quality_scores', 'read_length', 'gc_content', 'sample_id']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for read in reads:
        read['sample_id'] = sample_id
        writer.writerow(read)

    csv_key = f"processed/genomics/{sample_id}/{sample_id}_reads.csv"
    s3.put_object(
        Bucket=bucket,
        Key=csv_key,
        Body=output.getvalue().encode('utf-8'),
        ContentType='text/csv'
    )

    print(f"✅ Converted {len(reads)} reads → s3://{bucket}/{csv_key}")
    return build_response(200, 'PASS', f"Converted {len(reads)} reads to CSV")

def build_response(status_code, result, message):
    return {
        'statusCode': status_code,
        'body': json.dumps({'result': result, 'message': message})
    }
