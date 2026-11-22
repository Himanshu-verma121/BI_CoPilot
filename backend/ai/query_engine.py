from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import json
import re
from config import settings


def get_schema_description(schema: dict, db_type: str) -> str:
    description = ""

    def quote(name):
        if db_type.lower() == "mysql":
            return "`" + str(name).replace("`", "``") + "`"
        return '"' + str(name).replace('"', '""') + '"'

    for table_key, table_info in schema.items():
        schema_name = table_info.get("schema")
        table_name = table_info.get("table_name", table_key)

        if schema_name:
            table_ref = f"{quote(schema_name)}.{quote(table_name)}"
        else:
            table_ref = quote(table_name)

        description += f"\nTable: {table_name}\n"
        description += f"Schema: {schema_name or 'Default'}\n"
        description += f"SQL Reference: {table_ref}\n"

        for col in table_info.get("columns", []):
            column_name = col["name"]
            description += (
            f"  - {column_name} ({col['type']}) "
            f"[SQL name: {quote(column_name)}]\n"
        )

        if table_info.get("primary_keys"):
            description += f"Primary Keys: {table_info['primary_keys']}\n"

        for fk in table_info.get("foreign_keys", []):
            columns = fk.get("column", fk.get("constrained_columns", []))
            ref_table = fk.get("references_table", fk.get("referred_table"))
            ref_schema = fk.get("references_schema")
            ref_columns = fk.get("references_columns", fk.get("referred_columns", []))

            if ref_table:
                ref = (
                    f"{quote(ref_schema)}.{quote(ref_table)}"
                    if ref_schema else quote(ref_table)
                )
                description += (
                    f"Foreign Key: {columns} references "
                    f"{ref} columns {ref_columns}\n"
                )

    return description


