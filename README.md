# 🛡️ DDOS Attack Tracker

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**A sophisticated real-time web application for visualizing and analyzing simulated DDOS attacks with advanced threat scoring and OSINT integration.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API](#-api-documentation) • [Configuration](#%EF%B8%8F-configuration)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
- [Configuration](#%EF%B8%8F-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

DDOS Attack Tracker is a comprehensive web application designed for educational and demonstration purposes. It simulates realistic DDOS attack scenarios, providing real-time visualization, intelligent threat scoring, and optional OSINT (Open Source Intelligence) integration for enhanced geolocation and threat analysis.

### Key Capabilities

- **Real-time Attack Visualization**: Interactive world map with animated attack paths
- **Intelligent Threat Scoring**: Dynamic scoring system analyzing attack patterns and trends
- **OSINT Integration**: Optional integration with Shodan, IP2Location, and AbuseIPDB
- **Advanced Analytics**: Comprehensive statistics, trend detection, and threat severity assessment
- **RESTful API**: Full-featured API for programmatic access and data export
- **Configurable Architecture**: YAML-based configuration with environment variable overrides
- **Rate Limiting & Security**: Built-in CORS protection and API rate limiting

---

## ✨ Features

### 🗺️ Interactive Visualization

- **World Map Display**: Leaflet.js-powered interactive map
- **Animated Attack Lines**: Real-time visualization of attack paths
- **Color-coded Severity**: Visual distinction between Critical, High, Medium, and Low threats
- **Interactive Markers**: Click for detailed attack information
- **Geographic Clustering**: Visual identification of attack hotspots

### 📊 Advanced Threat Scoring

- **Dynamic Threat Levels**: Real-time calculation based on multiple factors
- **Pattern Recognition**: Detection of attack bursts and sustained campaigns
- **Trend Analysis**: Automatic escalation/de-escalation detection
- **Historical Context**: Considers previous attacks from same sources
- **Geographic Analysis**: Evaluates source country reputation and patterns

#### Threat Score Components

| Factor | Weight | Description |
|--------|--------|-------------|
| Attack Type | 30% | Severity of attack method (DNS Amp, SYN Flood, etc.) |
| Geographic Origin | 20% | Source country reputation and typical threat profile |
| Attack Frequency | 20% | Rate and pattern of recent attacks |
| Target Diversity | 15% | Number of unique targets attacked |
| Attack Intensity | 15% | Volume and persistence of attack traffic |

### 🔍 OSINT Integration (Optional)

- **Shodan**: IP reputation and service information
- **IP2Location**: Enhanced geolocation accuracy
- **AbuseIPDB**: Historical abuse reports and confidence scores
- **Caching**: Intelligent caching to minimize API calls
- **Fallback Handling**: Graceful degradation when APIs unavailable

### 📈 Analytics Dashboard

- **Real-time Statistics**: Live attack counts by severity
- **Top Sources/Targets**: Most active attack origins and destinations
- **Attack Type Distribution**: Breakdown of attack methods
- **Trend Indicators**: Visual escalation/de-escalation alerts
- **Time-series Data**: Historical attack patterns

### 🔌 RESTful API

- **GET /api/attacks**: Retrieve attacks with filtering and pagination
- **GET /api/stats**: Comprehensive attack statistics
- **POST /api/attacks/clear**: Clear attack history
- **GET /api/export**: Export data in JSON/CSV formats
- **Rate Limiting**: Configurable limits per endpoint

### 🎮 User Controls

- ⏸️ **Pause/Resume**: Control attack generation
- 🗑️ **Clear Map**: Remove all visualizations
- 📊 **Export Data**: Download attack logs (JSON/CSV)
- ⚙️ **Live Configuration**: Adjust parameters on-the-fly

---

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core application language
- **Flask 3.0+**: Web framework
- **SQLite**: Persistent data storage
- **PyYAML**: Configuration management
- **Requests**: HTTP client for OSINT APIs

### Frontend
- **HTML5/CSS3**: Modern responsive design
- **JavaScript (Vanilla)**: Client-side interactivity
- **Leaflet.js**: Interactive mapping library
- **Fetch API**: Asynchronous data loading

### Security & Performance
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-Limiter**: API rate limiting
- **Environment Variables**: Secure configuration management

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ddos-tracker.git
cd ddos-tracker
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Application

Create or edit `config.yaml`:

```yaml
app:
  debug: false
  port: 5000
  host: 0.0.0.0

security:
  cors_origins:
    - http://localhost:3000
    - http://localhost:5000
  rate_limit:
    default_limits:
      - 200 per day
      - 50 per hour
```

### Step 5: (Optional) Configure OSINT APIs

For enhanced geolocation and threat intelligence:

```yaml
osint:
  shodan:
    api_key: "YOUR_SHODAN_API_KEY"
    enabled: true
  ip2location:
    api_key: "YOUR_IP2LOCATION_KEY"
    enabled: true
  abuseipdb:
    api_key: "YOUR_ABUSEIPDB_KEY"
    enabled: true
```

Or set environment variables:

```bash
export SHODAN_API_KEY="your_key_here"
export IP2LOCATION_API_KEY="your_key_here"
export ABUSEIPDB_API_KEY="your_key_here"
```

---

## ⚙️ Configuration

The application uses a hierarchical configuration system:

1. **config.yaml**: Default configuration file
2. **Environment Variables**: Override YAML settings (format: `DDOS_CONFIG_<SECTION>_<KEY>`)
3. **Runtime**: Some settings adjustable via API

### Key Configuration Sections

#### Application Settings

```yaml
app:
  debug: false          # Enable debug mode
  port: 5000           # Server port
  host: 0.0.0.0        # Bind address
```

#### Threat Scoring

```yaml
threat_scoring:
  thresholds:
    critical: 80       # Score >= 80 is Critical
    high: 60          # Score >= 60 is High
    medium: 35        # Score >= 35 is Medium
  trend_detection:
    escalation_threshold: 10    # Points for escalation
    de_escalation_threshold: 10
```

#### Attack Generation

```yaml
attack_generation:
  us_attack_probability: 0.3   # 30% of attacks target US
  burst_attack_probability: 0.1
  intensity:
    min: 0.3
    max: 2.0
```

### Environment Variable Overrides

```bash
# Override debug mode
export DDOS_CONFIG_APP_DEBUG=true

# Override rate limits
export DDOS_CONFIG_SECURITY_RATE_LIMIT_EXPORT_LIMIT="20 per hour"
```

---

## 🚀 Usage

### Starting the Application

```bash
python app.py
```

The server will start on `http://localhost:5000` (or configured port).

### Accessing the Dashboard

Open your web browser and navigate to:
```
http://localhost:5000
```

### Using the API

#### Get Recent Attacks

```bash
curl http://localhost:5000/api/attacks?limit=10&severity=critical
```

#### Get Statistics

```bash
curl http://localhost:5000/api/stats
```

#### Export Data

```bash
# JSON format
curl http://localhost:5000/api/export?format=json

# CSV format
curl http://localhost:5000/api/export?format=csv > attacks.csv
```

#### Clear Attack History

```bash
curl -X POST http://localhost:5000/api/attacks/clear
```

---

## 📚 API Documentation

### Endpoints

#### GET /api/attacks

Retrieve attack records with optional filtering.

**Query Parameters:**
- `limit` (int): Number of records to return (default: 100, max: 1000)
- `severity` (string): Filter by severity level (critical, high, medium, low)
- `attack_type` (string): Filter by attack type
- `source_country` (string): Filter by source country code
- `target_country` (string): Filter by target country code
- `min_threat_score` (int): Minimum threat score (0-100)
- `start_time` (ISO 8601): Start of time range
- `end_time` (ISO 8601): End of time range

**Response:**
```json
{
  "attacks": [...],
  "count": 100,
  "total": 500,
  "page": 1
}
```

#### GET /api/stats

Get comprehensive attack statistics.

**Response:**
```json
{
  "total_attacks": 500,
  "by_severity": {
    "critical": 50,
    "high": 150,
    "medium": 200,
    "low": 100
  },
  "by_type": {...},
  "top_sources": [...],
  "top_targets": [...],
  "average_threat_score": 45.5,
  "trends": {
    "escalating": 5,
    "stable": 10,
    "de_escalating": 3
  }
}
```

#### POST /api/attacks/clear

Clear all attack history from database.

**Response:**
```json
{
  "success": true,
  "message": "All attacks cleared"
}
```

#### GET /api/export

Export attack data in various formats.

**Query Parameters:**
- `format` (string): Export format (json, csv) - default: json
- `limit` (int): Number of records (max: 1000)
- Same filtering parameters as `/api/attacks`

---

## 📁 Project Structure

```
ddos-tracker/
├── app.py                      # Main Flask application
├── database.py                 # Database operations
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── .gitignore                 # Git ignore rules
│
├── models/
│   ├── __init__.py
│   └── types.py               # Data models and type definitions
│
├── services/
│   ├── __init__.py
│   ├── threat_scoring.py      # Threat scoring engine
│   └── osint.py               # OSINT integration services
│
├── utils/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   └── validators.py          # Input validation utilities
│
├── templates/
│   └── index.html             # Main web interface
│
├── static/
│   ├── style.css              # Application styling
│   └── script.js              # Frontend JavaScript
│
└── tests/
    ├── __init__.py
    └── test_config.py         # Configuration tests
```

---

## 🔒 Security

### Built-in Security Features

- **CORS Protection**: Configurable allowed origins
- **Rate Limiting**: API endpoint protection
- **Input Validation**: Comprehensive request validation
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Output sanitization

### Security Best Practices

1. **API Keys**: Store in environment variables, never commit to repository
2. **CORS**: Configure appropriate origins for production
3. **Rate Limits**: Adjust based on expected traffic
4. **HTTPS**: Use reverse proxy (nginx/Apache) with SSL in production
5. **Firewall**: Restrict access to necessary ports only

### Production Deployment

For production use:

```yaml
app:
  debug: false
  host: 127.0.0.1   # Use reverse proxy

security:
  cors_origins:
    - https://yourdomain.com
  rate_limit:
    default_limits:
      - 1000 per day
      - 100 per hour
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Commit changes: `git commit -am 'Add feature'`
6. Push to branch: `git push origin feature-name`
7. Submit a Pull Request

### Coding Standards

- Follow PEP 8 style guide
- Add docstrings to functions and classes
- Include type hints where appropriate
- Write tests for new features
- Update documentation as needed

---

## 📸 Screenshots

### Main Dashboard
The interactive map displays real-time attack visualization with color-coded severity indicators and geographic distribution.
<img width="1891" height="899" alt="image" src="https://github.com/user-attachments/assets/ab20557f-e829-4ce6-b22c-5d251249fb67" />

### Analytics Panel
Comprehensive statistics showing attack patterns, top sources/targets, and trend indicators.
<img width="1888" height="844" alt="image" src="https://github.com/user-attachments/assets/d5d31c99-e4ee-485c-8444-d7f416dcf9f1" />


---

## 🎯 Use Cases

### Educational
- Cybersecurity training and demonstrations
- Network security course material
- Attack pattern analysis learning

### Development
- Testing security monitoring systems
- Developing threat intelligence tools
- Building security dashboards

### Research
- Attack pattern analysis
- Geographic threat distribution studies
- Threat scoring algorithm development

---

## ⚠️ Disclaimer

This application is designed for **educational and demonstration purposes only**. It generates simulated attack data and does not represent actual network traffic or real DDOS attacks. The application should not be used for:

- Actual network monitoring in production environments
- Making security decisions based on simulated data
- Any malicious purposes

Always use proper security tools and consult with cybersecurity professionals for real-world threat assessment.

---

## 📝 License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2025 DDOS Attack Tracker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🌟 Acknowledgments

- **Leaflet.js**: Interactive mapping library
- **Flask**: Python web framework
- **Shodan, IP2Location, AbuseIPDB**: OSINT data providers
- **OpenStreetMap**: Map tile provider

---

## 📞 Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/yourusername/ddos-tracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ddos-tracker/discussions)
- **Documentation**: See `/docs` folder for additional guides

---

## 🗺️ Roadmap

### Planned Features

- [ ] WebSocket support for real-time updates
- [ ] Historical data analytics dashboard
- [ ] Machine learning-based anomaly detection
- [ ] Multi-user support with authentication
- [ ] Custom attack scenario generator
- [ ] Integration with additional OSINT sources
- [ ] Mobile-responsive dashboard
- [ ] Docker containerization
- [ ] Kubernetes deployment templates
- [ ] Advanced reporting and PDF export

---

<div align="center">

**Made with ❤️ for cybersecurity education**

⭐ Star this repo if you find it useful!

</div>
