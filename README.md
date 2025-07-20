# Travel Data Parser API

A FastAPI-based web service that extracts structured travel booking information from various travel platform URLs.

## Project Structure

```
travel-data-parser/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/                 # API routes and endpoints
│   │   └── __init__.py
│   ├── core/                # Core configuration and settings
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/              # Pydantic models
│   │   └── __init__.py
│   ├── parsers/             # Platform-specific parsers
│   │   └── __init__.py
│   └── services/            # Business logic services
│       └── __init__.py
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore rules
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Setup

1. **Clone the repository and navigate to the project directory**

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, visit:
- API Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Dependencies

- **FastAPI** (>=0.104.0): Modern web framework for building APIs
- **httpx** (>=0.25.0): Async HTTP client for web scraping
- **BeautifulSoup4** (>=4.12.0): HTML parsing library
- **Anthropic** (>=0.8.0): Claude AI API client
- **Uvicorn** (>=0.24.0): ASGI server
- **Pydantic** (>=2.0.0): Data validation and settings management

## Development

The project follows a modular structure:
- `app/api/`: API route definitions
- `app/models/`: Pydantic models for request/response validation
- `app/services/`: Business logic and service classes
- `app/parsers/`: Platform-specific parsing implementations
- `app/core/`: Configuration and core utilities

## Environment Variables

See `.env.example` for all available configuration options.