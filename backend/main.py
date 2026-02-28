"""
FastAPI backend for LLM-Powered Data Analyst.
Converts natural language queries to SQL and returns results with visualizations.
"""

import os
import json
import base64
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import plotly.express as px
import plotly.io as pio

# Import LLM provider abstraction
from llm_provider import get_llm_provider

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="LLM Data Analyst API",
    description="Natural language to SQL query system for NYC Taxi data (with local LLM support)",
    version="2.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "nyc_taxi")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Initialize database engine
engine = create_engine(DATABASE_URL)

# Initialize LLM provider (Ollama or OpenAI)
# This will auto-detect: Ollama first, then OpenAI fallback
llm_provider = None  # Initialize on first request

# Database schema for LLM context
TABLE_SCHEMA = """
Table: taxi_trips
Columns:
- id: SERIAL PRIMARY KEY
- vendor_id: INTEGER (1=Creative Mobile, 2=VeriFone)
- tpep_pickup_datetime: TIMESTAMP (when meter was engaged)
- tpep_dropoff_datetime: TIMESTAMP (when meter was disengaged)
- passenger_count: INTEGER (number of passengers)
- trip_distance: FLOAT (distance in miles)
- pickup_longitude: FLOAT
- pickup_latitude: FLOAT
- rate_code_id: INTEGER (1=Standard, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negotiated, 6=Group)
- store_and_fwd_flag: VARCHAR(1)
- dropoff_longitude: FLOAT
- dropoff_latitude: FLOAT
- payment_type: INTEGER (1=Credit card, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown, 6=Voided)
- fare_amount: FLOAT (time-and-distance fare in USD)
- extra: FLOAT (miscellaneous extras)
- mta_tax: FLOAT (MTA tax)
- tip_amount: FLOAT (tip amount, auto-populated for credit cards)
- tolls_amount: FLOAT (tolls paid)
- improvement_surcharge: FLOAT
- total_amount: FLOAT (total charged to passenger)

Common queries:
- Revenue analysis: Use total_amount, fare_amount
- Time analysis: Use tpep_pickup_datetime, tpep_dropoff_datetime
- Distance analysis: Use trip_distance
- Payment analysis: Use payment_type
"""


# Human-readable labels for categorical columns
CATEGORY_LABELS = {
    "payment_type": {
        1: "Credit Card", 2: "Cash", 3: "No Charge", 4: "Dispute", 5: "Unknown", 6: "Voided"
    },
    "vendor_id": {
        1: "Creative Mobile", 2: "VeriFone"
    },
    "rate_code_id": {
        1: "Standard", 2: "JFK", 3: "Newark", 4: "Nassau/Westchester", 5: "Negotiated", 6: "Group"
    },
    "store_and_fwd_flag": {
        "Y": "Store & Forward", "N": "Direct"
    },
}


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    generate_chart: bool = True


class QueryResponse(BaseModel):
    sql: str
    data: list
    columns: list
    row_count: int
    chart: Optional[str] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None


class SchemaResponse(BaseModel):
    schema: str
    table_name: str
    row_count: int


