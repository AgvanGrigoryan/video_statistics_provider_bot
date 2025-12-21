import re
from datetime import date, datetime

from services.nlp.exceptions import NLPParseError
from services.nlp.models import TABLE_FIELDS, StatisticsQuery


def parse_date(value: str) -> date:
    """Parse date from ISO format string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)."""
    if not isinstance(value, str):
        raise NLPParseError(f"Date must be string, got: {type(value).__name__}")
    
    try:
        dt = datetime.fromisoformat(value)
        return dt.date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise NLPParseError(f"Invalid date format: '{value}'. Expected YYYY-MM-DD")


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
    except ValueError:
        raise NLPParseError(f"Cannot parse number: '{value}'")


def _get_numeric_fields() -> set[str]:
    """Extract all numeric fields from TABLE_FIELDS."""
    numeric = set()
    for table_rules in TABLE_FIELDS.values():
        numeric.update(table_rules["aggregation_fields"]["sum"])
        numeric.update(f for f in table_rules["filter_fields"] if "_count" in f)
    return numeric


NUMERIC_FIELDS = _get_numeric_fields()


class QueryValidator:
    """Validator for StatisticsQuery with normalization."""
    
    def validate_and_normalize(self, query: StatisticsQuery) -> None:
        """
        Validate and normalize query values in-place.
        
        Normalizes dates to YYYY-MM-DD and numbers to int/float.
        Mutates the query object.
        """
        self._validate_and_normalize_dates(query)
        self._validate_and_normalize_filters(query)
    
    def _validate_and_normalize_dates(self, query: StatisticsQuery) -> None:
        """Validate and normalize dates."""
        today = date.today()
        
        if query.date_range:
            start = parse_date(query.date_range.start)
            end = parse_date(query.date_range.end)
            
            if start > end:
                raise NLPParseError(f"Start date ({start}) is after end date ({end})")
            
            if end > today:
                raise NLPParseError(f"End date ({end}) cannot be in the future")
            
            query.date_range.start = start.isoformat()
            query.date_range.end = end.isoformat()
        
        date_fields = TABLE_FIELDS[query.data_source]["date_fields"]
        
        for f in query.filters:
            if f.field not in date_fields:
                continue
            
            if isinstance(f.value, list):
                normalized = []
                for v in f.value:
                    d = parse_date(v)
                    if d > today:
                        raise NLPParseError(f"Date in filter ({d}) cannot be in the future")
                    normalized.append(d.isoformat())
                f.value = normalized
            else:
                d = parse_date(f.value)
                if d > today:
                    raise NLPParseError(f"Date in filter ({d}) cannot be in the future")
                f.value = d.isoformat()
    
    def _validate_and_normalize_filters(self, query: StatisticsQuery) -> None:
        """Validate and normalize filters."""
        table_rules = TABLE_FIELDS.get(query.data_source)
        if not table_rules:
            raise NLPParseError(f"Unknown data_source: {query.data_source}")
        
        for f in query.filters:
            if f.field not in table_rules["filter_fields"]:
                raise NLPParseError(
                    f"Field '{f.field}' not available in '{query.data_source}'"
                )
            
            if f.operator == "between":
                if not isinstance(f.value, list) or len(f.value) != 2:
                    raise NLPParseError(
                        f"Operator 'between' requires array of two values, got: {f.value}"
                    )
                
                if f.field in NUMERIC_FIELDS:
                    f.value = [parse_number(v) for v in f.value]
            
            if f.field in NUMERIC_FIELDS and f.operator in ("gt", "gte", "lt", "lte", "eq"):
                f.value = parse_number(f.value)


validator = QueryValidator()