def extract_sql_from_response(response: str) -> str:
    """
    Extracting just the SQL query from LLM response.
    """
    
    # SQL between code blocks
    sql_pattern = r"```sql\s*(.*?)\s*```"
    match = re.search(sql_pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Without sql keyword
    code_pattern = r"```\s*(.*?)\s*```"
    match = re.search(code_pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code blocks — return cleaned response
    return response.strip()


def is_safe_sql(sql: str) -> bool:
    """
    Check if SQL is safe to execute.

    Only allow SELECT queries.
    NEVER allow:
    - DROP TABLE (deletes table)
    - DELETE (deletes rows)
    - UPDATE (modifies data)
    - INSERT (adds data)
    - TRUNCATE (empties table)

    """
    sql_upper       = sql.upper().strip()
    dangerous_words = ["DROP", "DELETE", "UPDATE", "INSERT",
                       "TRUNCATE", "ALTER", "CREATE", "REPLACE"]

    for word in dangerous_words:
        if word in sql_upper:
            return False

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False

    return True


def select_chart_type(df: pd.DataFrame, question: str) -> str:
    """
    Automatically select the best chart type based on:
    1. The data structure (columns, types)
    2. The question asked

    Rules:
    - Time/date column + numeric = LINE chart (trends over time)
    - Category + numeric + few rows = BAR chart (comparisons)
    - Two numeric columns = SCATTER chart (correlation)
    - One column with percentages = PIE chart (proportions)
    - Many rows = TABLE (too much data for chart)
    """
    question_lower = question.lower()
    columns        = df.columns.tolist()
    num_rows       = len(df)

    # Check for
    
    # time-based columns
    time_keywords = ["date", "month", "year", "week", "time", "day"]
    has_time = any(
        any(kw in col.lower() for kw in time_keywords)
        for col in columns
    )

    # Percentage questions
    proportion_keywords = ["percentage", "share", "proportion", "distribution", "%"]
    is_proportion = any(kw in question_lower for kw in proportion_keywords)

    # Trend questions
    trend_keywords = ["trend", "over time", "monthly", "weekly", "growth"]
    is_trend = any(kw in question_lower for kw in trend_keywords)

    # Decision logic
    if is_proportion and num_rows <= 10:
        return "pie"
    elif has_time or is_trend:
        return "line"
    elif num_rows <= 20:
        return "bar"
    elif num_rows > 100:
        return "table"    # too many rows for chart
    else:
        return "bar"      # default


def create_chart(df: pd.DataFrame, chart_type: str, question: str) -> dict:
    """
    Create Plotly chart from dataframe.

    """
    columns = df.columns.tolist()

    # Need at least 2 columns for most charts
    if len(columns) < 2:
        return None

    x_col = columns[0]   
    y_col = columns[1]   
    try:
        if chart_type == "bar":
            fig = px.bar(
                df, x=x_col, y=y_col,
                title=question[:60],
                color_discrete_sequence=["#667eea"]
            )
        elif chart_type == "line":
            fig = px.line(
                df, x=x_col, y=y_col,
                title=question[:60],
                markers=True,
                color_discrete_sequence=["#667eea"]
            )
        elif chart_type == "pie":
            fig = px.pie(
                df, names=x_col, values=y_col,
                title=question[:60]
            )
        elif chart_type == "scatter":
            fig = px.scatter(
                df, x=x_col, y=y_col,
                title=question[:60],
                color_discrete_sequence=["#667eea"]
            )
        else:
            return None

        fig.update_layout(
            paper_bgcolor = "rgba(0,0,0,0)",
            plot_bgcolor  = "rgba(0,0,0,0)",
            font          = dict(family="Arial"),
            margin        = dict(l=20, r=20, t=40, b=20)
        )

        return json.loads(fig.to_json())

    except Exception:
        return None


class QueryEngine:
    """
    Main AI Query Engine.

    English question → SQL → Results → Chart → Answer
    """

    # def __init__(self):
    #     # Initialize LLM
    #     self.llm = ChatOpenAI(
    #         api_key     = settings.OPENAI_API_KEY,
    #         model       = "gpt-4o-mini",
    #         temperature = 0     
    #     )
    #     # Initialize GROQ LLM
    def __init__(self):
        self.llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0
    )
        
    def build_sql_prompt(self, schema_desc: str, question: str, history: list,   db_type: str) -> str:
        """
        Build the prompt we send to GPT.
        """
        history_text = ""
        if history:
            history_text = "\nPrevious conversation:\n"
            for h in history[-3:]:    # last 3 messages only
                history_text += f"User: {h['question']}\n"
                history_text += f"SQL: {h['sql']}\n"

        prompt = f"""You are an expert SQL analyst for a Business Intelligence platform.
Your job is to convert natural language questions into accurate SQL queries.

SELECTED DATABASE TYPE: {db_type}

Generate SQL strictly compatible with this database type.
Do not use syntax or functions from another database engine.

DATABASE SCHEMA:
{schema_desc}

STRICT RULES:
1. ONLY write SELECT queries — NEVER write DROP, DELETE, UPDATE, INSERT
2. Use ONLY tables and columns present in the discovered schema.
3. Never invent table names, column names, or relationships.
4. Preserve exact table and column names, including capitalization.
5. Use the exact SQL Reference provided for each table.
6. Use only discovered foreign-key relationships when joining tables.
7. Always use table aliases for clarity.
8. Handle NULL values properly when required.
9. Use SQL syntax compatible with the selected database type.
10. Always add LIMIT 1000 if no limit is specified.
11. Return ONLY the SQL query inside a ```sql code block.

{history_text}

Current Question: {question}

SQL Query:"""
        return prompt

    def generate_sql(self, question: str, schema: dict, db_type: str, history: list = []) -> str:
        """
        Step 1: Convert English question to SQL using GPT.
        """
        schema_desc = get_schema_description(schema, db_type)
        prompt      = self.build_sql_prompt(schema_desc, question, history, db_type)

        response = self.llm.invoke(prompt)
        sql      = extract_sql_from_response(response.content)
        return sql

    def execute_sql(self, sql: str, connection_url: str) -> pd.DataFrame:
        """
        Step 2: Execute SQL on company database.
        """
        engine = create_engine(connection_url)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            df     = pd.DataFrame(
                result.fetchall(),
                columns=result.keys()
            )
        engine.dispose()
        return df

    def generate_answer(self, question: str, df: pd.DataFrame) -> str:
        """
        Step 3: Generate human readable answer.
        """
        # Dataframe to text for GPT
        data_preview = df.head(10).to_string()
        total_rows   = len(df)

        prompt = f"""You are a business analyst presenting data insights.
        
Question asked: {question}
Total rows returned: {total_rows}
Data (first 10 rows):
{data_preview}

Write a clear, concise business insight in 2-3 sentences.
Focus on key numbers and what they mean for the business.
Be direct and professional."""

        response = self.llm.invoke(prompt)
        return response.content

    def process_question(
        self,
        question       : str,
        connection_url : str,
        schema         : dict,
        db_type : str,
        history        : list = []
    ) -> dict:
        """
        Complete pipeline from question to answer.
        
        """
        result = {
            "question"  : question,
            "sql"       : None,
            "answer"    : None,
            "chart"     : None,
            "chart_type": None,
            "data"      : None,
            "row_count" : 0,
            "error"     : None
        }

        try:
            # 1: Generate SQL
            print(f"Generating SQL for: {question}")
            sql = self.generate_sql(question, schema, db_type, history)
            result["sql"] = sql
            print(f"Generated SQL: {sql}")

            # 2: Safety Check 
            if not is_safe_sql(sql):
                result["error"] = "I can only read data, not modify it."
                return result

            # 3: Execute SQL 
            print("Executing SQL...")
            df = self.execute_sql(sql, connection_url)
            result["row_count"] = len(df)
            result["data"]      = df.head(100).to_dict(orient="records")
            print(f"Got {len(df)} rows")

            # 4: Answer 
            print("Generating answer...")
            answer         = self.generate_answer(question, df)
            result["answer"] = answer

            # 5: Chart Type
            chart_type         = select_chart_type(df, question)
            result["chart_type"] = chart_type

            # 6: Chart 
            if len(df) > 0 and chart_type != "table":
                chart          = create_chart(df, chart_type, question)
                result["chart"] = chart

            return result

        except Exception as e:
            result["error"] = f"Error processing question: {str(e)}"
            print(f"Error: {str(e)}")
            return result