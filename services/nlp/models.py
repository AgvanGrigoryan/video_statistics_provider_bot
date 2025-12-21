from typing import Literal

from pydantic import BaseModel, Field, model_validator

TABLE_FIELDS = {
    "videos": {
        "aggregation_fields": {
            "count": {"*", "id"},
            "count_distinct": {"creator_id", "id"},
            "sum": {
                "views_count",
                "likes_count",
                "comments_count",
                "reports_count",
            },
        },
        "filter_fields": {
            "id",
            "creator_id",
            "video_created_at",
            "views_count",
            "likes_count",
            "comments_count",
            "reports_count",
        },
        "date_fields": {
            "video_created_at",
        },
    },
    "video_snapshots": {
        "aggregation_fields": {
            "count": {"*", "id"},
            "count_distinct": {"video_id", "id"},
            "sum": {
                "views_count",
                "likes_count",
                "comments_count",
                "reports_count",
                "delta_views_count",
                "delta_likes_count",
                "delta_comments_count",
                "delta_reports_count",
            },
        },
        "filter_fields": {
            "id",
            "video_id",
            "created_at",
            "views_count",
            "likes_count",
            "comments_count",
            "reports_count",
            "delta_views_count",
            "delta_likes_count",
            "delta_comments_count",
            "delta_reports_count",
        },
        "date_fields": {"created_at"},
    },
}


class Aggregation(BaseModel):
    function: Literal["count", "sum", "count_distinct"]
    field: str


class Filter(BaseModel):
    field: str
    operator: Literal["eq", "gt", "gte", "lt", "lte", "between"]
    value: str | int | float | list[str | int | float]


class DateRange(BaseModel):
    field: Literal["video_created_at", "created_at"]
    start: str  # YYYY-MM-DD
    end: str    # YYYY-MM-DD


class StatisticsQuery(BaseModel):
    query_type: Literal["aggregate"]
    data_source: Literal["videos", "video_snapshots"]
    aggregation: Aggregation
    filters: list[Filter] = Field(default_factory=list)
    date_range: DateRange | None = None

    @model_validator(mode="after")
    def validate_semantics(self):
        table = self.data_source
        rules = TABLE_FIELDS[table]

        agg_field = self.aggregation.field
        agg_func = self.aggregation.function
        allowed_fields = rules["aggregation_fields"].get(agg_func, set())

        if agg_field not in allowed_fields:
            raise ValueError(f"Агрегация {agg_func} по полю {agg_field} невозможна для {table}")

        for f in self.filters:
            if f.field not in rules["filter_fields"]:
                raise ValueError(f"Поле фильтра {f.field} не существует в {table}")

        dr = self.date_range
        if dr and dr.field not in rules["date_fields"]:
            raise ValueError(f"Поле даты {dr.field} не принадлежит {table}")

        if self.data_source == "videos" and agg_field.startswith("delta_"):
            raise ValueError("delta_* fields are not allowed for videos")

        return self
