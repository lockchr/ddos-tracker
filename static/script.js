// Initialize the map with bounds
const map = L.map('map', {
    center: [20, 0],
    zoom: 2,
    minZoom: 2,
    maxBounds: [[-90, -180], [90, 180]],
    maxBoundsViscosity: 1,
    worldCopyJump: false
}).setView([20, 0], 2);

// Add dark theme tile layer
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
}).addTo(map);

// Initialize heatmap layer
let heatmapData = [];
let heatLayer = L.heatLayer([], {
    radius: 25,
    blur: 35,
    maxZoom: 10,
    max: 1,
    gradient: {
        0: '#0000ff',
        0.5: '#00ff00',
        0.7: '#ffff00',
        0.9: '#ff0000',
        1: '#ff00ff'
    }
}).addTo(map);

// State management
let attacks = [];
let attackLines = [];
let attackMarkers = [];
let pulsingMarkers = [];
let isRunning = true;
let updateInterval;
let socket = null;
let totalAttacksCount = 0; // Total attack counter (unlimited)

// Severity colors
const severityColors = {
    'Critical': '#ff4757',
    'High': '#ff6348',
    'Medium': '#ffa502',
    'Low': '#26de81'
};

// Initialize the application
async function init() {
    await loadInitialAttacks();
    updateStats();
    updateTopLists();
    updateRecentAttacks();
    // Don't start auto update - WebSocket handles it now
}

// Load initial attacks from the server
async function loadInitialAttacks() {
    try {
        const response = await fetch('/api/attacks');
        attacks = await response.json();
        totalAttacksCount = attacks.length; // Initialize counter
        for (const attack of attacks) {
            drawAttackOnMap(attack);
        }
    } catch (error) {
        console.error('Error loading initial attacks:', error);
    }
}

// Draw an attack on the map
function drawAttackOnMap(attack) {
    const origin = attack.origin;
    const destination = attack.destination;
    const color = severityColors[attack.severity];
    
    // Create animated line from origin to destination with arrow decorator
    const line = L.polyline(
        [[origin.lat, origin.lon], [destination.lat, destination.lon]],
        {
            color: color,
            weight: 3,
            opacity: 0.8,
            className: 'attack-line',
            dashArray: '10, 5'
        }
    ).addTo(map);
    
    // Add arrow decorator to show direction
    const decorator = L.polylineDecorator(line, {
        patterns: [
            {
                offset: '50%',
                repeat: 0,
                symbol: L.Symbol.arrowHead({
                    pixelSize: 12,
                    polygon: false,
                    pathOptions: {
                        stroke: true,
                        weight: 2,
                        color: color,
                        opacity: 0.8
                    }
                })
            }
        ]
    }).addTo(map);
    
    // Add markers with better visibility
    const originMarker = L.circleMarker([origin.lat, origin.lon], {
        radius: 4,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
    }).addTo(map);
    
    const destinationMarker = L.circleMarker([destination.lat, destination.lon], {
        radius: 8,
        fillColor: color,
        color: '#fff',
        weight: 3,
        opacity: 1,
        fillOpacity: 1
    }).addTo(map);
    
    // Add popup to destination marker
    const popupContent = `
        <div class="popup-content">
            <div class="popup-title">${attack.attack_type}</div>
            <div class="severity-badge ${attack.severity}">${attack.severity}</div>
            <div><strong>From:</strong> ${origin.name}, ${origin.country}</div>
            ${attack.source_ip ? `<div><strong>Source IP:</strong> ${attack.source_ip}</div>` : ''}
            <div><strong>To:</strong> ${destination.name}, ${destination.country}</div>
            ${attack.destination_ip ? `<div><strong>Target IP:</strong> ${attack.destination_ip}</div>` : ''}
            <div><strong>Bandwidth:</strong> ${attack.bandwidth}</div>
            <div><strong>Packets:</strong> ${attack.packets.toLocaleString()}</div>
        </div>
    `;
    
    destinationMarker.bindPopup(popupContent, {
        closeButton: true,
        autoClose: true,
        closeOnClick: true
    });
    
    // Store references for cleanup
    attackLines.push({line, decorator});
    attackMarkers.push(originMarker, destinationMarker);
    
    // Severity-based fade duration - Extended durations for better visibility
    // Critical: 45 seconds, High: 35 seconds, Medium: 25 seconds, Low: 15 seconds
    const fadeDurations = {
        'Critical': 45000,
        'High': 35000,
        'Medium': 25000,
        'Low': 15000
    };
    const totalDuration = fadeDurations[attack.severity] || 25000;
    const fadeSteps = Math.floor(totalDuration / 600); // Number of 600ms intervals
    const opacityDecrement = 0.8 / fadeSteps; // How much to decrease opacity each step
    
    // Track if popup is open
    let popupOpen = false;
    
    // Listen for popup open/close events
    destinationMarker.on('popupopen', () => {
        popupOpen = true;
    });
    
    destinationMarker.on('popupclose', () => {
        popupOpen = false;
    });
    
    // Gradually fade out line and markers over time
    let opacity = 0.8;
    let stepCount = 0;
    const fadeInterval = setInterval(() => {
        // Pause fading if popup is open
        if (popupOpen) {
            return; // Skip this interval, don't increment stepCount or decrease opacity
        }
        
        stepCount++;
        opacity -= opacityDecrement;
        
        if (opacity <= 0 || !map.hasLayer(line) || stepCount >= fadeSteps) {
            clearInterval(fadeInterval);
            // Check if popup is open - if so, reset and continue fading
            if (popupOpen) {
                // Reset opacity and keep fading when popup closes
                opacity = 0.8;
                stepCount = 0;
            } else {
                // Remove layers when popup is not open
                if (map.hasLayer(line)) map.removeLayer(line);
                if (map.hasLayer(decorator)) map.removeLayer(decorator);
                if (map.hasLayer(originMarker)) map.removeLayer(originMarker);
                if (map.hasLayer(destinationMarker)) map.removeLayer(destinationMarker);
            }
        } else {
            // Fade line
            line.setStyle({ opacity: opacity });
            
            // Fade arrow decorator
            decorator.setPatterns([{
                offset: '50%',
                repeat: 0,
                symbol: L.Symbol.arrowHead({
                    pixelSize: 12,
                    polygon: false,
                    pathOptions: {
                        stroke: true,
                        weight: 2,
                        color: color,
                        opacity: opacity
                    }
                })
            }]);
            
            // Fade both markers
            originMarker.setStyle({ 
                opacity: opacity,
                fillOpacity: opacity * 0.9
            });
            destinationMarker.setStyle({ 
                opacity: opacity,
                fillOpacity: opacity
            });
        }
    }, 600);
    
    // Keep only recent 30 attacks visible
    if (attackLines.length > 30) {
        const oldAttack = attackLines.shift();
        if (oldAttack.line && map.hasLayer(oldAttack.line)) map.removeLayer(oldAttack.line);
        if (oldAttack.decorator && map.hasLayer(oldAttack.decorator)) map.removeLayer(oldAttack.decorator);
    }
    if (attackMarkers.length > 60) {
        const oldMarker = attackMarkers.shift();
        if (oldMarker && map.hasLayer(oldMarker)) map.removeLayer(oldMarker);
    }
}