# Helper functions
def generate_sql(natural_language_query: str) -> str:
    """Convert natural language to SQL using LLM provider (Ollama or OpenAI)."""

    global llm_provider

    # Initialize provider on first use
    if llm_provider is None:
        try:
            # Try to get provider (auto-detects Ollama or OpenAI)
            provider_type = os.getenv("LLM_PROVIDER")  # Optional: "ollama" or "openai"
            llm_provider = get_llm_provider(provider_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    try:
        sql = llm_provider.generate_sql(natural_language_query, TABLE_SCHEMA)
        return sql

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SQL: {str(e)}")


def execute_sql(sql: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame."""
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL execution error: {str(e)}")


def generate_chart(df: pd.DataFrame, query: str) -> tuple[str, str]:
    """Generate appropriate chart based on data shape — no keyword matching."""

    if df.empty or len(df.columns) < 2:
        return None, None

    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    non_numeric_cols = [c for c in cols if c not in numeric_cols]
    datetime_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns.tolist()

    # Pick X: prefer datetime > non-numeric > first numeric that isn't the only column
    if datetime_cols:
        x_col = datetime_cols[0]
    elif non_numeric_cols:
        x_col = non_numeric_cols[0]
    else:
        x_col = cols[0]

    # Apply human-readable labels if X column has a known mapping
    if x_col in CATEGORY_LABELS:
        df[x_col] = df[x_col].map(CATEGORY_LABELS[x_col]).fillna(df[x_col].astype(str))
    elif x_col in numeric_cols and df[x_col].nunique() <= 20:
        # If X is a numeric category (low cardinality), convert to string for discrete axis
        df[x_col] = df[x_col].astype(str)

    # Pick Y: first numeric column that isn't x and isn't an id/index column
    y_candidates = [c for c in numeric_cols if c != x_col and not c.lower().endswith('id') and c.lower() != 'index']
    if not y_candidates:
        return None, None
    y_col = y_candidates[0]

    try:
        # Datetime x
        if x_col in datetime_cols or df[x_col].astype(str).str.match(r'\d{4}-\d{2}').any():
            time_series_names = ['month', 'day', 'week', 'year', 'date', 'hour', 'time', 'period']
            is_time_series = any(w in x_col.lower() for w in time_series_names)

            # Check if dates are in chronological order (trend) or ranked order (top-N)
            try:
                dates = pd.to_datetime(df[x_col])
                is_chronological = dates.is_monotonic_increasing
            except Exception:
                is_chronological = False

            if is_time_series and is_chronological:
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over time", markers=True,
                              color_discrete_sequence=["#60a5fa"])
                chart_type = "line"
            elif len(df) <= 15:
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}",
                             color=y_col, color_continuous_scale="Blues")
                chart_type = "bar"
            elif len(df) <= 50:
                fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} over time",
                                 color=y_col, color_continuous_scale="Viridis")
                chart_type = "scatter"
            else:
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over time",
                              color_discrete_sequence=["#34d399"])
                chart_type = "line"

        # Few categories (≤ 30 rows) → bar chart
        elif len(df) <= 30:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}",
                         color=x_col, color_discrete_sequence=px.colors.qualitative.Bold)
            chart_type = "bar"

        # Many rows → line chart
        else:
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}",
                          color_discrete_sequence=["#a78bfa"])
            chart_type = "line"

        # Update layout
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=40, b=40)
        )

        # Convert to JSON for frontend
        chart_json = fig.to_json()

        return chart_json, chart_type

    except Exception as e:
        print(f"Chart generation error: {e}")
        return None, None


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LLM Data Analyst API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Check API, database, and LLM health."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check LLM provider
    llm_status = "not_initialized"
    llm_type = "none"

    if llm_provider is not None:
        llm_type = llm_provider.__class__.__name__.replace("Provider", "").lower()
        llm_status = "ready"

    return {
        "status": "ok",
        "database": db_status,
        "llm_provider": llm_type,
        "llm_status": llm_status
    }


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Get database schema information."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM taxi_trips"))
            row_count = result.scalar()

        return SchemaResponse(
            schema=TABLE_SCHEMA,
            table_name="taxi_trips",
            row_count=row_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process natural language query:
    1. Convert to SQL using LLM
    2. Execute SQL
    3. Generate visualization
    """

    # Generate SQL from natural language
    sql = generate_sql(request.query)

    # Execute query
    df = execute_sql(sql)

    # Generate chart if requested
    chart_json = None
    chart_type = None
    if request.generate_chart and not df.empty:
        chart_json, chart_type = generate_chart(df, request.query)

    # Convert DataFrame to response format
    # Handle datetime serialization
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    # Use to_json then parse back to handle NaN/Inf safely
    data = json.loads(df.to_json(orient="records", default_handler=str))

    return QueryResponse(
        sql=sql,
        data=data,
        columns=df.columns.tolist(),
        row_count=len(df),
        chart=chart_json,
        chart_type=chart_type
    )


@app.post("/validate-sql")
async def validate_sql(sql: str):
    """Validate SQL query without executing."""
    try:
        with engine.connect() as conn:
            # Use EXPLAIN to validate without running
            conn.execute(text(f"EXPLAIN {sql}"))
        return {"valid": True, "message": "SQL is valid"}
    except Exception as e:
        return {"valid": False, "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))

    uvicorn.run(app, host=host, port=port, reload=True)
