ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ARG APP_MODULE=app.api:app
RUN test -n "$APP_MODULE" || (echo "ERROR: pass --build-arg APP_MODULE=<module>:<app>" && exit 1)

ENV APP_MODULE=${APP_MODULE} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/var/mg.db \
    LLM_MODE=replay

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin appuser

COPY --chown=appuser:appuser . .
RUN mkdir -p /app/var && chown appuser:appuser /app/var

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','8000'), timeout=4)"

CMD ["sh", "-c", "exec uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT}"]