// Generate and display a new attack
async function generateNewAttack() {
    try {
        const response = await fetch('/api/generate_attack');
        const attack = await response.json();
        attacks.push(attack);
        
        // Keep only recent attacks in memory
        if (attacks.length > 100) {
            attacks.shift();
        }
        
        drawAttackOnMap(attack);
        updateStats();
        updateTopLists();
        updateRecentAttacks();
    } catch (error) {
        console.error('Error generating attack:', error);
    }
}

// Update statistics display
function updateStats() {
    updateStatsWithData(attacks);
}

// Update statistics display with specific data
function updateStatsWithData(data) {
    const severityCounts = {
        'Critical': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0
    };
    
    for (const attack of data) {
        severityCounts[attack.severity]++;
    }
    
    // Use totalAttacksCount for unlimited tracking
    document.getElementById('total-attacks').textContent = totalAttacksCount.toLocaleString();
    document.getElementById('critical-count').textContent = severityCounts['Critical'];
    document.getElementById('high-count').textContent = severityCounts['High'];
    document.getElementById('medium-count').textContent = severityCounts['Medium'];
    document.getElementById('low-count').textContent = severityCounts['Low'];
}

// Update top sources and targets lists
async function updateTopLists() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // Update top sources
        const sourcesContainer = document.getElementById('top-sources');
        sourcesContainer.innerHTML = '';
        for (const source of stats.top_sources) {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <span class="list-item-name">${source.name}</span>
                <span class="list-item-value">${source.count}</span>
            `;
            sourcesContainer.appendChild(item);
        }
        
        // Update top targets
        const targetsContainer = document.getElementById('top-targets');
        targetsContainer.innerHTML = '';
        for (const target of stats.top_targets) {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <span class="list-item-name">${target.name}</span>
                <span class="list-item-value">${target.count}</span>
            `;
            targetsContainer.appendChild(item);
        }
        
        // Update attack types
        const typesContainer = document.getElementById('attack-types');
        typesContainer.innerHTML = '';
        for (const [type, count] of Object.entries(stats.by_type)) {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <span class="list-item-name">${type}</span>
                <span class="list-item-value">${count}</span>
            `;
            typesContainer.appendChild(item);
        }
    } catch (error) {
        console.error('Error updating top lists:', error);
    }
}

// Update recent attacks log
function updateRecentAttacks() {
    updateRecentAttacksWithData(attacks);
}

// Update recent attacks log with specific data
function updateRecentAttacksWithData(data) {
    const logContainer = document.getElementById('recent-attacks');
    logContainer.innerHTML = '';
    
    // Show last 10 attacks
    const recentAttacks = data.slice(-10).reverse();
    
    for (const attack of recentAttacks) {
        const item = document.createElement('div');
        item.className = `attack-item severity-${attack.severity}`;
        item.style.cursor = 'pointer';
        item.title = 'Click to view full details';
        
        const timestamp = new Date(attack.timestamp).toLocaleTimeString();
        
        item.innerHTML = `
            <div class="attack-header">
                <span class="attack-type">${attack.attack_type}</span>
                <span class="attack-severity ${attack.severity}">${attack.severity}</span>
            </div>
            <div class="attack-details">
                <div class="attack-route">
                    🔴 ${attack.origin.name} → 🎯 ${attack.destination.name}
                </div>
                <div>📊 ${attack.bandwidth} | 📦 ${attack.packets.toLocaleString()} packets</div>
                <div>🕐 ${timestamp}</div>
            </div>
        `;
        
        // Add click handler to show modal
        item.addEventListener('click', () => {
            showAttackModal(attack);
        });
        
        logContainer.appendChild(item);
    }
}

// Start automatic attack generation
function startAutoUpdate() {
    updateInterval = setInterval(() => {
        if (isRunning) {
            generateNewAttack();
        }
    }, 3000); // Generate new attack every 3 seconds
}

// Toggle attack generation
document.getElementById('toggle-attacks').addEventListener('click', function() {
    isRunning = !isRunning;
    this.textContent = isRunning ? '⏸️ Pause' : '▶️ Resume';
    this.classList.toggle('btn-primary');
    this.classList.toggle('btn-secondary');
});

// Clear map
document.getElementById('clear-map').addEventListener('click', function() {
    // Remove all lines and markers
    for (const line of attackLines) {
        map.removeLayer(line);
    }
    for (const marker of attackMarkers) {
        map.removeLayer(marker);
    }
    
    attackLines = [];
    attackMarkers = [];
    
    // Clear attacks array but keep generating new ones
    attacks = [];
    
    updateStats();
    updateTopLists();
    updateRecentAttacks();
});

// Chart instances
let frequencyChart, severityChart, typesChart;
let topAttackTypesChart, topSourcesChart, topTargetsChart, commonSeverityChart, countriesChart;
let threatHistoryChart;

// Initialize charts
function initCharts() {
    // Attack Frequency Chart
    const freqCtx = document.getElementById('attackFrequencyChart').getContext('2d');
    frequencyChart = new Chart(freqCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Number of Attacks',
                data: [],
                borderColor: '#00d9ff',
                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const timeLabel = frequencyChart.data.labels[index];
                    const attackCount = frequencyChart.data.datasets[0].data[index];
                    showChartDetailsModal('Time Period', timeLabel, attackCount, 'time');
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#e0e0e0' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Attacks: ${context.parsed.y} attacks detected in this time interval`;
                        },
                        footer: function() {
                            return 'Click to view details';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Attacks',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time Period',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });

    // Severity Distribution Chart
    const sevCtx = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(sevCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ff4757',
                    '#ff6348',
                    '#ffa502',
                    '#26de81'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const severity = severityChart.data.labels[index];
                    const count = severityChart.data.datasets[0].data[index];
                    showChartDetailsModal('Severity', severity, count, 'severity');
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} attacks (${percentage}% of total)`;
                        },
                        footer: function() {
                            return 'Click to view details';
                        }
                    }
                }
            }
        }
    });

    // Attack Types Chart
    const typesCtx = document.getElementById('attackTypesChart').getContext('2d');
    typesChart = new Chart(typesCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Number of Attacks',
                data: [],
                backgroundColor: '#00d9ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const attackType = typesChart.data.labels[index];
                    const count = typesChart.data.datasets[0].data[index];
                    showChartDetailsModal('Attack Type', attackType, count, 'attack_type');
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} attacks of type "${context.label}"`;
                        },
                        footer: function() {
                            return 'Click to view details';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Attacks',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Attack Type',
                        color: '#e0e0e0'
                    },
                    ticks: { 
                        color: '#e0e0e0',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });

    // Initial chart updates
    updateCharts();
    
    // Update charts every 10 seconds
    setInterval(updateCharts, 10000);
    
    // Initialize common attacks charts
    initCommonAttacksCharts();
    
    // Initialize threat intel charts
    initThreatIntelCharts();
}

