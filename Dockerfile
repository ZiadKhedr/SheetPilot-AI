FROM node:24-bookworm-slim AS frontend
WORKDIR /app/frontend
RUN npm install -g pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim
ENV SHEETPILOT_ROOT=/app
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[app]"
COPY demo_data/ ./demo_data/
COPY --from=frontend /app/frontend/dist ./frontend/dist/
RUN useradd --uid 10001 --create-home sheetpilot && mkdir -p /app/.data && chown -R sheetpilot:sheetpilot /app
USER sheetpilot
EXPOSE 8000
CMD ["python","-m","uvicorn","sheetpilot.api:app","--host","0.0.0.0","--port","8000"]
