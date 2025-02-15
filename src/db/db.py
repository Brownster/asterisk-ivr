from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .models import Base, Caller, ChatHistory
import yaml
import os
from utils.logger import logger
from alembic.config import Config
from alembic import command

class Database:
    def __init__(self):
        with open('config/db_config.yml') as f:
            config = yaml.safe_load(f)['database']
        
        # Build the connection string
        connection_string = (
            f"{config['dialect']}+{config['driver']}://"
            f"{config['username']}:{config['password']}@"
            f"{config['host']}:{config['port']}/"
            f"{config['database_name']}"
        )
        
        # Append SSL parameters if environment variables are set
        ssl_params = []
        if os.getenv("DB_SSL_CA"):
            ssl_params.append(f"ssl_ca={os.getenv('DB_SSL_CA')}")
        if os.getenv("DB_SSL_CERT"):
            ssl_params.append(f"ssl_cert={os.getenv('DB_SSL_CERT')}")
        if os.getenv("DB_SSL_KEY"):
            ssl_params.append(f"ssl_key={os.getenv('DB_SSL_KEY')}")
        if ssl_params:
            connection_string += "?" + "&".join(ssl_params)
        
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=2,
            pool_timeout=30,
            pool_recycle=3600  # Pre-ping can be added if desired (pool_pre_ping=True)
        )
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self._run_migrations()
    
    def _run_migrations(self):
        """Apply Alembic migrations programmatically."""
        try:
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("script_location", "src/db/migrations")
            command.upgrade(alembic_cfg, "head")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    def get_session(self):
        return self.Session()

    def get_caller(self, cli):
        session = self.get_session()
        try:
            caller = session.query(Caller).filter_by(cli=cli).first()
            return caller
        except Exception as e:
            logger.error(f"Error retrieving caller {cli}: {e}")
        finally:
            session.close()

    def add_chat_history(self, caller_cli, call_id, role, message, session_data=None):
        session = self.get_session()
        try:
            new_entry = ChatHistory(
                caller_cli=caller_cli,
                call_id=call_id,
                role=role,
                message=message,
                session_data=session_data
            )
            session.add(new_entry)
            session.commit()
        except Exception as e:
            logger.error(f"Error adding chat history for caller {caller_cli}: {e}")
            session.rollback()
        finally:
            session.close()

    def safe_execute_raw(self, query: str, params: dict = None):
        """Safe parameterized query execution."""
        session = self.get_session()
        try:
            statement = text(query)
            result = session.execute(statement, params or {})
            session.commit()
            return result
        except Exception as e:
            logger.error(f"Query failed: {str(e)} - Query: {query}")
            session.rollback()
            raise
        finally:
            session.close()
