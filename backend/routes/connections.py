from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, inspect
from pydantic import BaseModel
from typing import Optional
import json
from database.db import get_db
from models.models import DBConnection
from utils.auth import verify_token

router = APIRouter(prefix="/connections", tags=["DB Connections"])


class ConnectionRequest(BaseModel):
    name    : str
    db_type : str          # mysql, postgresql, sqlite
    host    : Optional[str] = "localhost"
    port    : Optional[int] = 3306
    username: Optional[str] = ""
    password: Optional[str] = ""
    db_name : str


def build_connection_url(data: ConnectionRequest) -> str:
    """
    Different databases  URLs formats:
    MySQL:      mysql+pymysql://user:pass@host:port/dbname
    PostgreSQL: postgresql://user:pass@host:port/dbname
    SQLite:     sqlite:///path/to/file.db
    """
    if data.db_type == "mysql":
        return f"mysql+pymysql://{data.username}:{data.password}@{data.host}:{data.port}/{data.db_name}"
    elif data.db_type == "postgresql":
        return f"postgresql://{data.username}:{data.password}@{data.host}:{data.port}/{data.db_name}"
    elif data.db_type == "sqlite":
        return f"sqlite:///{data.db_name}"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported database type: {data.db_type}")



def scan_database_schema(connection_url: str) -> dict:
    """
    Dynamically discover schemas, tables, columns,
    primary keys and foreign keys across supported databases.
    """

    engine = create_engine(connection_url)

    try:
        inspector = inspect(engine)
        db_type = engine.dialect.name

        schema = {}

        # System schemas that should not be scanned.
        system_schemas = {
            "postgresql": {"pg_catalog", "information_schema"},
            "mysql": {
                "information_schema",
                "mysql",
                "performance_schema",
                "sys"
            },
            "sqlite": {"temp"}
        }

        excluded_schemas = system_schemas.get(db_type, set())

        # Discover schemas dynamically.
        schemas = inspector.get_schema_names()

        for schema_name in schemas:

            if schema_name.lower() in excluded_schemas:
                continue

            # Discover tables inside each schema.
            table_names = inspector.get_table_names(
                schema=schema_name
            )

            for table_name in table_names:

                columns = []

                # Discover columns.
                for col in inspector.get_columns(
                    table_name,
                    schema=schema_name
                ):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True)
                    })

                # Discover primary keys.
                pk = inspector.get_pk_constraint(
                    table_name,
                    schema=schema_name
                )

                # Discover foreign keys.
                fks = inspector.get_foreign_keys(
                    table_name,
                    schema=schema_name
                )

                foreign_keys = []

                for fk in fks:
                    foreign_keys.append({
                        "column": fk.get("constrained_columns", []),
                        "references_schema": fk.get("referred_schema"),
                        "references_table": fk.get("referred_table"),
                        "references_columns": fk.get("referred_columns", [])
                    })

                # Preserve exact schema and table names.
                qualified_name = f"{schema_name}.{table_name}"

                schema[qualified_name] = {
                    "schema": schema_name,
                    "table_name": table_name,
                    "columns": columns,
                    "primary_keys": pk.get(
                        "constrained_columns", []
                    ),
                    "foreign_keys": foreign_keys
                }

        return schema

    finally:
        engine.dispose()



@router.post("/add")
def add_connection(
    data         : ConnectionRequest,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """
    Add new database connection for the company.
    """
    company_id     = current_user["company_id"]
    connection_url = build_connection_url(data)

    # Test connection
    try:
        test_engine = create_engine(connection_url)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))   # simple test query
        test_engine.dispose()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot connect to database: {str(e)}"
        )

    # Scan schema
    try:
        schema = scan_database_schema(connection_url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot scan database schema: {str(e)}"
        )

    # Save to our database
    connection = DBConnection(
        company_id   = company_id,
        name         = data.name,
        db_type      = data.db_type,
        host         = data.host,
        port         = data.port,
        username     = data.username,
        password_enc = data.password,   
        db_name      = data.db_name,
        schema_json  = json.dumps(schema)
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return {
        "message"       : "Database connected successfully!",
        "connection_id" : connection.id,
        "tables_found"  : len(schema),
        "tables"        : list(schema.keys()),
        "schema"        : schema
    }


@router.get("/list")
def list_connections(
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """Get all database connections for current company."""
    connections = db.query(DBConnection).filter(
        DBConnection.company_id == current_user["company_id"],
        DBConnection.is_active  == True
    ).all()

    return {
        "connections": [
            {
                "id"     : c.id,
                "name"   : c.name,
                "db_type": c.db_type,
                "db_name": c.db_name,
                "tables" : len(json.loads(c.schema_json)) if c.schema_json else 0
            }
            for c in connections
        ]
    }