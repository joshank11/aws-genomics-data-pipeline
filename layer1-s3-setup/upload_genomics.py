import boto3
import os

# Best practice: use environment variable instead of hardcoded bucket name
# export BUCKET_NAME=clovertex-genomics-prod-shashank
BUCKET = os.environ.get('BUCKET_NAME', 'clovertex-genomics-prod-shashank')
REGION = 'ap-south-2'

s3 = boto3.client('s3', region_name=REGION)

SAMPLE_ID = 'sample_001'

def upload_file(local_path, s3_key):
    s3.upload_file(local_path, BUCKET, s3_key)
    print(f"✅ Uploaded: s3://{BUCKET}/{s3_key}")

upload_file(
    'sample_001.fastq',
    f'raw/genomics/{SAMPLE_ID}/sample_001.fastq'
)

print("\n📁 Verifying upload...")
response = s3.list_objects_v2(Bucket=BUCKET, Prefix=f'raw/genomics/{SAMPLE_ID}/')
for obj in response.get('Contents', []):
    print(f"   {obj['Key']}  ({obj['Size']} bytes)")
