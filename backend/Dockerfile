FROM python:3.12-slim

WORKDIR /repo/backend

# Copy only requirements first for layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

ENV FLASK_APP=app.py
# /repo is mounted at runtime (volume); PYTHONPATH lets "from backend.x" resolve
ENV PYTHONPATH=/repo

EXPOSE 5000

CMD ["sh", "-c", "alembic upgrade head && flask run --host=0.0.0.0 --port=5000 --reload"]
