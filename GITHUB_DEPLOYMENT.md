# Content Workflow Agent - Local Deployment Guide

## Overview

This guide provides complete instructions for running the Content Workflow Agent locally from a fresh GitHub repository clone. The application will run with a Streamlit frontend and FastAPI backend, designed for local development and testing.

## Prerequisites

- Python 3.11 or higher
- Git
- OpenAI API key

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-github-repo-url>
cd content-workflow-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Run automated setup (recommended)
python setup.py

# OR manually install dependencies
pip install -r requirements_github.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
FACT_CHECK_PROVIDER=duckduckgo
COMPLIANCE_MODE=standard
TIMEZONE=US/Eastern
```

### 3. Start the Application

#### Option 1: Standalone Streamlit (Recommended for GitHub Deployment)

```bash
# Start the standalone Streamlit application
streamlit run ui_standalone.py --server.port 8501
```

Access the application at: http://localhost:8501

#### Option 2: Full Stack (FastAPI + Streamlit) - For Development

Terminal 1 - Start FastAPI backend:
```bash
uvicorn app.api:app --host 127.0.0.1 --port 5000 --reload
```

Terminal 2 - Start original Streamlit frontend:
```bash
streamlit run ui.py --server.port 8501
```

Access the application at: http://localhost:8501
API documentation at: http://localhost:5000/docs

## Dependencies File

The `requirements_github.txt` file contains all necessary dependencies:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
streamlit==1.28.1
pydantic==2.5.0
python-dotenv==1.0.0
openai==1.3.0
langchain==0.0.339
langchain-openai==0.0.2
langgraph==0.0.26
requests==2.31.0
duckduckgo-search==3.9.6
wikipedia-api==0.6.0
numpy==1.24.4
scikit-learn==1.3.2
tiktoken==0.5.1
pytest==7.4.3
```

## Directory Structure

Ensure your GitHub repository has this structure:

```
content-workflow-agent/
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── config.py
│   ├── graph.py
│   ├── models.py
│   ├── prompts.py
│   └── tools/
│       ├── __init__.py
│       ├── compliance.py
│       ├── embeddings.py
│       ├── factcheck.py
│       ├── hashtag_optimizer.py
│       ├── schedule.py
│       └── search.py
├── static/
│   └── index.html
├── tests/
├── .env.example
├── .gitignore
├── GITHUB_DEPLOYMENT.md
├── README.md
├── requirements_github.txt
├── setup.py
├── ui.py
└── ui_standalone.py
```

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for content generation | None | Yes |
| `FACT_CHECK_PROVIDER` | Search provider (duckduckgo/wikipedia) | duckduckgo | No |
| `COMPLIANCE_MODE` | Compliance level (standard/strict) | standard | No |
| `TIMEZONE` | Default timezone for scheduling | US/Eastern | No |

### Compliance Modes

- **standard**: Basic content safety checks
- **strict**: Enhanced compliance for regulated industries

### Search Providers

- **duckduckgo**: Free web search (default)
- **wikipedia**: Encyclopedic content
- **serpapi**: Premium search (requires API key)

## Usage

### Standalone Streamlit Interface

1. Run `streamlit run ui_standalone.py --server.port 8501`
2. Enter your blog content in the text area (minimum 100 characters)
3. Optionally add a topic hint for better targeting
4. Click "Generate Content Plan" 
5. Review generated posts for Twitter, LinkedIn, and Instagram
6. Check fact-checking results and compliance status
7. Review optimal posting times with rationales
8. Download results as text file or copy to clipboard

**Features:**
- Direct workflow integration (no API needed)
- Real-time progress indicators
- Complete content generation pipeline
- Professional styling and layout
- Downloadable results

### API Usage (if running FastAPI)

```bash
# Health check
curl http://localhost:5000/health

# Generate content plan
curl -X POST http://localhost:5000/v1/plan \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your blog content here...",
    "topic_hint": "Optional topic hint"
  }'
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
pytest tests/
```

### Code Formatting

```bash
# Install formatting tools
pip install black ruff

# Format code
black .
ruff check . --fix
```

## Troubleshooting

### Common Issues

**1. OpenAI API Errors**
- Verify your API key is correct in `.env`
- Check your OpenAI account has sufficient credits
- Ensure API key has proper permissions

**2. Import Errors**
- Activate your virtual environment
- Run the setup script: `python setup.py`
- Or manually install: `pip install -r requirements_github.txt`
- Check Python version compatibility (3.11+)

**3. Streamlit Connection Issues**
- Use 127.0.0.1 instead of localhost if experiencing connection issues
- Check firewall settings
- Try different port: `streamlit run ui_standalone.py --server.port 8502`
- For GitHub deployment, always use `ui_standalone.py` for best experience

**4. Search Provider Failures**
- DuckDuckGo search may have rate limits
- Try switching to Wikipedia: set `FACT_CHECK_PROVIDER=wikipedia` in `.env`
- Check internet connection for search functionality

### Performance Optimization

**For better performance:**
- Use SSD storage for faster file operations
- Ensure stable internet connection for API calls
- Consider upgrading OpenAI plan for higher rate limits
- Monitor system resources during processing

## Security Notes

- Never commit your `.env` file to GitHub
- Keep your OpenAI API key secure and rotate regularly
- Use environment variables for all sensitive configuration
- Review generated content before publishing

## Production Deployment

For production deployment, consider:
- Using a process manager like PM2 or systemd
- Setting up reverse proxy with nginx
- Implementing proper logging and monitoring
- Using containerization with Docker
- Setting up CI/CD pipelines

## Support

For issues and questions:
1. Check this documentation first
2. Review error logs for specific issues
3. Test with minimal examples
4. Check OpenAI API status and limits

## License

[Include your license information here]