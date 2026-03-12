FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN corepack enable && pnpm install --no-frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
# Keep packaging toolchain on patched versions to avoid known HIGH CVEs in runtime image scan.
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir --upgrade setuptools wheel

COPY backend /app/backend
COPY --from=frontend-builder /app/frontend/dist /app/frontend_dist

ENV PYTHONPATH=/app/backend
ENV MUP_DATABASE_URL=sqlite:///./data/app.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
