from typing import Any
from services.nlp.models import StatisticsQuery, Filter, Aggregation


class QueryBuilder:
    """Build SQL queries from StatisticsQuery objects."""
    
    def build_sql(self, query: StatisticsQuery) -> tuple[str, list[Any]]:
        """Generate parameterized SQL query for asyncpg.
        
        Args:
            query: Validated StatisticsQuery object
        
        Returns:
            Tuple of (SQL string, parameter list)
        """
        table = query.data_source
        select_clause = self._build_select(query.aggregation)
        where_clauses, params = self._build_where(query)
        
        sql = f"SELECT {select_clause} FROM {table}"
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        return sql, params
    
    def _build_select(self, agg: Aggregation) -> str:
        """Build SELECT clause with aggregation function.
        
        Args:
            agg: Aggregation configuration
        
        Returns:
            SQL SELECT clause string
            
        Raises:
            ValueError: If aggregation function is unknown
        """
        func = agg.function.upper()
        field = agg.field
        
        if func == "COUNT":
            return f"COUNT({field})"
        elif func == "SUM":
            return f"SUM({field})"
        elif func == "COUNT_DISTINCT":
            return f"COUNT(DISTINCT {field})"
        else:
            raise ValueError(f"Unknown aggregation function: {func}")
    
    def _build_where(self, query: StatisticsQuery) -> tuple[list[str], list[Any]]:
        """Build WHERE clause from filters and date range.
        
        Args:
            query: StatisticsQuery with filters and date_range
        
        Returns:
            Tuple of (condition list, parameter list)
        """
        clauses: list[str] = []
        params: list[Any] = []
        param_idx = 1
        
        # Process filters
        for f in query.filters:
            clause, new_params, param_idx = self._build_filter_clause(f, param_idx)
            clauses.append(clause)
            params.extend(new_params)
        
        # Process date_range
        if query.date_range:
            dr = query.date_range
            clauses.append(f"{dr.field} BETWEEN ${param_idx} AND ${param_idx + 1}")
            params.extend([dr.start, dr.end])
            param_idx += 2
        
        return clauses, params
    
    def _build_filter_clause(
        self, 
        f: Filter, 
        start_idx: int
    ) -> tuple[str, list[Any], int]:
        """Build single WHERE condition with parameterized values.
        
        Args:
            f: Filter object
            start_idx: Current parameter index for $N placeholder
        
        Returns:
            Tuple of (condition string, values, next index)
            
        Raises:
            ValueError: If operator is unknown or between value is invalid
        """
        field = f.field
        op = f.operator
        value = f.value
        
        if op == "eq":
            return f"{field} = ${start_idx}", [value], start_idx + 1
        
        elif op == "gt":
            return f"{field} > ${start_idx}", [value], start_idx + 1
        
        elif op == "gte":
            return f"{field} >= ${start_idx}", [value], start_idx + 1
        
        elif op == "lt":
            return f"{field} < ${start_idx}", [value], start_idx + 1
        
        elif op == "lte":
            return f"{field} <= ${start_idx}", [value], start_idx + 1
        
        elif op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError(f"Operator 'between' requires list of 2 values, got: {value!r}")
            clause = f"{field} BETWEEN ${start_idx} AND ${start_idx + 1}"
            return clause, [value[0], value[1]], start_idx + 2
        
        else:
            raise ValueError(f"Unknown operator: {op}")


query_builder = QueryBuilder()