// Initialize Most Common Attacks charts
function initCommonAttacksCharts() {
    // Top Attack Types Chart
    const topTypesCtx = document.getElementById('topAttackTypesChart').getContext('2d');
    topAttackTypesChart = new Chart(topTypesCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Attacks',
                data: [],
                backgroundColor: [
                    '#ff4757', '#ff6348', '#ffa502', '#26de81',
                    '#00d9ff', '#5f27cd', '#ff9ff3', '#48dbfb',
                    '#1dd1a1', '#feca57'
                ]
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed.x} total attacks recorded`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Attacks',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Attack Type',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });

    // Top Sources Chart
    const topSrcCtx = document.getElementById('topSourcesChart').getContext('2d');
    topSourcesChart = new Chart(topSrcCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ff4757', '#ff6348', '#ffa502', '#26de81',
                    '#00d9ff', '#5f27cd', '#ff9ff3', '#48dbfb'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0', font: { size: 10 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} attacks originated (${percentage}% of total)`;
                        }
                    }
                }
            }
        }
    });

    // Top Targets Chart
    const topTgtCtx = document.getElementById('topTargetsChart').getContext('2d');
    topTargetsChart = new Chart(topTgtCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#00d9ff', '#5f27cd', '#ff9ff3', '#48dbfb',
                    '#ff4757', '#ff6348', '#ffa502', '#26de81'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0', font: { size: 10 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} attacks targeted (${percentage}% of total)`;
                        }
                    }
                }
            }
        }
    });

    // Common Severity Chart
    const commSevCtx = document.getElementById('commonSeverityChart').getContext('2d');
    commonSeverityChart = new Chart(commSevCtx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: ['#ff4757', '#ff6348', '#ffa502', '#26de81']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#e0e0e0' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label} Severity: ${context.parsed} attacks (${percentage}% of total)`;
                        }
                    }
                }
            }
        }
    });

    // Countries Chart
    const countriesCtx = document.getElementById('countriesChart').getContext('2d');
    countriesChart = new Chart(countriesCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Attacks',
                data: [],
                backgroundColor: '#00d9ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed.y} attacks (source + target)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Attacks',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Country',
                        color: '#e0e0e0'
                    },
                    ticks: { 
                        color: '#e0e0e0',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });

    // Initial update
    updateCommonAttacksCharts();
    
    // Update every 10 seconds
    setInterval(updateCommonAttacksCharts, 10000);
}

// Update Most Common Attacks charts
async function updateCommonAttacksCharts() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // Update attack types
        const typeEntries = Object.entries(stats.by_type).sort((a, b) => b[1] - a[1]).slice(0, 10);
        topAttackTypesChart.data.labels = typeEntries.map(e => e[0]);
        topAttackTypesChart.data.datasets[0].data = typeEntries.map(e => e[1]);
        topAttackTypesChart.update();
        
        // Update top sources
        topSourcesChart.data.labels = stats.top_sources.slice(0, 8).map(s => s.name);
        topSourcesChart.data.datasets[0].data = stats.top_sources.slice(0, 8).map(s => s.count);
        topSourcesChart.update();
        
        // Update top targets
        topTargetsChart.data.labels = stats.top_targets.slice(0, 8).map(t => t.name);
        topTargetsChart.data.datasets[0].data = stats.top_targets.slice(0, 8).map(t => t.count);
        topTargetsChart.update();
        
        // Update severity
        const sevData = stats.by_severity;
        commonSeverityChart.data.labels = Object.keys(sevData);
        commonSeverityChart.data.datasets[0].data = Object.values(sevData);
        commonSeverityChart.update();
        
        // Update countries
        const countries = {};
        for (const source of stats.top_sources) {
            if (source.country) {
                countries[source.country] = (countries[source.country] || 0) + source.count;
            }
        }
        for (const target of stats.top_targets) {
            if (target.country) {
                countries[target.country] = (countries[target.country] || 0) + target.count;
            }
        }
        const countryEntries = Object.entries(countries).sort((a, b) => b[1] - a[1]).slice(0, 10);
        countriesChart.data.labels = countryEntries.map(e => e[0]);
        countriesChart.data.datasets[0].data = countryEntries.map(e => e[1]);
        countriesChart.update();
    } catch (error) {
        console.error('Error updating common attacks charts:', error);
    }
}

