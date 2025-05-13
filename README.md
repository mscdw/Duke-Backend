# Avigilon Web Endpoints

This project is a backend server built with FastAPI to interact with Avigilon web endpoints.

## Features
- FastAPI for building APIs
- HTTPX for making HTTP requests
- PostgreSQL for storage
- APScheduler for task scheduling

## Setup
1. Create a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
