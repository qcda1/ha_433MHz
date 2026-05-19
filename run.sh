cat > /addons/dc_apps/rtl433_bridge/Dockerfile << 'EOF'
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.20
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip rtl-sdr libusb rtl_433

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir requests pyyaml bottle paste schedule

WORKDIR /app
COPY *.py .
COPY views/ views/
COPY static/ static/

CMD ["python3", "-u", "/app/main.py"]
EOF