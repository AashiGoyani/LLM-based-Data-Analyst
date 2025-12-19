"""
LLM Provider abstraction for text-to-SQL generation.
Supports multiple backends: Ollama (local), OpenAI, or custom models.
"""

import os
import requests
from typing import Optional
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_sql(self, query: str, schema: str) -> str:
        """Generate SQL from natural language query."""
        pass


class OllamaProvider(LLMProvider):
    """Local Ollama model provider."""

    def __init__(self, model_name: str = "sql-analyst", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"

    def generate_sql(self, query: str, schema: str) -> str:
        """Generate SQL using local Ollama model."""
        try:
            # Ollama already has system prompt in Modelfile
            # Just send the user query
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": query,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                    }
                },
                timeout=120
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

            result = response.json()
            sql = result.get("response", "").strip()

            # Clean up response
            sql = self._clean_sql(sql)

            return sql

        except requests.exceptions.ConnectionError:
            raise Exception(
                "Cannot connect to Ollama. Make sure it's running:\n"
                "  1. Install: curl -fsSL https://ollama.ai/install.sh | sh\n"
                "  2. Start: ollama serve\n"
                "  3. Create model: bash model/create_ollama_model.sh"
            )
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")

    def _clean_sql(self, sql: str) -> str:
        """Clean SQL output."""
        # Remove markdown code blocks
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0]
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0]

        # Remove common prefixes
        prefixes = [
            "SQL Query:", "Query:", "SQL:", "Answer:", "A:",
            "Here is the SQL query:", "The SQL query is:"
        ]
        for prefix in prefixes:
            if sql.strip().startswith(prefix):
                sql = sql.replace(prefix, "", 1)

        return sql.strip()

    def is_available(self) -> bool:
        """Check if Ollama is running and model exists."""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            # Check if our model exists
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]

            return self.model_name in model_names

        except:
            return False


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (fallback option)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        from openai import OpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise Exception("OpenAI API key not configured")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def generate_sql(self, query: str, schema: str) -> str:
        """Generate SQL using OpenAI API."""

        system_prompt = f"""You are an expert SQL query generator for PostgreSQL.
Convert natural language requests into valid SQL queries.

{schema}

Rules:
1. Return ONLY the SQL query, no explanations
2. Always use proper PostgreSQL syntax
3. Limit results to 1000 rows unless specifically asked for more
4. Use appropriate aggregations for summary queries
5. For time-based trends, extract month/year from timestamps
6. Always include ORDER BY for meaningful sorting
7. Use aliases for calculated columns
8. For revenue, use total_amount column
9. Handle NULL values appropriately"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=500
            )

            sql = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if sql.startswith("```"):
                sql = sql.split("```")[1]
                if sql.startswith("sql"):
                    sql = sql[3:]
            sql = sql.strip()

            return sql

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


def get_llm_provider(provider_type: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get appropriate LLM provider.

    Priority:
    1. Use provider_type if specified
    2. Check if Ollama is available (preferred)
    3. Fall back to OpenAI if API key is set
    4. Raise error if nothing is available
    """

    # If provider explicitly specified
    if provider_type:
        if provider_type.lower() == "ollama":
            return OllamaProvider()
        elif provider_type.lower() == "openai":
            return OpenAIProvider()

    # Auto-detect: Try Ollama first (local, no cost)
    ollama = OllamaProvider()
    if ollama.is_available():
        print("Using Ollama (local model)")
        return ollama

    # Fall back to OpenAI
    try:
        openai = OpenAIProvider()
        print("Using OpenAI API")
        return openai
    except:
        pass

    # Nothing available
    raise Exception(
        "No LLM provider available.\n\n"
        "Option 1 (Recommended): Use local Ollama model\n"
        "  1. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh\n"
        "  2. Start service: ollama serve\n"
        "  3. Create model: bash model/create_ollama_model.sh\n\n"
        "Option 2: Use OpenAI API\n"
        "  1. Get API key from https://platform.openai.com\n"
        "  2. Add to .env: OPENAI_API_KEY=sk-...\n"
    )
