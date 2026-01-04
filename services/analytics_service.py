import logging
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DataError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from services.exceptions import DatabaseError, LLMServiceError, NLPParseError, QueryBuildError
from services.nlp.service import nlp_service
from services.query_builder.builder import query_builder

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Orchestrates NLP → SQL → Database execution pipeline."""
    
    async def process_user_query(
        self,
        user_message: str,
        session: AsyncSession,
        user_id: int | None = None
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
        ctx = f"[User {user_id}]" if user_id else "[Unknown User]"

        logger.info(f"{ctx} Processing query: {user_message[:100]}")
        try:
            parsed_query = await nlp_service.parse_nl(user_message)
            logger.debug(
                f"{ctx} Parsed: {parsed_query.data_source}."
                f"{parsed_query.aggregation.function}({parsed_query.aggregation.field})"
            )

            sql, params_dict = query_builder.build_sql(parsed_query)
            logger.debug(f"{ctx} SQL: {sql}")
            logger.debug(f"{ctx} Params: {params_dict}")
        
  
            result = await session.execute(text(sql), params_dict)
            value = result.scalar()

            if value is None:
                logger.warning("Query returned NULL, returning 0")
                return 0

            logger.info(f"{ctx} Result: {value}")
            return int(value)

        except LLMServiceError as e:
            logger.warning(f"{ctx} LLM error: {e.message}")
            raise
        except NLPParseError as e:
            logger.warning(f"{ctx} NLP parse error: {e.message}")
            raise
        except QueryBuildError as e:
            logger.error(f"{ctx} Query build error: {e.message}", exc_info=True)
            raise
        except OperationalError as e:
            logger.error(f"{ctx} Database unavailable: {e}", exc_info=True)
            raise DatabaseError(
                message=f"Operational error: {e}",
                user_message="База данных временно недоступна"
            ) from e
        
        except DataError as e:
            logger.error(f"{ctx} Data type error: {e}", exc_info=True)
            raise DatabaseError(
                message=f"Data error: {e}",
                user_message="Ошибка типов данных"
            ) from e
        except SQLAlchemyError as e:
            logger.error(f"{ctx} Database error: {e}", exc_info=True)
            raise DatabaseError(
                message=f"Database error: {e}",
                user_message="Ошибка выполнения запроса"
            ) from e
        
        except Exception as e:
            logger.exception(f"{ctx} Unexpected error during query execution: {e}")
            raise DatabaseError(
                message=f"Unexpected error: {e}",
                user_message="Неожиданная ошибка сервера"
            ) from e

analytics_service = AnalyticsService()