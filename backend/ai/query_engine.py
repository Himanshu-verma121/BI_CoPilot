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
    """Choose a chart from an explicit request first, then the result structure."""
    q = question.lower()
    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    rows = len(df)

    # Respect an explicitly requested visualization before using heuristics.
    requested = [
        (("donut", "doughnut"), "donut"),
        (("pie chart", "pie graph"), "pie"),
        (("treemap", "tree map"), "treemap"),
        (("sunburst",), "sunburst"),
        (("histogram",), "histogram"),
        (("box plot", "boxplot"), "box"),
        (("violin plot", "violin"), "violin"),
        (("heatmap", "heat map", "correlation matrix"), "heatmap"),
        (("funnel",), "funnel"),
        (("waterfall",), "waterfall"),
        (("radar", "spider chart"), "radar"),
        (("bubble chart", "bubble plot"), "bubble"),
        (("scatter",), "scatter"),
        (("area chart", "area graph", "stacked area"), "area"),
        (("stacked bar", "stacked column"), "stacked_bar"),
        (("grouped bar", "clustered bar", "grouped column"), "grouped_bar"),
        (("bar chart", "bar graph", "column chart"), "bar"),
        (("line chart", "line graph"), "line"),
    ]
    for phrases, chart in requested:
        if any(phrase in q for phrase in phrases):
            return chart

    time_words = ("date", "month", "year", "week", "time", "day")
    has_time = any(any(word in str(c).lower() for word in time_words) for c in cols)
    if any(word in q for word in ("trend", "over time", "monthly", "weekly", "growth")) or has_time:
        return "line"
    if any(word in q for word in ("percentage", "proportion", "share", "distribution")) and rows <= 10:
        return "pie"
    if len(numeric_cols) >= 2:
        return "scatter"
    if rows > 100:
        return "table"
    return "bar"


def create_chart(df: pd.DataFrame, chart_type: str, question: str) -> dict:
    """Build a Plotly figure from query results without assuming fixed column names."""
    if df.empty or len(df.columns) < 2:
        return None

    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    x_col = cols[0]
    y_col = numeric_cols[0] if numeric_cols else cols[1]
    color_col = cols[2] if len(cols) > 2 else None
    title = question[:80]
    palette = ["#667eea", "#22c55e", "#f59e0b", "#ec4899", "#06b6d4"]

    try:
        if chart_type in ("pie", "donut"):
            fig = px.pie(df, names=x_col, values=y_col, title=title,
                         hole=0.48 if chart_type == "donut" else 0)
        elif chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette)
        elif chart_type in ("grouped_bar", "stacked_bar"):
            if not color_col:
                return px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette).to_dict()
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title,
                         barmode="group" if chart_type == "grouped_bar" else "stack")
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, markers=True)
        elif chart_type == "area":
            fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type in ("scatter", "bubble"):
            size_col = numeric_cols[1] if chart_type == "bubble" and len(numeric_cols) > 1 else None
            fig = px.scatter(df, x=x_col, y=y_col, size=size_col, color=color_col,
                             title=title, size_max=55)
        elif chart_type == "histogram":
            target = numeric_cols[0] if numeric_cols else y_col
            fig = px.histogram(df, x=target, title=title, color=color_col)
        elif chart_type in ("box", "violin"):
            target = numeric_cols[0] if numeric_cols else y_col
            fig = (px.box(df, x=x_col, y=target, color=color_col, title=title)
                   if x_col != target else px.box(df, y=target, title=title))
            if chart_type == "violin":
                fig = (px.violin(df, x=x_col, y=target, color=color_col, box=True, title=title)
                       if x_col != target else px.violin(df, y=target, box=True, title=title))
        elif chart_type == "heatmap":
            if len(cols) >= 3:
                fig = px.density_heatmap(df, x=cols[0], y=cols[1], z=y_col,
                                         title=title, color_continuous_scale="Viridis")
            else:
                matrix = df[numeric_cols].corr() if len(numeric_cols) >= 2 else df.select_dtypes(include="number")
                if matrix.empty:
                    return None
                fig = px.imshow(matrix, text_auto=True, aspect="auto", title=title,
                                color_continuous_scale="Viridis")
        elif chart_type == "treemap":
            path_cols = [c for c in cols if c != y_col][:2]
            fig = px.treemap(df, path=path_cols, values=y_col, title=title)
        elif chart_type == "sunburst":
            path_cols = [c for c in cols if c != y_col][:3]
            fig = px.sunburst(df, path=path_cols, values=y_col, title=title)
        elif chart_type == "funnel":
            fig = px.funnel(df, x=y_col, y=x_col, title=title)
        elif chart_type == "waterfall":
            import plotly.graph_objects as go
            fig = go.Figure(go.Waterfall(x=df[x_col].astype(str), y=df[y_col], name=y_col))
            fig.update_layout(title=title)
        elif chart_type == "radar":
            if len(numeric_cols) < 3:
                return None
            import plotly.graph_objects as go
            categories = numeric_cols
            values = df[categories].iloc[0].tolist()
            fig = go.Figure(go.Scatterpolar(r=values + values[:1],
                                            theta=categories + categories[:1],
                                            fill="toself", name=str(df.iloc[0][x_col])))
            fig.update_layout(title=title, polar=dict(radialaxis=dict(visible=True)))
        else:
            return None

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Arial"),
            margin=dict(l=30, r=20, t=50, b=35)
        )
        return json.loads(fig.to_json())
    except Exception as e:
        print(f"Chart generation failed ({chart_type}): {e}")
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