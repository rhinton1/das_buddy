FROM python:3.11-slim
WORKDIR /app

COPY jiraSvr.py .

RUN pip install --no-cache-dir \
    mcp \
    jira \
    python-dotenv \
    starlette \
    uvicorn

# sse = expose over HTTP; stdio = local subprocess mode (default)
ENV TRANSPORT=sse
ENV PORT=8001

EXPOSE 8001

CMD ["python", "jiraSvr.py"]

