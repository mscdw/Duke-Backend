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
- Appearance and face mask event search with advanced filtering and pagination

## Requirements

- Python 3.10+

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
AVIGILON_BASE=https://your-avigilon-url
AVIGILON_USERNAME=your-avigilon-username
AVIGILON_PASSWORD=your-avigilon-password
AVIGILON_CLIENT_NAME=your-avigilon-client-name
AVIGILON_USER_NONCE=your-avigilon-user-nonce
AVIGILON_USER_KEY=your-avigilon-user-key
AVIGILON_API_VERIFY_SSL=False
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

## API Endpoints

### General

- `GET /api/health` — Health check
- `GET /api/wep-capabilities` — Web capabilities
- `GET /api/cameras` — List all cameras
- `GET /api/sites` — List all sites
- `GET /api/site?id=...` — Get a specific site
- `GET /api/servers` — List all servers
- `GET /api/event-subtopics` — List event subtopics
- `GET /api/appearance-descriptions` — List appearance descriptions

### Events & Media

- `GET /api/events-search` — Search for events
- `GET /api/media` — Get media for a camera

### Appearance & Face Mask Events

- `POST /api/appearance-search` — Search for appearance events
- `POST /api/appearance-search-by-description` — Search for appearance events by description
- `GET /api/all-face-events-fetch?date=YYYY-MM-DD` — Get all face mask events for a given date

## Security Notes

- **Do not use `verify=False` in production.** For local/dev, you may set `AVIGILON_API_VERIFY_SSL=False` in your `.env`.
- Never commit secrets or `.env` files to version control.

## Project Structure

- `app/main.py` — FastAPI app entrypoint
- `app/api/` — Routers for endpoints (appearance, events, etc.)
- `app/services/` — Service layer for Avigilon API integration
- `app/core/config.py` — Settings and environment config

---

For questions or contributions, please contact the project maintainer.