// Update all charts
async function updateCharts(timeRange = null) {
    try {
        // Get time range from selector if not provided
        if (!timeRange) {
            const selector = document.getElementById('timeRangeSelector');
            timeRange = selector ? selector.value : '60';
        }
        
        // Update frequency chart
        const freqResponse = await fetch(`/api/trends/frequency?range=${timeRange}`);
        const freqData = await freqResponse.json();
        frequencyChart.data.labels = freqData.labels;
        frequencyChart.data.datasets[0].data = freqData.data;
        frequencyChart.update();

        // Update severity chart
        const sevResponse = await fetch('/api/trends/severity');
        const sevData = await sevResponse.json();
        severityChart.data.labels = sevData.labels;
        severityChart.data.datasets[0].data = sevData.data;
        severityChart.update();

        // Update types chart
        const typesResponse = await fetch('/api/trends/types');
        const typesData = await typesResponse.json();
        typesChart.data.labels = typesData.labels;
        typesChart.data.datasets[0].data = typesData.data;
        typesChart.update();
    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

// Initialize time range selector
function initTimeRangeSelector() {
    const selector = document.getElementById('timeRangeSelector');
    if (selector) {
        selector.addEventListener('change', (e) => {
            updateCharts(e.target.value);
        });
    }
}

// Tab switching functionality
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    for (const button of tabButtons) {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Remove active class from all buttons and panes
            for (const btn of document.querySelectorAll('.tab-button')) {
                btn.classList.remove('active');
            }
            for (const pane of document.querySelectorAll('.tab-pane')) {
                pane.classList.remove('active');
            }
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // Resize map when map tab is shown
            if (tabName === 'map') {
                setTimeout(() => {
                    map.invalidateSize();
                }, 100);
            }
        });
    }
}

// Initialize WebSocket connection
function initWebSocket() {
    socket = io();
    
    socket.on('connect', () => {
        // Connected
    });
    
    socket.on('connection_response', (data) => {
        // Connection confirmed
    });
    
    socket.on('new_attack', (attack) => {
        attacks.push(attack);
        totalAttacksCount++; // Increment unlimited counter
        
        if (attacks.length > 100) {
            attacks.shift();
        }
        
        drawAttackOnMap(attack);
        createPulsingMarker(attack);
        updateHeatmap(attack);
        addAttackToTicker(attack);
        updateStats();
        updateTopLists();
        updateRecentAttacks();
    });
    
    socket.on('disconnect', () => {
        // Disconnected
    });
}

// Create pulsing marker for attack intensity
function createPulsingMarker(attack) {
    const destination = attack.destination;
    const color = severityColors[attack.severity];
    
    // Determine size based on severity
    const sizeMap = {
        'Critical': 50,
        'High': 40,
        'Medium': 30,
        'Low': 20
    };
    const maxSize = sizeMap[attack.severity] || 30;
    
    // Create pulsing circle
    const pulseCircle = L.circle([destination.lat, destination.lon], {
        color: color,
        fillColor: color,
        fillOpacity: 0.3,
        weight: 2,
        radius: 1000
    }).addTo(map);
    
    pulsingMarkers.push(pulseCircle);
    
    // Animate the pulse
    let currentRadius = 1000;
    let growing = true;
    let opacity = 0.6;
    
    const pulseInterval = setInterval(() => {
        if (growing) {
            currentRadius += 2000;
            opacity -= 0.02;
            if (currentRadius >= maxSize * 1000) {
                growing = false;
            }
        } else {
            currentRadius -= 2000;
            opacity += 0.02;
            if (currentRadius <= 1000) {
                growing = true;
            }
        }
        
        pulseCircle.setRadius(currentRadius);
        pulseCircle.setStyle({ fillOpacity: Math.max(0.1, opacity) });
    }, 50);
    
    // Remove after 5 seconds
    setTimeout(() => {
        clearInterval(pulseInterval);
        if (map.hasLayer(pulseCircle)) {
            map.removeLayer(pulseCircle);
        }
        const index = pulsingMarkers.indexOf(pulseCircle);
        if (index > -1) {
            pulsingMarkers.splice(index, 1);
        }
    }, 5000);
}

// Update heatmap with new attack
function updateHeatmap(attack) {
    try {
        const severityWeight = {
            'Critical': 1,
            'High': 0.7,
            'Medium': 0.4,
            'Low': 0.2
        };
        
        const weight = severityWeight[attack.severity] || 0.5;
        
        // Add both origin and destination to heatmap
        heatmapData.push(
            [attack.origin.lat, attack.origin.lon, weight],
            [attack.destination.lat, attack.destination.lon, weight]
        );
        
        // Keep only recent 200 points for performance
        if (heatmapData.length > 200) {
            heatmapData = heatmapData.slice(-200);
        }
        
        // Only update heatmap if map tab is visible to avoid canvas errors
        const mapTab = document.getElementById('map-tab');
        if (mapTab?.classList.contains('active')) {
            heatLayer.setLatLngs(heatmapData);
        }
    } catch (error) {
        // Silently ignore heatmap errors
    }
}

// Filter and Search State
let activeFilters = {
    search: '',
    severity: '',
    attackType: '',
    country: '',
    dateStart: '',
    dateEnd: ''
};

