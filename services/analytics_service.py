# services/analytics_service.py
import logging
import re
from typing import Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from services.nlp.service import nlp_service
from services.nlp.exceptions import NLPParseError
from services.query_builder.builder import query_builder

logger = logging.getLogger(__name__)


class AnalyticsError(Exception):
    """Database execution error."""
    
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class AnalyticsService:
    """Orchestrates NLP → SQL → Database execution pipeline."""
    
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
        
        # Step 2: Generate SQL with $1, $2 placeholders
        sql, params = query_builder.build_sql(parsed_query)
        logger.info(f"SQL: {sql}")
        logger.debug(f"Params: {params}")
        
        # Step 3: Execute query
        try:
            # Convert $1, $2 to :param_1, :param_2 for SQLAlchemy
            sql_alchemy, params_dict = self._prepare_query(sql, params)
            logger.debug(f"SQLAlchemy SQL: {sql_alchemy}")
            logger.debug(f"SQLAlchemy params: {params_dict}")
            
            result = await session.execute(text(sql_alchemy), params_dict)
            row = result.scalar()
            
            if row is None:
                logger.warning("Query returned NULL, returning 0")
                return 0
            
            return int(row)
        
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}", exc_info=True)
            raise AnalyticsError("Ошибка выполнения запроса к базе данных") from e
        
        except Exception as e:
            logger.exception(f"Unexpected error during query execution: {e}")
            raise AnalyticsError("Неожиданная ошибка при выполнении запроса") from e
    
    def _prepare_query(
        self, 
        sql: str, 
        params: list[Any]
    ) -> tuple[str, dict[str, Any]]:
        """
        Convert asyncpg-style $1, $2 to SQLAlchemy-style :param_1, :param_2.
        
        Uses regex replacement in reverse order to avoid issues with
        $1 being replaced inside $10, $11, etc.
        
        Args:
            sql: SQL with $1, $2, ... placeholders
            params: List of parameter values
        
        Returns:
            (sql_with_named_params, params_dict)
        """
        params_dict = {}
        
        # Replace in REVERSE order: $10, $9, ..., $2, $1
        # This prevents $1 from matching inside $10
        for i in range(len(params), 0, -1):
            placeholder = f"${i}"
            param_name = f"param_{i}"
            
            # Use regex with word boundary to match exactly $N
            # \b ensures we don't match $1 inside $10
            pattern = re.escape(placeholder) + r'\b'
            sql = re.sub(pattern, f":{param_name}", sql)
            
            params_dict[param_name] = params[i - 1]
        
        return sql, params_dict


analytics_service = AnalyticsService()