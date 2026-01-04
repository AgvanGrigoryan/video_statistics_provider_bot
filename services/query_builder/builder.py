from typing import Any

from services.exceptions import QueryBuildError
from services.nlp.models import Aggregation, Filter, StatisticsQuery


class QueryBuilder:
    """Build SQL queries from StatisticsQuery objects with SQL injection protection."""
    
    # Whitelist для защиты от SQL injection
    ALLOWED_FIELDS = {
        "*", "id", "video_id", "creator_id",
        "video_created_at", "created_at",
        "views_count", "likes_count", "comments_count", "reports_count",
        "delta_views_count", "delta_likes_count", 
        "delta_comments_count", "delta_reports_count",
    }
    
    ALLOWED_TABLES = {"videos", "video_snapshots"}
    ALLOWED_OPERATORS = {"eq", "gt", "gte", "lt", "lte", "between"}
    
    def build_sql(self, query: StatisticsQuery) -> tuple[str, dict[str, Any]]:
        """
        Generate parameterized SQL query for asyncpg-style placeholders ($1, $2).
        
        Args:
            query: Validated StatisticsQuery object
        
        Returns:
            Tuple of (SQL string with $N placeholders, parameter list)
        """
        table = query.data_source
        
        # SQL injection protection
        if table not in self.ALLOWED_TABLES:
            raise QueryBuildError(
                message=f"Invalid table: {table}",
                user_message=f"Недопустимая таблица: {table}"
            )
        
        select_clause = self._build_select(query.aggregation)
        where_clauses, params = self._build_where(query)
        
        sql = f"SELECT {select_clause} FROM {table}"
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        return sql, params
    
    def _validate_field(self, field: str) -> None:
        """Validate field name against whitelist (SQL injection protection)."""
        if field not in self.ALLOWED_FIELDS:
            raise QueryBuildError(
                message=f"Invalid field name: {field}",
                user_message=f"Недопустимое поле: {field}"
            )
    
    def _build_select(self, agg: Aggregation) -> str:
        """
        Build SELECT clause with aggregation function.
        
        Args:
            agg: Aggregation configuration
        
        Returns:
            SQL SELECT clause string
            
        Raises:
            QueryBuildError: If aggregation function is unknown
        """
        func = agg.function.upper()
        field = agg.field
        
        # SQL injection protection
        self._validate_field(field)
        
        if func == "COUNT":
            return f"COUNT({field})"
        elif func == "SUM":
            return f"SUM({field})"
        elif func == "COUNT_DISTINCT":
            return f"COUNT(DISTINCT {field})"
        else:
            raise QueryBuildError(
                message=f"Unknown aggregation function: {func}",
                user_message=f"Неизвестная функция агрегации: {func}"
            )
    
    def _build_where(self, query: StatisticsQuery) -> tuple[list[str], dict[str, Any]]:
        """
        Build WHERE clause from filters and date range.
        
        Args:
            query: StatisticsQuery with filters and date_range
        
        Returns:
            Tuple of (condition list, parameter dict)
        """
        clauses: list[str] = []
        params: dict[str, Any] = {}
        param_idx = 1
        
        # Process filters
        for f in query.filters:
            clause, new_params, param_idx = self._build_filter_clause(f, param_idx)
            clauses.append(clause)
            params.update(new_params)
        
        # Process date_range
        if query.date_range:
            dr = query.date_range
            
            # SQL injection protection
            self._validate_field(dr.field)
            
            clauses.append(f"{dr.field} BETWEEN :param_{param_idx} AND :param_{param_idx + 1}")
            params[f"param_{param_idx}"] = dr.start
            params[f"param_{param_idx + 1}"] = dr.end
            param_idx += 2
        
        return clauses, params
    
    def _build_filter_clause(
        self, 
        f: Filter, 
        start_idx: int
    ) -> tuple[str, dict[str, Any], int]:
        """
        Build single WHERE condition with parameterized values.
        
        Args:
            f: Filter object
            start_idx: Current parameter index for $N placeholder
        
        Returns:
            Tuple of (condition string, values, next index)
            
        Raises:
            QueryBuildError: If operator is unknown or between value is invalid
        """
        field = f.field
        op = f.operator
        value = f.value
        
        # SQL injection protection
        self._validate_field(field)
        if op not in self.ALLOWED_OPERATORS:
            raise QueryBuildError(
                message=f"Invalid operator: {op}",
                user_message=f"Недопустимый оператор: {op}"
            )
        param_name = f"param_{start_idx}"
        if op == "eq":
            return f"{field} = :{param_name}", {param_name: value}, start_idx + 1
        
        elif op == "gt":
            return f"{field} > :{param_name}", {param_name: value}, start_idx + 1
        
        elif op == "gte":
            return f"{field} >= :{param_name}", {param_name: value}, start_idx + 1
        
        elif op == "lt":
            return f"{field} < :{param_name}", {param_name: value}, start_idx + 1
        
        elif op == "lte":
            return f"{field} <= :{param_name}", {param_name: value}, start_idx + 1

        elif op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise QueryBuildError(
                    message=f"Between requires 2 values, got: {value!r}",
                    user_message="Оператор 'between' требует два значения"
                )
            param_name_1 = f"param_{start_idx}"
            param_name_2 = f"param_{start_idx + 1}"

            clause = f"{field} BETWEEN :{param_name_1} AND :{param_name_2}"
            params = {param_name_1: value[0], param_name_2: value[1]}

            return clause, params, start_idx + 2
        
        else:
            raise QueryBuildError(
                message=f"Unknown operator: {op}",
                user_message=f"Неизвестный оператор: {op}"
            )


query_builder = QueryBuilder()