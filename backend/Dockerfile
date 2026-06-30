FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV PYTHONPATH=/app

EXPOSE 5000

# Corre migraciones y luego levanta Flask
CMD ["sh", "-c", "alembic upgrade head && flask run --host=0.0.0.0 --port=5000 --reload"]