// Initialize filter and search functionality
function initFilters() {
    const searchInput = document.getElementById('search-input');
    const clearSearch = document.getElementById('clear-search');
    const applyFilters = document.getElementById('apply-filters');
    const clearFilters = document.getElementById('clear-filters');
    const filterSeverity = document.getElementById('filter-severity');
    const filterAttackType = document.getElementById('filter-attack-type');
    const filterCountry = document.getElementById('filter-country');
    const filterDateStart = document.getElementById('filter-date-start');
    const filterDateEnd = document.getElementById('filter-date-end');
    
    // Populate country filter with unique countries
    populateCountryFilter();
    
    // Search input with debounce
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            activeFilters.search = e.target.value.toLowerCase();
            applyActiveFilters();
        }, 300);
    });
    
    // Clear search button
    clearSearch.addEventListener('click', () => {
        searchInput.value = '';
        activeFilters.search = '';
        applyActiveFilters();
    });
    
    // Apply filters button
    applyFilters.addEventListener('click', () => {
        activeFilters.severity = filterSeverity.value;
        activeFilters.attackType = filterAttackType.value;
        activeFilters.country = filterCountry.value;
        activeFilters.dateStart = filterDateStart.value;
        activeFilters.dateEnd = filterDateEnd.value;
        applyActiveFilters();
    });
    
    // Clear all filters button
    clearFilters.addEventListener('click', () => {
        searchInput.value = '';
        filterSeverity.value = '';
        filterAttackType.value = '';
        filterCountry.value = '';
        filterDateStart.value = '';
        filterDateEnd.value = '';
        activeFilters = {
            search: '',
            severity: '',
            attackType: '',
            country: '',
            dateStart: '',
            dateEnd: ''
        };
        applyActiveFilters();
    });
}

// Populate country filter dropdown
async function populateCountryFilter() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        const countries = new Set();
        for (const source of stats.top_sources) {
            countries.add(source.country);
        }
        for (const target of stats.top_targets) {
            countries.add(target.country);
        }
        
        const countryFilter = document.getElementById('filter-country');
        const sortedCountries = Array.from(countries).sort((a, b) => a.localeCompare(b));
        
        for (const country of sortedCountries) {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = country;
            countryFilter.appendChild(option);
        }
    } catch (error) {
        console.error('Error populating country filter:', error);
    }
}

// Apply active filters to visible data
function applyActiveFilters() {
    let filteredAttacks = [...attacks];
    let filterCount = 0;
    
    // Apply search filter
    if (activeFilters.search) {
        filterCount++;
        filteredAttacks = filteredAttacks.filter(attack => 
            attack.source_ip?.toLowerCase().includes(activeFilters.search) ||
            attack.destination_ip?.toLowerCase().includes(activeFilters.search) ||
            attack.origin.country.toLowerCase().includes(activeFilters.search) ||
            attack.destination.country.toLowerCase().includes(activeFilters.search) ||
            attack.attack_type.toLowerCase().includes(activeFilters.search)
        );
    }
    
    // Apply severity filter
    if (activeFilters.severity) {
        filterCount++;
        filteredAttacks = filteredAttacks.filter(attack => 
            attack.severity.toLowerCase() === activeFilters.severity.toLowerCase()
        );
    }
    
    // Apply attack type filter
    if (activeFilters.attackType) {
        filterCount++;
        filteredAttacks = filteredAttacks.filter(attack => 
            attack.attack_type === activeFilters.attackType
        );
    }
    
    // Apply country filter
    if (activeFilters.country) {
        filterCount++;
        filteredAttacks = filteredAttacks.filter(attack => 
            attack.origin.country === activeFilters.country ||
            attack.destination.country === activeFilters.country
        );
    }
    
    // Apply date range filters
    if (activeFilters.dateStart || activeFilters.dateEnd) {
        filterCount++;
        filteredAttacks = filteredAttacks.filter(attack => {
            const attackDate = new Date(attack.timestamp).toISOString().split('T')[0];
            const startMatch = !activeFilters.dateStart || attackDate >= activeFilters.dateStart;
            const endMatch = !activeFilters.dateEnd || attackDate <= activeFilters.dateEnd;
            return startMatch && endMatch;
        });
    }
    
    // Update filter status badge
    const filterStatus = document.getElementById('active-filters');
    if (filterCount === 0) {
        filterStatus.textContent = 'No filters active';
        filterStatus.style.background = 'rgba(0, 217, 255, 0.1)';
    } else {
        filterStatus.textContent = `${filterCount} filter${filterCount > 1 ? 's' : ''} active - ${filteredAttacks.length} results`;
        filterStatus.style.background = 'rgba(255, 193, 7, 0.2)';
    }
    
    // Clear and redraw map with filtered attacks
    clearMapLayers();
    for (const attack of filteredAttacks) {
        drawAttackOnMap(attack);
    }
    
    // Update displays with filtered data (DON'T modify the attacks array!)
    updateStatsWithData(filteredAttacks);
    updateRecentAttacksWithData(filteredAttacks);
}

// Clear map layers
function clearMapLayers() {
    for (const line of attackLines) {
        map.removeLayer(line);
    }
    for (const marker of attackMarkers) {
        map.removeLayer(marker);
    }
    attackLines = [];
    attackMarkers = [];
}

// Dark mode toggle functionality
function initDarkMode() {
    const toggleButton = document.getElementById('toggle-dark-mode');
    const body = document.body;
    
    // Check for saved preference
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'enabled') {
        body.classList.add('dark-mode');
        toggleButton.textContent = '☀️ Light Mode';
    }
    
    // Toggle dark mode
    toggleButton.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        
        if (body.classList.contains('dark-mode')) {
            toggleButton.textContent = '☀️ Light Mode';
            localStorage.setItem('darkMode', 'enabled');
            
            // Switch to dark map tiles
            map.eachLayer((layer) => {
                if (layer instanceof L.TileLayer) {
                    map.removeLayer(layer);
                }
            });
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap &copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 19
            }).addTo(map);
        } else {
            toggleButton.textContent = '🌙 Dark Mode';
            localStorage.setItem('darkMode', 'disabled');
            
            // Switch to light map tiles
            map.eachLayer((layer) => {
                if (layer instanceof L.TileLayer) {
                    map.removeLayer(layer);
                }
            });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            }).addTo(map);
        }
    });
}

