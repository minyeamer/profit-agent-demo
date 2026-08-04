FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md semantic_schema.yml ./
COPY docs ./docs
COPY src ./src
RUN pip install --no-cache-dir uv && uv sync --no-dev

EXPOSE 8510
CMD ["uv", "run", "streamlit", "run", "src/profit_agent_demo/web_app.py", "--server.address=0.0.0.0", "--server.port=8510"]
