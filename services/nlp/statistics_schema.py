

STATISTICS_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "query_type": {
            "type": "string",
            "enum": ["aggregate"],
            "description": "Тип запроса"
        },
        "data_source": {
            "type": "string",
            "enum": ["videos", "video_snapshots"],
            "description": "Источник данных"
        },
        "aggregation": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "string",
                    "enum": ["count", "sum", "count_distinct"],
                    "description": "Агрегатная функция"
                },
                "field": {
                    "type": "string",
                    "enum": [
                        "*",
                        "id",
                        "video_id",
                        "creator_id",
                        "views_count",
                        "likes_count",
                        "comments_count",
                        "reports_count",
                        "delta_views_count",
                        "delta_likes_count",
                        "delta_comments_count",
                        "delta_reports_count"
                    ],
                    "description": "Поле агрегации"
                }
            },
            "required": ["function", "field"]
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": [
                            "id",
                            "video_id",
                            "creator_id",
                            "video_created_at",
                            "created_at",
                            "views_count",
                            "likes_count",
                            "comments_count",
                            "reports_count",
                            "delta_views_count",
                            "delta_likes_count",
                            "delta_comments_count",
                            "delta_reports_count"
                        ]
                    },
                    "operator": {
                        "type": "string",
                        "enum": ["eq", "gt", "gte", "lt", "lte", "between"]
                    },
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "number"}
                                    ]
                                }
                            }
                        ]
                    }
                },
                "required": ["field", "operator", "value"]
            }
        },
        "date_range": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": ["video_created_at", "created_at"],
                    "description": "Поле даты"
                },
                "start": {
                    "type": "string",
                    "format": "date"
                },
                "end": {
                    "type": "string",
                    "format": "date"
                }
            },
            "required": ["field", "start", "end"]
        }
    },
    "required": ["query_type", "data_source", "aggregation"]
}


STATISTICS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "extract_query_intent",
        "description": "Extract structured analytics query from Russian natural language",
        "parameters": STATISTICS_TOOL_SCHEMA
    }
}