// Attack Details Modal
let currentAttackData = null;

function initAttackModal() {
    const modal = document.getElementById('attack-modal');
    const closeBtn = document.getElementById('modal-close');
    const copyBtn = document.getElementById('copy-details');
    const filterBtn = document.getElementById('filter-similar');
    
    // Close modal
    closeBtn.addEventListener('click', closeAttackModal);
    
    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeAttackModal();
        }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeAttackModal();
        }
    });
    
    // Copy details
    copyBtn.addEventListener('click', () => {
        if (currentAttackData) {
            const details = `
DDOS ATTACK DETAILS
Attack Type: ${currentAttackData.attack_type}
Severity: ${currentAttackData.severity}
Timestamp: ${new Date(currentAttackData.timestamp).toLocaleString()}
Bandwidth: ${currentAttackData.bandwidth}
Packets: ${currentAttackData.packets.toLocaleString()}
Duration: ${currentAttackData.duration}

SOURCE
------
IP: ${currentAttackData.source_ip || 'N/A'}
Location: ${currentAttackData.origin.name}, ${currentAttackData.origin.country}
Coordinates: ${currentAttackData.origin.lat}, ${currentAttackData.origin.lon}

TARGET
------
IP: ${currentAttackData.destination_ip || 'N/A'}
Location: ${currentAttackData.destination.name}, ${currentAttackData.destination.country}
Coordinates: ${currentAttackData.destination.lat}, ${currentAttackData.destination.lon}
            `.trim();
            
            navigator.clipboard.writeText(details).then(() => {
                copyBtn.textContent = '✓ Copied!';
                setTimeout(() => {
                    copyBtn.textContent = '📋 Copy Details';
                }, 2000);
            });
        }
    });
    
    // Filter similar attacks
    filterBtn.addEventListener('click', () => {
        if (currentAttackData) {
            const filterType = document.getElementById('filter-attack-type');
            filterType.value = currentAttackData.attack_type;
            activeFilters.attackType = currentAttackData.attack_type;
            applyActiveFilters();
            closeAttackModal();
        }
    });
}

function showAttackModal(attack) {
    currentAttackData = attack;
    const modal = document.getElementById('attack-modal');
    
    // Populate attack information
    document.getElementById('modal-attack-type').textContent = attack.attack_type;
    document.getElementById('modal-severity').textContent = attack.severity;
    document.getElementById('modal-severity').className = `detail-value attack-severity ${attack.severity}`;
    document.getElementById('modal-timestamp').textContent = new Date(attack.timestamp).toLocaleString();
    document.getElementById('modal-bandwidth').textContent = attack.bandwidth;
    document.getElementById('modal-packets').textContent = attack.packets.toLocaleString();
    document.getElementById('modal-duration').textContent = attack.duration;
    
    // Populate source information
    document.getElementById('modal-source-ip').textContent = attack.source_ip || 'N/A';
    document.getElementById('modal-source-location').textContent = attack.origin.name;
    document.getElementById('modal-source-country').textContent = attack.origin.country;
    document.getElementById('modal-source-coords').textContent = `${attack.origin.lat.toFixed(4)}, ${attack.origin.lon.toFixed(4)}`;
    
    // Populate target information
    document.getElementById('modal-target-ip').textContent = attack.destination_ip || 'N/A';
    document.getElementById('modal-target-location').textContent = attack.destination.name;
    document.getElementById('modal-target-country').textContent = attack.destination.country;
    document.getElementById('modal-target-coords').textContent = `${attack.destination.lat.toFixed(4)}, ${attack.destination.lon.toFixed(4)}`;
    
    // Show modal
    modal.classList.add('active');
}

function closeAttackModal() {
    const modal = document.getElementById('attack-modal');
    modal.classList.remove('active');
    currentAttackData = null;
}

// Live Attack Feed Ticker
let tickerAttacks = [];
const MAX_TICKER_ITEMS = 20;

function initTicker() {
    const tickerContent = document.getElementById('ticker-content');
    
    // Initialize with some placeholder text
    if (tickerContent) {
        tickerContent.innerHTML = '<div class="ticker-item">Initializing live attack feed...</div>';
    }
}

function addAttackToTicker(attack) {
    const tickerContent = document.getElementById('ticker-content');
    if (!tickerContent) return;
    
    // Add to ticker attacks array
    tickerAttacks.push(attack);
    
    // Keep only the most recent attacks
    if (tickerAttacks.length > MAX_TICKER_ITEMS) {
        tickerAttacks.shift();
    }
    
    // Recreate ticker content with duplicates for seamless loop
    updateTickerContent();
}

function updateTickerContent() {
    const tickerContent = document.getElementById('ticker-content');
    if (!tickerContent || tickerAttacks.length === 0) return;
    
    // Create ticker items HTML
    let itemsHTML = '';
    
    for (const attack of tickerAttacks) {
        const time = new Date(attack.timestamp).toLocaleTimeString();
        const item = `
            <div class="ticker-item severity-${attack.severity}" data-attack-id="${attack.timestamp}">
                <span class="ticker-attack-type">${attack.attack_type}</span>
                <span class="ticker-route">${attack.origin.country}</span>
                <span class="ticker-arrow">→</span>
                <span class="ticker-route">${attack.destination.country}</span>
                <span class="ticker-time">${time}</span>
            </div>
        `;
        itemsHTML += item;
    }
    
    // Duplicate content for seamless infinite scroll - no animation pause
    tickerContent.innerHTML = itemsHTML + itemsHTML;
    
    // Add click handlers to all ticker items
    const tickerItems = tickerContent.querySelectorAll('.ticker-item');
    for (const item of tickerItems) {
        item.addEventListener('click', () => {
            const attackTimestamp = item.dataset.attackId;
            const attack = tickerAttacks.find(a => a.timestamp === attackTimestamp);
            if (attack) {
                showAttackModal(attack);
            }
        });
    }
}

