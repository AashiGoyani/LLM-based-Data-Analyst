#!/usr/bin/env python3
"""
Load NYC Taxi CSV data into PostgreSQL database.
Handles large files with chunked loading and progress tracking.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "nyc_taxi")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Column mapping for NYC Taxi data
COLUMN_MAPPING = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "tpep_pickup_datetime",
    "tpep_dropoff_datetime": "tpep_dropoff_datetime",
    "passenger_count": "passenger_count",
    "trip_distance": "trip_distance",
    "pickup_longitude": "pickup_longitude",
    "pickup_latitude": "pickup_latitude",
    "RatecodeID": "rate_code_id",
    "RateCodeID": "rate_code_id",
    "store_and_fwd_flag": "store_and_fwd_flag",
    "dropoff_longitude": "dropoff_longitude",
    "dropoff_latitude": "dropoff_latitude",
    "payment_type": "payment_type",
    "fare_amount": "fare_amount",
    "extra": "extra",
    "mta_tax": "mta_tax",
    "tip_amount": "tip_amount",
    "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge",
    "total_amount": "total_amount",
}

# Expected columns in target table
TARGET_COLUMNS = [
    "vendor_id",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "pickup_longitude",
    "pickup_latitude",
    "rate_code_id",
    "store_and_fwd_flag",
    "dropoff_longitude",
    "dropoff_latitude",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
]


def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(DATABASE_URL)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize DataFrame columns."""
    # Rename columns to match database schema
    df = df.rename(columns=COLUMN_MAPPING)

    # Select only target columns that exist
    available_cols = [col for col in TARGET_COLUMNS if col in df.columns]
    df = df[available_cols]

    # Convert datetime columns
    datetime_cols = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert numeric columns
    numeric_cols = [
        "vendor_id", "passenger_count", "rate_code_id", "payment_type",
        "trip_distance", "pickup_longitude", "pickup_latitude",
        "dropoff_longitude", "dropoff_latitude", "fare_amount",
        "extra", "mta_tax", "tip_amount", "tolls_amount",
        "improvement_surcharge", "total_amount"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_csv_to_db(csv_path: str, chunk_size: int = 100000, limit: int = None):
    """
    Load CSV file into PostgreSQL in chunks.

    Args:
        csv_path: Path to CSV file
        chunk_size: Number of rows per chunk
        limit: Maximum total rows to load (None for all)
    """
    engine = get_engine()
    csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return

    print(f"\nLoading: {csv_path.name}")
    print(f"Chunk size: {chunk_size:,} rows")

    total_rows = 0
    chunk_num = 0

    try:
        # Read CSV in chunks
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
            chunk_num += 1

            # Clean data
            chunk = clean_dataframe(chunk)

            # Check limit
            if limit and total_rows + len(chunk) > limit:
                chunk = chunk.head(limit - total_rows)

            # Load to database
            chunk.to_sql(
                "taxi_trips",
                engine,
                if_exists="append",
                index=False,
                method="multi"
            )

            total_rows += len(chunk)
            print(f"  Chunk {chunk_num}: Loaded {len(chunk):,} rows (Total: {total_rows:,})")

            # Check if we've reached the limit
            if limit and total_rows >= limit:
                print(f"  Reached limit of {limit:,} rows")
                break

        print(f"Completed: {total_rows:,} total rows loaded from {csv_path.name}")

    except Exception as e:
        print(f"Error loading {csv_path.name}: {e}")
        raise


def get_table_count(engine) -> int:
    """Get current row count in taxi_trips table."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM taxi_trips"))
        return result.scalar()


def main():
    """Main function to load all taxi data."""
    import argparse

    parser = argparse.ArgumentParser(description="Load NYC Taxi data into PostgreSQL")
    parser.add_argument(
        "--file",
        type=str,
        help="Specific CSV file to load (default: load all in archive/)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit rows per file (default: no limit)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100000,
        help="Rows per chunk (default: 100000)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before loading"
    )

    args = parser.parse_args()

    engine = get_engine()

    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  docker-compose up -d")
        sys.exit(1)

    # Clear existing data if requested
    if args.clear:
        print("\nClearing existing data...")
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE taxi_trips RESTART IDENTITY"))
            conn.commit()
        print("Table cleared.")

    # Get initial count
    initial_count = get_table_count(engine)
    print(f"\nCurrent rows in database: {initial_count:,}")

    # Determine files to load
    if args.file:
        csv_files = [Path(args.file)]
    else:
        # Load all CSV files from archive directory
        archive_dir = Path(__file__).parent.parent / "archive"
        csv_files = sorted(archive_dir.glob("*.csv"))

        if not csv_files:
            print(f"No CSV files found in {archive_dir}")
            sys.exit(1)

        print(f"\nFound {len(csv_files)} CSV file(s) to load:")
        for f in csv_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size_mb:.1f} MB)")

    # Load each file
    print("\n" + "=" * 50)
    for csv_file in csv_files:
        load_csv_to_db(
            csv_file,
            chunk_size=args.chunk_size,
            limit=args.limit
        )
        print("=" * 50)

    # Final count
    final_count = get_table_count(engine)
    loaded = final_count - initial_count
    print(f"\nLoading complete!")
    print(f"  Rows loaded: {loaded:,}")
    print(f"  Total rows in database: {final_count:,}")


if __name__ == "__main__":
    main()
