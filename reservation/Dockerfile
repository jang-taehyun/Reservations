FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY reservation.py /app/reservation.py

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "reservation.py"]