// Update threat level display
async function updateThreatLevel() {
    try {
        const response = await fetch('/api/threat/score');
        const data = await response.json();
        
        // Update preview in stats bar
        const previewElement = document.getElementById('threat-level-preview');
        if (previewElement) {
            previewElement.textContent = `${data.level} (${data.score})`;
            previewElement.className = `stat-value threat-${data.level.toLowerCase()}`;
        }
        
        // Update full threat dashboard if on threat tab
        const scoreElement = document.getElementById('threat-score');
        const levelElement = document.getElementById('threat-level');
        const trendElement = document.getElementById('threat-trend');
        
        if (scoreElement) scoreElement.textContent = data.score;
        if (levelElement) {
            levelElement.textContent = data.level;
            levelElement.className = `threat-level threat-${data.level.toLowerCase()}`;
        }
        
        if (trendElement) {
            const trendIcons = {
                'escalating': '↗',
                'de-escalating': '↘',
                'stable': '→'
            };
            const icon = trendIcons[data.trend] || '→';
            const trendText = data.trend.charAt(0).toUpperCase() + data.trend.slice(1);
            trendElement.innerHTML = `<span class="trend-icon">${icon}</span> ${trendText}`;
            trendElement.className = `trend-value trend-${data.trend}`;
        }
        
        // Update threat factors
        if (data.factors) {
            const factors = ['frequency', 'severity', 'diversity', 'concentration'];
            for (const factor of factors) {
                const valueEl = document.getElementById(`factor-${factor}`);
                const barEl = document.getElementById(`factor-${factor}-bar`);
                if (valueEl && data.factors[factor] !== undefined) {
                    valueEl.textContent = data.factors[factor].toFixed(1);
                }
                if (barEl && data.factors[factor] !== undefined) {
                    // Calculate percentage (out of max possible for each factor)
                    const maxValues = { frequency: 30, severity: 40, diversity: 15, concentration: 15 };
                    const percentage = (data.factors[factor] / maxValues[factor]) * 100;
                    barEl.style.width = `${Math.min(100, percentage)}%`;
                }
            }
        }
        
        // Update gauge
        const gaugeFill = document.getElementById('gauge-fill');
        const gaugePointer = document.getElementById('gauge-pointer');
        if (gaugeFill && gaugePointer) {
            // Gauge is 180 degrees (half circle), max dash array is ~251
            const percentage = data.score / 100;
            const dashOffset = 251.2 - (251.2 * percentage);
            gaugeFill.style.strokeDashoffset = dashOffset;
            
            // Update pointer position (rotate around arc)
            const angle = 180 * percentage; // 0 to 180 degrees
            const radians = (angle - 90) * (Math.PI / 180); // -90 to start from left
            const radius = 80;
            const centerX = 100;
            const centerY = 100;
            const x = centerX + radius * Math.cos(radians);
            const y = centerY + radius * Math.sin(radians);
            gaugePointer.setAttribute('cx', x);
            gaugePointer.setAttribute('cy', y);
        }
        
    } catch (error) {
        console.error('Error updating threat level:', error);
    }
}

// Initialize Threat Intel Charts
function initThreatIntelCharts() {
    // Threat History Chart
    const threatHistCtx = document.getElementById('threatHistoryChart').getContext('2d');
    threatHistoryChart = new Chart(threatHistCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Threat Score',
                data: [],
                borderColor: '#ff4757',
                backgroundColor: 'rgba(255, 71, 87, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const score = context.parsed.y;
                            const level = score >= 80 ? 'Critical' : 
                                        score >= 60 ? 'High' : 
                                        score >= 35 ? 'Medium' : 'Low';
                            return `Threat Score: ${score} (${level})`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Threat Score',
                        color: '#e0e0e0'
                    },
                    ticks: { color: '#e0e0e0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time',
                        color: '#e0e0e0'
                    },
                    ticks: { 
                        color: '#e0e0e0',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });
    
    // Initial update
    updateThreatHistoryChart();
    
    // Update every 10 seconds
    setInterval(updateThreatHistoryChart, 10000);
}

// Update threat history chart
async function updateThreatHistoryChart() {
    try {
        const response = await fetch('/api/threat/history');
        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            // Get last 30 readings
            const history = data.history.slice(-30);
            
            // Extract times and scores
            const labels = history.map(h => {
                const date = new Date(h.timestamp);
                return date.toLocaleTimeString();
            });
            const scores = history.map(h => h.score);
            
            // Update chart
            threatHistoryChart.data.labels = labels;
            threatHistoryChart.data.datasets[0].data = scores;
            threatHistoryChart.update();
        }
    } catch (error) {
        console.error('Error updating threat history chart:', error);
    }
}

