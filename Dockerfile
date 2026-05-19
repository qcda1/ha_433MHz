FROM arm64v8/python:3.11-alpine

RUN apk add --no-cache rtl-sdr libusb rtl_433

RUN pip install --no-cache-dir requests pyyaml bottle paste schedule

WORKDIR /app
COPY *.py .
COPY views/ views/
COPY static/ static/

CMD ["python3", "-u", "/app/main.py"]
