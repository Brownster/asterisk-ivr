from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Caller(Base):
    __tablename__ = 'callers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cli = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    caller_cli = Column(String(20), nullable=False)
    call_id = Column(String(50), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    role = Column(String(20), nullable=False)  # Expected values: 'user', 'system', 'llm'
    message = Column(Text, nullable=False)
    session_data = Column(JSON)

    __table_args__ = (
        Index('idx_caller_cli', 'caller_cli'),
        Index('idx_call_id', 'call_id'),
    )
