from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from database.db import get_db
from models.models import DBConnection, Conversation
from utils.auth import verify_token
from ai.query_engine import QueryEngine
from config import settings

router     = APIRouter(prefix="/query", tags=["Query"])
ai_engine  = QueryEngine()    


class QueryRequest(BaseModel):
    question      : str
    connection_id : int


@router.post("/ask")
def ask_question(
    data         : QueryRequest,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """
    Main endpoint — user asks question, AI answers.
    """
    company_id = current_user["company_id"]

    # Database connection
    connection = db.query(DBConnection).filter(
        DBConnection.id         == data.connection_id,
        DBConnection.company_id == company_id,
        DBConnection.is_active  == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # Connection URL
    if connection.db_type == "mysql":
        url = f"mysql+pymysql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    elif connection.db_type == "postgresql":
        url = f"postgresql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    else:
        url = f"sqlite:///{connection.db_name}"

    # Schema
    schema = json.loads(connection.schema_json)

    # Conversation history
    history = db.query(Conversation).filter(
        Conversation.company_id    == company_id,
        Conversation.connection_id == data.connection_id
    ).order_by(
        Conversation.created_at.desc()
    ).limit(5).all()

    history_list = [
        {"question": h.question, "sql": h.sql_generated}
        for h in reversed(history)
    ]

    # Process question through AI engine
    result = ai_engine.process_question(
        question       = data.question,
        connection_url = url,
        schema         = schema,
        history        = history_list
    )

    # Save conversation to database
    conv = Conversation(
        company_id    = company_id,
        user_id       = current_user["user_id"],
        connection_id = data.connection_id,
        question      = data.question,
        sql_generated = result.get("sql"),
        answer        = result.get("answer"),
        chart_type    = result.get("chart_type"),
        chart_data    = json.dumps(result.get("chart")) if result.get("chart") else None,
    )
    db.add(conv)
    db.commit()

    return result