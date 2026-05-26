# Changelog

## 1.2.1

- Log rotation via RotatingFileHandler (max 1MB × 4 files)
- JSON output file trimming when exceeding 10MB

## 1.2.0

- Use arm64v8/python:3.11-alpine base image
- Direct port 8099 exposure
- X-Ingress-Path support for HA ingress session

## 1.1.1

- Fix config.json: add missing comma after ingress_panel

## 1.1.0

- Replace rtl_433 subprocess with pbkhrv/rtl_433 JSON file reader
- Remove scan_duration and frequency options
- Add reset_position() on startup

## 1.0.0

- Initial release
