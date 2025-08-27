# Property Analysis Agentic System

An AI-powered multi-agent system for comprehensive property analysis in Los Angeles.

## 🎯 Features

- **Automated Web Scraping**: Extracts data from LA City Planning website
- **Intelligent Research**: Conducts supplementary web searches using Tavily API
- **AI Analysis**: Processes data through OpenRouter LLM integration
- **Comprehensive Reports**: Generates detailed property analysis reports
- **Real-time Monitoring**: Tracks agent performance with LangSmith
- **User-friendly Interface**: Chat-based Streamlit interface
- **Scalable Architecture**: FastAPI backend with Docker containerization

## 🛠️ Tech Stack

- **Agentic Framework**: CrewAI
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **LLM**: OpenRouter API (Claude 3 Opus / GPT-4)
- **Search**: Tavily API
- **Monitoring**: LangSmith
- **Web Scraping**: Selenium, BeautifulSoup4, Playwright
- **Containerization**: Docker

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Chrome/Chromium browser (for web scraping)
- API Keys:
  - [OpenRouter API Key](https://openrouter.ai/)
  - [Tavily API Key](https://tavily.com/)
  - [LangSmith API Key](https://smith.langchain.com/)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/RachelCh634/Property-Analysis-System
cd property-analysis-system
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
# OPENROUTER_API_KEY=your_key_here
# TAVILY_API_KEY=your_key_here
# LANGSMITH_API_KEY=your_key_here
```

### 4. Run the Application

#### Option A: Run Directly

```bash
# Terminal 1: Start FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Streamlit frontend
streamlit run streamlit_app.py
```

#### Option B: Run with Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### 5. Access the Application

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 📖 Usage

1. **Enter Property Address**: Input a Los Angeles property address in the chat interface
2. **Automated Analysis**: The system will:
   - Scrape data from LA City Planning website
   - Conduct supplementary web searches
   - Analyze data using AI
   - Generate comprehensive report
3. **View Results**: Receive detailed property analysis including:
   - Zoning information
   - Permit history
   - Development opportunities
   - Market context
   - Regulatory considerations

## 🏗️ Project Structure

```
property-analysis-system/
├── streamlit_app.py       # Streamlit frontend
├── main.py               # FastAPI backend
├── agents.py             # CrewAI agents implementation
├── scraper.py            # Web scraping logic
├── llm_integration.py    # OpenRouter LLM integration
├── search_integration.py # Tavily search integration
├── models.py             # Pydantic data models
├── services.py           # Business logic layer
├── config.yaml           # System configuration
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose setup
├── .env.example         # Environment variables template
└── README.md            # Project documentation
```

## 🔧 Configuration

### config.yaml

The system configuration is managed through `config.yaml`:

- **Agents**: Configure agent roles, models, and parameters
- **Scraping**: Set URLs, selectors, and timeouts
- **LLM**: Configure prompts and model settings
- **Search**: Set search depth and query templates

### Environment Variables

Key environment variables in `.env`:

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `TAVILY_API_KEY`: Your Tavily search API key
- `LANGSMITH_API_KEY`: Your LangSmith monitoring key
- `APP_ENV`: Application environment (development/production)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

## 📊 API Documentation

### Endpoints

#### POST `/analyze`
Analyze a property by address

**Request:**
```json
{
  "address": "1600 Vine"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "property_overview": "...",
    "zoning_info": "...",
    "permits": [],
    "analysis": "...",
    "recommendations": "..."
  }
}
```

#### GET `/health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Selenium WebDriver Issues**
   ```bash
   # Install Chrome/Chromium
   sudo apt-get install chromium-browser chromium-driver
   ```

2. **API Key Errors**
   - Ensure all API keys are correctly set in `.env`
   - Check API key validity and quota limits

3. **Port Already in Use**
   ```bash
   # Kill process on port
   lsof -ti:8501 | xargs kill -9
   lsof -ti:8000 | xargs kill -9
   ```

4. **Docker Issues**
   ```bash
   # Reset Docker
   docker-compose down -v
   docker-compose up --build
   ```

## Testing

### test_api.py
Async performance testing suite that validates system requirements with 10 test addresses. Tests include comprehensive metrics validation (90% success rate, <120s avg response time), concurrent user handling (10 simultaneous requests), and individual response time verification. All tests use pytest-asyncio framework and httpx async client for realistic performance simulation.

Run tests: `python -m pytest -s -v`