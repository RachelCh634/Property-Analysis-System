# Deployment Guide

## Local Development

### Prerequisites
- Python 3.11+
- Chrome/Chromium browser

### Setup
```bash
# Clone repository
git clone https://github.com/RachelCh634/Property-Analysis-System
cd property-analysis-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Run application
# Terminal 1:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2:
streamlit run streamlit_app.py
```

Access at:
- Streamlit UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

## Docker Deployment

### Build and Run
```bash
# Using Docker Compose (recommended)
docker-compose up --build

# Or using Docker directly
docker build -t property-analysis .
docker run -p 8501:8501 -p 8000:8000 --env-file .env property-analysis
```

### Stop Services
```bash
docker-compose down
```

## Production Deployment

### Environment Configuration
```bash
# Production .env settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Add production API keys
OPENROUTER_API_KEY=<production_key>
TAVILY_API_KEY=<production_key>
LANGSMITH_API_KEY=<production_key>
```

### Cloud Deployment Options

#### Option 1: AWS EC2
1. Launch Ubuntu 22.04 instance (t3.medium minimum)
2. Install Docker and Docker Compose
3. Clone repository and configure .env
4. Run with docker-compose

#### Option 2: Heroku
```bash
heroku create app-name
heroku config:set OPENROUTER_API_KEY=<key>
heroku config:set TAVILY_API_KEY=<key>
heroku config:set LANGSMITH_API_KEY=<key>
git push heroku main
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f logs/app.log
```

## Troubleshooting

### Common Issues

1. **Port already in use**
```bash
# Kill process on port
lsof -ti:8501 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

2. **Docker issues**
```bash
docker-compose down -v
docker-compose up --build
```

3. **API key errors**
- Verify all keys are set in .env
- Check API quotas and limits