ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.20
FROM $BUILD_FROM

# Install system dependencies + rtl_433
RUN apk add --no-cache python3 py3-pip rtl-sdr libusb rtl_433

# Create virtualenv (PEP668 compliant)
RUN python3 -m venv /opt/venv

# Activate venv in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir requests pyyaml bottle paste

WORKDIR /app

COPY *.py .
COPY run.sh .
COPY views/ views/
COPY static/ static/

RUN chmod a+x /app/run.sh

CMD ["/app/run.sh"]
