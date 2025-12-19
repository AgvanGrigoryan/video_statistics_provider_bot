FROM python:3.12-slim as base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

WORKDIR /app


FROM base as builder

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM base

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY . .


RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "-m", "bot.main"]
