from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from config import settings
from models import Base
import logging

logger = logging.getLogger(__name__)

# Configurar engine com pool de conexões
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=20,
    max_overflow=40,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializar banco de dados criando todas as tabelas"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def drop_db():
    """Dropar todas as tabelas (apenas para desenvolvimento)"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database dropped")


# Event listener para habilitar busca full-text em PostgreSQL
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Configurações de conexão PostgreSQL"""
    try:
        cursor = dbapi_conn.cursor()
        # Habilitar extensões úteis
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")  # Para busca de texto
        cursor.execute("CREATE EXTENSION IF NOT EXISTS uuid-ossp;")  # Para UUIDs
        dbapi_conn.commit()
        cursor.close()
    except Exception as e:
        logger.warning(f"Could not setup PostgreSQL extensions: {str(e)}")
        dbapi_conn.rollback()
