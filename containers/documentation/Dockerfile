FROM python:3.11-slim

WORKDIR /app

COPY agents/documentation/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/documentation/ ./

EXPOSE 8006

CMD ["python", "main.py"]