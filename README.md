# LLM-based Data Analyst

A natural language to SQL query system powered by locally-hosted LLM (Ollama + CodeLlama-7B) for analyzing NYC Taxi trip data. Ask questions in plain English and get SQL queries, data tables, and interactive visualizations automatically.

## Features

- **Natural Language Queries**: Ask questions like "Count trips by day of week" and get accurate SQL
- **Local LLM**: Uses Ollama with CodeLlama-7B - no API costs, runs offline
- **Prompt Engineering**: Custom Modelfile with embedded database schema and few-shot examples
- **Auto-Visualization**: Generates interactive Plotly charts from query results
- **Full-Stack Application**: FastAPI backend + Next.js frontend
- **Real-Time Results**: Execute queries on 40,000+ NYC taxi trip records

## Demo

```
User Query: "Show average trip distance by payment type"

Generated SQL:
SELECT payment_type, AVG(trip_distance) as avg_distance
FROM taxi_trips
GROUP BY payment_type
ORDER BY payment_type;

Results:
payment_type | avg_distance
1 (Credit)   | 3.2 miles
2 (Cash)     | 2.8 miles
...

[Interactive Chart Displayed]
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│  Next.js     │────▶│  FastAPI    │
│   (3000)    │◀────│  Frontend    │◀────│  (8000)     │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                            ┌────────────────────┼──────────────────┐
                            │                    │                  │
                            ▼                    ▼                  ▼
                    ┌──────────────┐    ┌──────────────┐   ┌──────────────┐
                    │   Ollama     │    │  PostgreSQL  │   │   Plotly     │
                    │ (11434)      │    │   (5432)     │   │   Charts     │
                    │ CodeLlama 7B │    │  NYC Taxi    │   │              │
                    └──────────────┘    └──────────────┘   └──────────────┘
```

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Relational database
- **Ollama** - Local LLM inference server
- **Plotly** - Interactive visualization library

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Plotly.js** - React bindings for Plotly

