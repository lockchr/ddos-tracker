# DDOS Attack Tracker

A real-time web application that visualizes simulated DDOS (Distributed Denial of Service) attacks on an interactive world map.

## Features

- 🗺️ **Interactive World Map**: Visualizes attack origins and destinations with animated lines
- 📊 **Real-time Statistics**: Displays attack counts by severity level
- 🎯 **Top Sources & Targets**: Shows the most active attack sources and targets
- 📝 **Attack Log**: Lists recent attacks with detailed information
- 🔴 **Color-coded Severity**: Different colors for Critical, High, Medium, and Low severity attacks
- ⏸️ **Pause/Resume**: Control to pause and resume attack generation
- 🗑️ **Clear Map**: Remove all attack visualizations from the map

## Attack Types Simulated

- SYN Flood
- UDP Flood
- HTTP Flood
- DNS Amplification
- NTP Amplification

## Technology Stack

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **Map Library**: Leaflet.js
- **Visualization**: Real-time attack animations

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

- The application automatically generates simulated DDOS attacks every 3 seconds
- Attacks are displayed as colored lines connecting origin and destination cities
- Click on destination markers to see detailed attack information
- Use the **Pause** button to stop generating new attacks
- Use the **Clear Map** button to remove all visualizations
- View statistics and recent attacks in the side panel

## Project Structure

```
DDOS Tracker/
├── app.py              # Flask backend application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── templates/
│   └── index.html     # Frontend HTML template
└── static/
    ├── style.css      # Styling and themes
    └── script.js      # Map visualization and interactions
```

## Features Explained

### Statistics Dashboard
- **Total Attacks**: Count of all detected attacks
- **Severity Breakdown**: Attacks categorized by Critical, High, Medium, and Low

### World Map
- **Attack Lines**: Animated lines showing attack paths
- **Color Coding**: Lines/markers colored by severity
- **Interactive Markers**: Click for detailed attack information

### Side Panel
- **Top Attack Sources**: Cities originating the most attacks
- **Top Attack Targets**: Cities receiving the most attacks
- **Attack Types**: Distribution of different attack methods
- **Recent Attacks**: Chronological log of the latest attacks

## Notes

This is a **simulation tool** for educational and demonstration purposes. It generates realistic-looking DDOS attack data but does not represent actual network traffic or real attacks.

## Future Enhancements

- Database integration for persistent storage
- User authentication and multiple users
- Export attack data to CSV/JSON
- Historical attack analysis and trends
- Custom attack simulation parameters
- Integration with real threat intelligence feeds

## License

This project is for educational purposes.
