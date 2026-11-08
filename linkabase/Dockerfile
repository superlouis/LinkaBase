FROM node:22-slim AS editor-build
WORKDIR /editor
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ARG UV_VERSION=0.8.22
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --no-managed-python
COPY . .
COPY --from=editor-build /editor_dist /app/editor_dist
ENV WORKSPACE_DIR=/data
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8501 8090
CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
