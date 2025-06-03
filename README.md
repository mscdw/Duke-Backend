# Duke Energy POC - FastAPI Proxy API

## Overview

This project is a FastAPI-based proxy API for interacting with the Avigilon REST API, providing endpoints for health checks, login, camera/site/server/event/media queries, and appearance/event webhooks. It is designed for secure, production-ready deployments and includes comprehensive automated tests.

## Features
- Async FastAPI app with modular routers
- Secure, environment-based configuration using `.env`
- Proxies all endpoints from the Avigilon server
- Robust error handling and logging
- Automated unit tests for all endpoints
- OpenAPI docs at `/docs`

## Requirements
- Python 3.10+

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
AVIGILON_API_VERIFY_SSL=false
# Logging
LOG_LEVEL=INFO
```

## Setup (Local Development)

1. **Clone the repo:**
   ```sh
   git clone <repo-url>
   cd duke-backend
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
- `GET /api/wep-capabilities`
- `GET /api/cameras`
- `GET /api/sites`
- `GET /api/site?id=...`
- `GET /api/servers`
- `GET /api/event-subtopics`
- `GET /api/appearance-descriptions`
- `GET /api/events-search`
- `GET /api/media`
- `POST /api/appearance-search`
- `POST /api/appearance-search-by-description`

## Security Notes
- **Do not use `verify=False` in production.** For local/dev, you may set `AVIGILON_API_VERIFY_SSL=false` in your `.env`.
- Never commit secrets or `.env` files to version control.

## Logging
- Logging is configured via the `LOG_LEVEL` env variable.

## Contributing
Pull requests are welcome! Please add/maintain tests for any new features or bugfixes.

---

For any issues, contact the project maintainer.