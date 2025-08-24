FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Start the Finnish Deals Bot
CMD ["python", "railway_start.py"]
