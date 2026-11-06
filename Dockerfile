FROM node:22-slim AS editor-build
WORKDIR /editor
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=editor-build /editor_dist /app/editor_dist
ENV WORKSPACE_DIR=/data
EXPOSE 8501 8090
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
