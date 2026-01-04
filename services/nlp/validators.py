import re
from datetime import date, datetime
from uuid import UUID

from services.exceptions import NLPParseError
from services.nlp.models import TABLE_FIELDS, StatisticsQuery


def parse_date(value: str) -> date:
    """Parse date from ISO format string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)."""
    if not isinstance(value, str):
        raise NLPParseError(
            message=f"Date must be string, got: {type(value).__name__}",
            user_message="Некорректный тип даты"
        )
    try:
        dt = datetime.fromisoformat(value)
        return dt.date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError as e:
            raise NLPParseError(
                message=f"Invalid date: {value}",
                user_message="Некорректный формат даты"
            ) from e

def parse_number(value: int | float | str) -> int | float:
    """
    Normalize numbers from various formats.
    
    Examples: 100 -> 100, "100k" -> 100000, "5 тыс" -> 5000
    """
    if isinstance(value, (int, float)):
        return value
    
    s = str(value).strip().lower()
    
    if re.match(r'^\d+(\.\d+)?[kк]$', s):
        return int(float(s[:-1]) * 1000)
    
    s_clean = s.replace(' ', '').replace('тыс', '').replace('тысяч', '')
    if s_clean != s and s_clean:
        try:
            return int(float(s_clean) * 1000)
        except ValueError:
            pass
    
    s_normalized = s.replace(' ', '').replace(',', '.')
    try:
        if '.' in s_normalized:
            return float(s_normalized)
        return int(s_normalized)
    except ValueError as e:
        raise NLPParseError(
            message=f"Cannot parse number: {value}",
            user_message=f"Не удалось распознать число: '{value}'"
        ) from e


def validate_uuid(value: str, field_name: str) -> str:
    """
    Validate UUID format.
    
    Args:
        value: UUID string (with or without dashes)
        field_name: Name of the field (for error messages)
    
    Returns:
        Normalized UUID string
        
    Raises:
        NLPParseError: If UUID format is invalid
    """
    if not isinstance(value, str):
        raise NLPParseError(
            message=f"UUID field must be string, got: {type(value).__name__}",
            user_message=f"Поле '{field_name}' должно быть строкой"
        )
    
    # Try to parse as UUID to validate format
    # Remove spaces
    value = value.strip()
    try:
        # UUID() accepts both formats: with and without dashes
        uuid_obj = UUID(value)
        
        # Return original format (preserve dashes/no-dashes as provided)
        return value
        
    except ValueError as e:
        raise NLPParseError(
            message=f"Invalid UUID format for field '{field_name}': '{value}'. ",
            user_message=f"Некорректный формат UUID для поля '{field_name}'"
        ) from e


def _get_numeric_fields() -> set[str]:
    """Extract all numeric fields from TABLE_FIELDS."""
    numeric = set()
    for table_rules in TABLE_FIELDS.values():
        numeric.update(table_rules["aggregation_fields"]["sum"])
        numeric.update(f for f in table_rules["filter_fields"] if "_count" in f)
    return numeric


def _get_uuid_fields() -> set[str]:
    """Get all UUID fields (id, video_id, creator_id)."""
    return {"id", "video_id", "creator_id"}


NUMERIC_FIELDS = _get_numeric_fields()
UUID_FIELDS = _get_uuid_fields()


class QueryValidator:
    """Validator for StatisticsQuery with normalization."""
    
    def validate_and_normalize(self, query: StatisticsQuery) -> None:
        """
        Validate and normalize query values in-place.
        
        Normalizes:
        - Dates to YYYY-MM-DD
        - Numbers to int/float
        - UUIDs (validates format)
        
        Mutates the query object.
        """
        self._validate_and_normalize_dates(query)
        self._validate_and_normalize_filters(query)
    
    def _validate_and_normalize_dates(self, query: StatisticsQuery) -> None:
        """Validate and normalize dates to date objects."""
        today = date.today()
        
        if query.date_range:
            start = parse_date(query.date_range.start)  # str → date
            end = parse_date(query.date_range.end)
            
            if start > end:
                raise NLPParseError(
                    message=f"Start date {start} > end date {end}",
                    user_message=f"Начальная дата ({start}) позже конечной ({end})"
                )
            
            if end > today:
                raise NLPParseError(
                    message=f"End date {end} is in future (today: {today})",
                    user_message=f"Конечная дата ({end}) не может быть в будущем"
                )
            query.date_range.start = start  # type: date
            query.date_range.end = end      # type: date
        
        date_fields = TABLE_FIELDS[query.data_source]["date_fields"]
        
        for f in query.filters:
            if f.field not in date_fields:
                continue
            
            if isinstance(f.value, list):
                normalized = []
                for v in f.value:
                    d = parse_date(v)
                    if d > today:
                        raise NLPParseError(
                            message=f"Date {d} is in future (today: {today})",
                            user_message=f"Дата ({d}) не может быть в будущем"
                        )
                    normalized.append(d)  # ✅ date объект
                f.value = normalized
            else:
                d = parse_date(f.value)
                if d > today:
                    raise NLPParseError(
                        message=f"Date {d} is in future (today: {today})",
                        user_message=f"Дата ({d}) не может быть в будущем"
                    )
                f.value = d  # ✅ date объект

    
    def _validate_and_normalize_filters(self, query: StatisticsQuery) -> None:
        """Validate and normalize filters."""
        table_rules = TABLE_FIELDS.get(query.data_source)
        if not table_rules:
            raise NLPParseError(
                message=f"Unknown data_source: {query.data_source}",
                user_message=f"Неизвестная таблица: {query.data_source}"
            )
            
        for f in query.filters:
            if f.field not in table_rules["filter_fields"]:
                raise NLPParseError(
                    message=f"Field '{f.field}' not available in '{query.data_source}'",
                    user_message=f"Поле '{f.field}' недоступно в таблице '{query.data_source}'"
                )
            
            # Validate UUID fields
            if f.field in UUID_FIELDS:
                if isinstance(f.value, list):
                    # For 'between' or 'in' operators (though unusual for UUIDs)
                    f.value = [validate_uuid(v, f.field) for v in f.value]
                else:
                    f.value = validate_uuid(f.value, f.field)
                continue  # Skip numeric validation
            
            # Validate 'between' operator
            if f.operator == "between":
                if not isinstance(f.value, list) or len(f.value) != 2:
                    raise NLPParseError(
                        message=f"Operator 'between' requires array of two values, got: {f.value}",
                        user_message="Оператор 'between' требует два значения"
                    )
                
                if f.field in NUMERIC_FIELDS:
                    f.value = [parse_number(v) for v in f.value]
            
            # Normalize numeric fields
            if f.field in NUMERIC_FIELDS and f.operator in ("gt", "gte", "lt", "lte", "eq"):
                f.value = parse_number(f.value)


validator = QueryValidator()