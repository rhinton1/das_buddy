FROM python:3.11-slim
WORKDIR /app

COPY postSvr.py .

RUN pip install --no-cache-dir \
    mcp \
    httpx \
    python-dotenv \
    starlette \
    uvicorn

ENV TRANSPORT=sse
ENV PORT=8002

EXPOSE 8002

CMD ["python", "postSvr.py"]

