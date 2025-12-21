import logging

from pydantic import ValidationError

from services.llm import llm_service
from services.nlp.exceptions import NLPParseError
from services.nlp.models import StatisticsQuery
from services.nlp.statistics_prompt import system_prompt
from services.nlp.statistics_schema import STATISTICS_TOOL
from services.nlp.validators import validator

logger = logging.getLogger(__name__)

class NLPService:

    async def parse_nl(self, user_message: str) -> StatisticsQuery:
        """Parses the query in Russian into a structured StatisticsQuery.
        
        Args:
            user_message: User's request in Russian
            
        Returns:
            Validated StatisticsQuery object
            
        Raises:
            NLPParseError: If the LLM returned an invalid response
        """
        request_msg = (
            f"Запрос: '{user_message}'\n"
            "Верни JSON согласно схеме."
        )

        response: dict = await llm_service.ask_with_tools(
            prompt=request_msg,
            system_prompt=system_prompt,
            tools=[STATISTICS_TOOL],
            temperature=0.0
        )
        try:
            parsed = StatisticsQuery.model_validate(response)
        except ValidationError as e:
            logger.error(f"Pydantic Validation errors: {e.json(indent=2)}")
            raise NLPParseError("Невалидная структура") from e

        try:
            validator.validate_and_normalize(parsed)
        except NLPParseError as e:
            logger.error(f"Semantic Validation failed: {e}")
            raise

        logger.info(f"Parsed: {parsed.data_source}.{parsed.aggregation.function}")
        return parsed

nlp_service = NLPService()