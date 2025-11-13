FROM python:3.11-slim

WORKDIR /app

COPY agents/infrastructure/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/infrastructure/ ./

EXPOSE 8004

CMD ["python", "main.py"]