### AI/ML
- **CodeLlama-7B** - Meta's code-specialized LLM
- **Prompt Engineering** - Custom system prompts with schema injection
- **Few-Shot Learning** - In-context examples for better SQL generation

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **Docker Desktop** (for PostgreSQL)
- **Ollama** - [Install from ollama.ai](https://ollama.ai/download)

## Quick Start

### 1. Clone and Setup

```bash
cd /path/to/sql
```

### 2. Start Ollama Service

```bash
# Start Ollama (in a new terminal)
ollama serve
```

### 3. Create Custom Model

```bash
# Create sql-analyst model with NYC Taxi schema
cd model
bash create_ollama_model.sh
```

This downloads CodeLlama-7B (~3.8GB) and creates a custom model with:
- Database schema embedded in system prompt
- Few-shot examples for common queries
- Optimized parameters for SQL generation

### 4. Start Database

```bash
# Start PostgreSQL in Docker
docker-compose up -d

# Wait for database to be ready
sleep 5
```

### 5. Load Sample Data

```bash
# Activate virtual environment
source venv/bin/activate

# Load 40,000 taxi trip records (~30 seconds)
python3 scripts/load_data.py --limit 10000
```

### 6. Start Backend

```bash
# In a new terminal
cd backend
source ../venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Expected output:
```
Using Ollama (local model)
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 7. Start Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

### 8. Open Application

Navigate to **http://localhost:3000** and start querying!

## Example Queries

Try these natural language queries:

**Simple Aggregations:**
- "Count total trips"
- "Show average trip distance"
- "What is the total revenue?"

**Group By Queries:**
- "Count trips by payment type"
- "Average fare by vendor"
- "Count trips by day of week"

**Time-Based Analysis:**
- "Show monthly revenue trend"
- "Top 10 days with highest revenue"
- "Average trip distance by hour of day"

**Complex Analytics:**
- "Show average tip percentage by payment type"
- "What is the distribution of passenger counts?"
- "Compare weekday vs weekend trip distances"

## Project Structure

```
sql/
├── backend/
│   ├── llm_provider.py      # Ollama integration
│   ├── main.py              # FastAPI endpoints
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Main chat interface
│   │   ├── layout.tsx       # App layout
│   │   └── globals.css      # Global styles
│   ├── package.json         # Node dependencies
│   └── tsconfig.json        # TypeScript config
│
├── model/
│   ├── Modelfile            # Ollama model definition
│   └── create_ollama_model.sh  # Model setup script
│
├── scripts/
│   └── load_data.py         # Data loading utility
│
├── docker/
│   └── init.sql             # Database schema
│
├── archive/                  # NYC Taxi CSV files
│   └── *.csv                # Trip data (7.4GB)
│
├── docker-compose.yml       # PostgreSQL setup
├── .env                     # Configuration
└── README.md               # This file
```

## Configuration

### Environment Variables (.env)

```bash
# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=nyc_taxi
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

```

### Frontend Environment (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## How It Works

### 1. Prompt Engineering Approach

Instead of fine-tuning, I use **prompt engineering** with a custom Modelfile:

```
FROM codellama:7b-instruct

SYSTEM """You are an expert SQL query generator for PostgreSQL.

Database Schema:
Table: taxi_trips
Columns:
- tpep_pickup_datetime: TIMESTAMP
- total_amount: FLOAT
- payment_type: INTEGER
...

Examples:
Q: Count trips by day of week
A: SELECT TO_CHAR(tpep_pickup_datetime, 'Day') as day_name,
   COUNT(*) as total_trips FROM taxi_trips...
"""
```

This gives CodeLlama all the context it needs without modifying model weights.

### 2. Request Flow

1. **User types query** → Frontend sends to backend
2. **Backend calls Ollama** → LLM generates SQL
3. **Execute SQL** → Run query on PostgreSQL
4. **Generate visualization** → Create Plotly chart
5. **Return results** → Display SQL, table, and chart

### 3. SQL Generation (backend/llm_provider.py)

```python
class OllamaProvider:
    def generate_sql(self, query: str) -> str:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "sql-analyst",
                "prompt": f"Convert to SQL: {query}",
                "timeout": 120  # 2 minutes for CPU inference
            }
        )
        sql = response.json()["response"]
        return self._clean_sql(sql)
```

## Performance

- **SQL Generation**: 30-90 seconds on CPU (2-5s with GPU)
- **Query Execution**: <100ms for most queries
- **Data Loading**: ~3 seconds per 10,000 rows
- **Model Size**: 3.8GB (CodeLlama-7B)
- **Memory Usage**: ~8GB RAM during inference

## Database Schema

```sql
CREATE TABLE taxi_trips (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count INTEGER,
    trip_distance FLOAT,
    payment_type INTEGER,
    fare_amount FLOAT,
    tip_amount FLOAT,
    total_amount FLOAT,
    ...
);
```

**Indexes:**
- `idx_pickup_datetime` on `tpep_pickup_datetime`
- `idx_payment_type` on `payment_type`
- `idx_vendor` on `vendor_id`

## API Endpoints

### POST /query
Generate SQL and execute query

**Request:**
```json
{
  "query": "Count trips by day of week",
  "generate_chart": true
}
```

**Response:**
```json
{
  "sql": "SELECT TO_CHAR(...)...",
  "data": [...],
  "columns": ["day_name", "total_trips"],
  "row_count": 7,
  "chart": "{...plotly json...}",
  "chart_type": "bar"
}
```

### GET /health
Check system status

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm_provider": "ollama",
  "model": "sql-analyst"
}
```

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Start Ollama service
ollama serve

# Verify model exists
ollama list | grep sql-analyst
```

### "Database connection failed"
```bash
# Check Docker container
docker ps | grep nyc_taxi_db

# Restart database
docker-compose restart
```

### "Timeout generating SQL"
- Normal on CPU (30-90 seconds for complex queries)
- Consider using GPU for faster inference
- Timeout is set to 120 seconds in `llm_provider.py`

### Frontend won't start
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

## Acknowledgments

- **Meta AI** - CodeLlama-7B model
- **Ollama** - Local LLM inference framework
- **NYC TLC** - NYC Taxi trip data
- **FastAPI** - Modern Python web framework
- **Vercel** - Next.js framework

