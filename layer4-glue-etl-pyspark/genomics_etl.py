from pyspark.sql import SparkSession
from pyspark.sql.functions import when, col
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

spark = SparkSession.builder.appName("GenomicsETL").getOrCreate()

# Explicit schema — never rely on inference for production ETL
schema = StructType([
    StructField("read_id",        StringType(),  True),
    StructField("sequence",       StringType(),  True),
    StructField("quality_scores", StringType(),  True),
    StructField("read_length",    IntegerType(), True),
    StructField("gc_content",     DoubleType(),  True),
    StructField("sample_id",      StringType(),  True)
])

# Read all CSV files from processed/
df = spark.read \
    .option("header", "true") \
    .schema(schema) \
    .csv("s3://clovertex-genomics-prod-shashank/processed/genomics/*/*.csv")

# Enforce correct data types
df = (
    df.withColumn("read_length", col("read_length").cast("int"))
      .withColumn("gc_content",  col("gc_content").cast("double"))
)

# GC content classification — standard genomics QC metric
df = df.withColumn(
    "gc_category",
    when(col("gc_content") < 40, "LOW")
    .when(col("gc_content") < 60, "MEDIUM")
    .otherwise("HIGH")
)

# Read length classification
df = df.withColumn(
    "quality_band",
    when(col("read_length") < 50, "SHORT")
    .otherwise("LONG")
)

# Write Parquet — columnar format, ~100x cheaper on Athena vs CSV
# partitionBy creates Hive-style folders: curated/genomics/sample_id=sample_003/
df.write \
    .mode("overwrite") \
    .partitionBy("sample_id") \
    .parquet("s3://clovertex-genomics-prod-shashank/curated/genomics/")

print("ETL Complete")
