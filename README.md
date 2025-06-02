# Duke Energy POC - FastAPI Proxy API

## Overview

This project is a FastAPI-based proxy API for interacting with the Duke REST API, providing endpoints for health checks, login, camera/site/server/event/media queries, and webhooks. It is designed for secure, production-ready deployments with Docker and includes comprehensive automated tests.

## Features
- Async FastAPI app with modular routers
- Secure, environment-based configuration
- Proxies all endpoints from the Duke server
- Robust error handling and logging
- Automated unit tests for all endpoints
- OpenAPI docs at `/docs`

## Requirements
- Python 3.10+
- Docker

## Environment Variables
Create a `.env` file in the project root with the following variables:

```
# Avigilon API
AVIGILON_BASE_URL=https://your-avigilon-url
AVIGILON_USERNAME=your-avigilon-username
AVIGILON_PASSWORD=your-avigilon-password
AVIGILON_CLIENT_NAME=your-avigilon-client-name
AVIGILON_USER_NONCE=your-avigilon-user-nonce
AVIGILON_USER_KEY=your-avigilon-user-key
# Logging
LOG_LEVEL=INFO
```

## Setup (Local Development)

1. **Clone the repo:**
   ```sh
   git clone <repo-url>
   cd duke-energy-poc
   ```
2. **Create and activate a virtualenv:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Create your `.env` file** (see above).
5. **Run the app:**
   ```sh
   uvicorn app.main:app --reload
   ```
6. **Access docs:**
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Running Tests

```sh
pytest
```

## API Endpoints

- `GET /api/health`
- `GET /api/web-capabilities`
- `POST /api/login`
- `GET /api/cameras?session=...`
- `GET /api/sites?session=...`
- `GET /api/site?session=...&id=...`
- `GET /api/servers?session=...`
- `GET /api/events`
- `POST /api/media?session=...&cameraId=...&format=...&t=...`
- `POST /webhook/events`

## Security Notes
- **Do not use `verify=False` in production.** For local/dev, you may set `DUKE_API_VERIFY_SSL=false` in your `.env` (update code to use this variable for httpx client).
- Never commit secrets or `.env` files to version control.

## Logging
- Logging is configured via the `LOG_LEVEL` env variable.

## Contributing
Pull requests are welcome! Please add/maintain tests for any new features or bugfixes.

---

For any issues, contact the project maintainer.
