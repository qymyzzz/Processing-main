FROM python:3.13.7-slim 

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8443
EXPOSE 8080

CMD ["python", "main.py"]