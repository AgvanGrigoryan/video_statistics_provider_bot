# services/analytics_service.py

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from services.nlp.service import nlp_service
from services.nlp.exceptions import NLPParseError
from services.query_builder.builder import query_builder

logger = logging.getLogger(__name__)


class AnalyticsError(Exception):
    """Ошибка выполнения аналитического запроса."""
    
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class AnalyticsService:
    """
    Orchestrates NLP → SQL → Database execution pipeline.
    """
    
    async def process_user_query(
        self,
        user_message: str,
        session: AsyncSession,
    ) -> int:
        """
        Process user's natural language query and return numeric result.
        
        Args:
            user_message: User's question in Russian
            session: Database session from get_async_session()
        
        Returns:
            Numeric result (count, sum, etc.)
            
        Raises:
            NLPParseError: If LLM fails to parse query
            AnalyticsError: If database execution fails
        """
        # Step 1: Parse natural language → StatisticsQuery
        logger.info(f"Processing: {user_message[:100]}...")
        parsed_query = await nlp_service.parse_nl(user_message)
        
        # Step 2: Generate SQL
        sql, params = query_builder.build_sql(parsed_query)
        logger.info(f"SQL: {sql}")
        logger.debug(f"Params: {params}")
        
        # Step 3: Execute query
        try:
            # Конвертируем $1, $2 в :param_1, :param_2 для SQLAlchemy
            sql_alchemy, params_dict = self._prepare_query(sql, params)
            
            result = await session.execute(text(sql_alchemy), params_dict)
            row = result.scalar()
            
            if row is None:
                logger.warning("Query returned NULL, returning 0")
                return 0
            
            return int(row)
        
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise AnalyticsError("Ошибка выполнения запроса к базе данных") from e
    
    def _prepare_query(
        self, 
        sql: str, 
        params: list[Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        Convert asyncpg-style $1, $2 to SQLAlchemy-style :param_1, :param_2.
        
        Args:
            sql: SQL with $1, $2, ... placeholders
            params: List of parameter values
        
        Returns:
            (sql_with_named_params, params_dict)
        """
        params_dict = {}
        
        for i, value in enumerate(params, start=1):
            placeholder = f"${i}"
            param_name = f"param_{i}"
            sql = sql.replace(placeholder, f":{param_name}")
            params_dict[param_name] = value
        
        return sql, params_dict


analytics_service = AnalyticsService()