// Show chart details modal
async function showChartDetailsModal(category, value, count, filterType) {
    // Create or get the modal
    let modal = document.getElementById('chart-details-modal');
    if (!modal) {
        // Create modal HTML
        modal = document.createElement('div');
        modal.id = 'chart-details-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="chart-modal-title"></h2>
                    <button class="modal-close" id="chart-modal-close">×</button>
                </div>
                <div class="modal-body">
                    <div class="chart-modal-info">
                        <div class="chart-modal-stat">
                            <span class="chart-modal-label">Total Attacks:</span>
                            <span class="chart-modal-value" id="chart-modal-count"></span>
                        </div>
                        <div class="chart-modal-stat">
                            <span class="chart-modal-label">Filter:</span>
                            <span class="chart-modal-value" id="chart-modal-filter"></span>
                        </div>
                    </div>
                    <div class="chart-modal-attacks" id="chart-modal-attacks">
                        <p>Loading attacks...</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="chart-modal-apply-filter">Apply Filter to Map</button>
                    <button class="btn btn-primary" id="chart-modal-close-btn">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add event listeners
        document.getElementById('chart-modal-close').addEventListener('click', () => {
            modal.classList.remove('active');
        });
        
        document.getElementById('chart-modal-close-btn').addEventListener('click', () => {
            modal.classList.remove('active');
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                modal.classList.remove('active');
            }
        });
    }
    
    // Update modal content
    document.getElementById('chart-modal-title').textContent = `${category}: ${value}`;
    document.getElementById('chart-modal-count').textContent = count.toLocaleString();
    document.getElementById('chart-modal-filter').textContent = value;
    
    // Fetch matching attacks from database
    const attacksContainer = document.getElementById('chart-modal-attacks');
    attacksContainer.innerHTML = '<p class="loading">Loading attack details...</p>';
    
    try {
        let url = '/api/filter?limit=20';
        if (filterType === 'severity') {
            url += `&severity=${encodeURIComponent(value)}`;
        } else if (filterType === 'attack_type') {
            url += `&type=${encodeURIComponent(value)}`;
        } else if (filterType === 'country') {
            url += `&country=${encodeURIComponent(value)}`;
        }
        
        const response = await fetch(url);
        const matchingAttacks = await response.json();
        
        if (matchingAttacks.length === 0) {
            attacksContainer.innerHTML = '<p class="no-data">No attacks found for this filter.</p>';
        } else {
            // Display first 20 attacks
            let html = '<div class="chart-modal-attack-list">';
            for (const attack of matchingAttacks.slice(0, 20)) {
                const time = new Date(attack.timestamp).toLocaleString();
                html += `
                    <div class="chart-modal-attack-item severity-${attack.severity}" data-attack='${JSON.stringify(attack).replaceAll("'", "&apos;")}'>
                        <div class="attack-item-header">
                            <span class="attack-type">${attack.attack_type}</span>
                            <span class="attack-severity ${attack.severity}">${attack.severity}</span>
                        </div>
                        <div class="attack-item-details">
                            <div>🔴 ${attack.source_country || attack.origin?.country || 'Unknown'} → 🎯 ${attack.dest_country || attack.destination?.country || 'Unknown'}</div>
                            <div>📊 ${attack.bandwidth} | 📦 ${attack.packets.toLocaleString()} packets</div>
                            <div>🕐 ${time}</div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
            
            if (matchingAttacks.length > 20) {
                html += `<p class="chart-modal-note">Showing 20 of ${matchingAttacks.length} total attacks</p>`;
            }
            
            attacksContainer.innerHTML = html;
            
            // Add click handlers to show full details
            const items = attacksContainer.querySelectorAll('.chart-modal-attack-item');
            for (const item of items) {
                item.style.cursor = 'pointer';
                item.title = 'Click to view full details';
                item.addEventListener('click', () => {
                    const attackData = JSON.parse(item.dataset.attack);
                    // Convert database format to display format if needed
                    if (attackData.source_country && !attackData.origin) {
                        attackData.origin = {
                            name: attackData.source_city || attackData.source_country,
                            country: attackData.source_country,
                            lat: 0,
                            lon: 0
                        };
                        attackData.destination = {
                            name: attackData.dest_city || attackData.dest_country,
                            country: attackData.dest_country,
                            lat: 0,
                            lon: 0
                        };
                    }
                    modal.classList.remove('active');
                    showAttackModal(attackData);
                });
            }
        }
    } catch (error) {
        console.error('Error fetching chart details:', error);
        attacksContainer.innerHTML = '<p class="error">Error loading attack details. Please try again.</p>';
    }
    
    // Set up apply filter button
    const applyFilterBtn = document.getElementById('chart-modal-apply-filter');
    applyFilterBtn.onclick = () => {
        // Apply the filter
        if (filterType === 'severity') {
            document.getElementById('filter-severity').value = value;
            activeFilters.severity = value;
        } else if (filterType === 'attack_type') {
            document.getElementById('filter-attack-type').value = value;
            activeFilters.attackType = value;
        } else if (filterType === 'country') {
            document.getElementById('filter-country').value = value;
            activeFilters.country = value;
        }
        
        applyActiveFilters();
        modal.classList.remove('active');
        
        // Switch to map tab
        const mapButton = document.querySelector('[data-tab="map"]');
        if (mapButton) {
            mapButton.click();
        }
    };
    
    // Show modal
    modal.classList.add('active');
}

// Update countries at risk
async function updateCountriesAtRisk() {
    try {
        const response = await fetch('/api/threat/countries');
        const countries = await response.json();
        
        const listElement = document.getElementById('country-risk-list');
        if (!listElement) return;
        
        if (countries.length === 0) {
            listElement.innerHTML = '<div class="risk-item loading">No data yet. Attacks are being generated...</div>';
            return;
        }
        
        listElement.innerHTML = '';
        const topCountries = countries.slice(0, 10);
        
        for (let i = 0; i < topCountries.length; i++) {
            const country = topCountries[i];
            const item = document.createElement('div');
            item.className = `risk-item rank-${i + 1}`;
            
            item.innerHTML = `
                <div class="risk-country">
                    <span class="risk-country-name">${country.country}</span>
                    <span class="risk-country-stats">${country.attack_count} attacks | ${country.critical_count} critical</span>
                </div>
                <div class="risk-score">
                    <span class="risk-score-value">${country.score}</span>
                    <span class="risk-attacks">${country.attack_count} total</span>
                </div>
            `;
            listElement.appendChild(item);
        }
    } catch (error) {
        console.error('Error updating countries at risk:', error);
        const listElement = document.getElementById('country-risk-list');
        if (listElement) {
            listElement.innerHTML = '<div class="risk-item loading">Error loading data...</div>';
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    init();
    initCharts();
    initTabs();
    initTimeRangeSelector();
    initWebSocket();
    initFilters();
    initDarkMode();
    initAttackModal();
    initTicker();
    
    // Update threat level immediately and every 5 seconds
    updateThreatLevel();
    updateCountriesAtRisk();
    setInterval(updateThreatLevel, 5000);
    setInterval(updateCountriesAtRisk, 10000);
});
