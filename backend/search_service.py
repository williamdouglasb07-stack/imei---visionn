from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from models import IMEI, ImageUpload, SearchHistory
from schemas import SearchQueryType
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Serviço de busca de IMEIs"""
    
    @staticmethod
    def search_imeis(
        user_id: str,
        query: str,
        search_type: SearchQueryType = SearchQueryType.partial,
        limit: int = 20,
        offset: int = 0,
        db: Session = None
    ) -> dict:
        """
        Buscar IMEIs com diferentes estratégias
        """
        if not db:
            raise ValueError("Database session required")
        
        start_time = time.time()
        
        # Normalizar query
        query_normalized = query.strip()
        
        # Construir query base
        base_query = db.query(IMEI).filter(IMEI.user_id == user_id)
        
        # Aplicar filtro baseado no tipo de busca
        if search_type == SearchQueryType.full:
            # Busca completa exata
            filtered_query = base_query.filter(
                IMEI.imei_normalized == query_normalized
            )
        elif search_type == SearchQueryType.partial:
            # Busca parcial (contém)
            filtered_query = base_query.filter(
                IMEI.imei_normalized.ilike(f"%{query_normalized}%")
            )
        elif search_type == SearchQueryType.last_digits:
            # Busca pelos últimos dígitos
            filtered_query = base_query.filter(
                IMEI.imei_normalized.endswith(query_normalized)
            )
        else:
            filtered_query = base_query
        
        # Contar total
        total = filtered_query.count()
        
        # Aplicar paginação e ordenar por data (mais recentes primeiro)
        results = filtered_query.order_by(
            IMEI.extracted_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Calcular tempo de busca
        search_time_ms = (time.time() - start_time) * 1000
        
        # Registrar no histórico de buscas
        try:
            search_history = SearchHistory(
                user_id=user_id,
                query=query_normalized,
                query_type=search_type.value,
                results_count=total,
                search_time_ms=search_time_ms
            )
            db.add(search_history)
            db.commit()
        except Exception as e:
            logger.error(f"Error saving search history: {str(e)}")
            db.rollback()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": results,
            "search_time_ms": search_time_ms
        }
    
    @staticmethod
    def search_advanced(
        user_id: str,
        query: str,
        filters: dict = None,
        db: Session = None
    ) -> list:
        """
        Busca avançada com filtros
        """
        if not db:
            raise ValueError("Database session required")
        
        base_query = db.query(IMEI).filter(IMEI.user_id == user_id)
        
        # Busca por IMEI
        if query:
            base_query = base_query.filter(
                IMEI.imei_normalized.ilike(f"%{query}%")
            )
        
        # Filtro por marca
        if filters and filters.get("brand"):
            base_query = base_query.filter(
                IMEI.device_brand.ilike(f"%{filters['brand']}%")
            )
        
        # Filtro por modelo
        if filters and filters.get("model"):
            base_query = base_query.filter(
                IMEI.device_model.ilike(f"%{filters['model']}%")
            )
        
        # Filtro por validação
        if filters and filters.get("is_valid") is not None:
            base_query = base_query.filter(
                IMEI.is_valid == filters["is_valid"]
            )
        
        # Filtro por data
        if filters and filters.get("start_date"):
            base_query = base_query.filter(
                IMEI.extracted_at >= filters["start_date"]
            )
        
        if filters and filters.get("end_date"):
            base_query = base_query.filter(
                IMEI.extracted_at <= filters["end_date"]
            )
        
        return base_query.order_by(IMEI.extracted_at.desc()).all()
    
    @staticmethod
    def get_search_suggestions(
        user_id: str,
        prefix: str,
        db: Session = None,
        limit: int = 10
    ) -> list:
        """
        Obter sugestões de busca (autocomplete)
        """
        if not db:
            raise ValueError("Database session required")
        
        suggestions = db.query(IMEI.imei_normalized).distinct().filter(
            and_(
                IMEI.user_id == user_id,
                IMEI.imei_normalized.startswith(prefix)
            )
        ).order_by(IMEI.extracted_at.desc()).limit(limit).all()
        
        return [s[0] for s in suggestions]
    
    @staticmethod
    def get_search_history(
        user_id: str,
        limit: int = 50,
        db: Session = None
    ) -> list:
        """
        Obter histórico de buscas do usuário
        """
        if not db:
            raise ValueError("Database session required")
        
        return db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(
            SearchHistory.searched_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_similar_imeis(
        user_id: str,
        imei: str,
        threshold: float = 0.8,
        db: Session = None
    ) -> list:
        """
        Encontrar IMEIs similares (para detectar possíveis duplicatas/correções)
        """
        if not db:
            raise ValueError("Database session required")
        
        # Implementação simples: encontrar IMEIs que começam com os primeiros 8 dígitos
        tac = imei[:8]
        
        similar = db.query(IMEI).filter(
            and_(
                IMEI.user_id == user_id,
                IMEI.imei_normalized.startswith(tac)
            )
        ).order_by(IMEI.extracted_at.desc()).all()
        
        return similar
