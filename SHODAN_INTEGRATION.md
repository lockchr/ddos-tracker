# Shodan OSINT Integration

## Overview

The DDOS Tracker now includes powerful OSINT (Open Source Intelligence) capabilities through Shodan API integration. This allows you to enrich IP address data with device intelligence, discover vulnerabilities, and search for potential threats.

## Features

### 1. IP Intelligence Lookup
Get detailed information about any IP address:
- Organization and ISP details
- Open ports and running services
- Known vulnerabilities (CVEs)
- Device type and operating system
- Hostnames and domains
- Last update timestamp

### 2. Threat Search
Search Shodan's database for potential threats:
- Search by port, country, product, or vulnerability
- Find exposed services and devices
- Identify vulnerable systems

### 3. API Status Monitoring
Check your Shodan API usage:
- Query credits remaining
- Scan credits available
- Account plan type

## Setup

### 1. Get a Shodan API Key

1. Sign up for a free account at [https://account.shodan.io/register](https://account.shodan.io/register)
2. Navigate to [https://account.shodan.io/](https://account.shodan.io/)
3. Copy your API key

**Free Plan Limits:**
- 100 query credits per month
- 1 scan credit per month
- Access to basic API features

**Paid Plans:** Offer more credits and advanced features

### 2. Configure the API Key

**Option A: Environment Variable (Recommended)**
```bash
# Linux/Mac
export DDOS_CONFIG_OSINT_SHODAN_API_KEY="your_api_key_here"
export DDOS_CONFIG_OSINT_SHODAN_ENABLED="true"

# Windows
set DDOS_CONFIG_OSINT_SHODAN_API_KEY=your_api_key_here
set DDOS_CONFIG_OSINT_SHODAN_ENABLED=true
```

**Option B: Configuration File**

Edit `config.yaml`:
```yaml
osint:
  shodan:
    enabled: true
    api_key: "your_api_key_here"
    cache_duration: 3600  # Cache results for 1 hour
    timeout: 10
    max_results: 10
```

### 3. Restart the Application

```bash
python app.py
```

You should see:
```
✓ Shodan OSINT integration enabled
```

## API Endpoints

### Check OSINT Status

**Endpoint:** `GET /api/osint/status`

**Response:**
```json
{
  "osint_enabled": true,
  "shodan_available": true,
  "shodan_credits": {
    "query_credits": 95,
    "scan_credits": 1,
    "plan": "free"
  }
}
```

### IP Intelligence Lookup

**Endpoint:** `GET /api/osint/ip/<ip_address>`

**Rate Limit:** 20 requests per hour

**Example:**
```bash
curl http://localhost:5000/api/osint/ip/8.8.8.8
```

**Response:**
```json
{
  "ip": "8.8.8.8",
  "enriched": true,
  "shodan": {
    "ip": "8.8.8.8",
    "organization": "Google LLC",
    "isp": "Google LLC",
    "asn": "AS15169",
    "country": "United States",
    "city": "Mountain View",
    "hostnames": ["dns.google"],
    "domains": ["google.com"],
    "ports": [53, 443],
    "vulns": [],
    "os": null,
    "tags": ["dns"],
    "last_update": "2024-01-15T10:30:00.000000",
    "services": [
      {
        "port": 53,
        "transport": "udp",
        "product": "DNS",
        "version": "",
        "banner": "..."
      }
    ]
  }
}
```

### Threat Search

**Endpoint:** `GET /api/osint/search?q=<query>`

**Rate Limit:** 10 requests per hour

**Example Queries:**

1. **SSH servers in China:**
```bash
curl "http://localhost:5000/api/osint/search?q=port:22+country:CN"
```

2. **Apache servers in Russia:**
```bash
curl "http://localhost:5000/api/osint/search?q=product:\"Apache+httpd\"+country:RU"
```

3. **Log4j vulnerability:**
```bash
curl "http://localhost:5000/api/osint/search?q=vuln:CVE-2021-44228"
```

**Response:**
```json
{
  "query": "port:22 country:CN",
  "result_count": 10,
  "results": [
    {
      "ip": "xxx.xxx.xxx.xxx",
      "port": 22,
      "organization": "Example ISP",
      "hostnames": ["example.com"],
      "location": {
        "city": "Beijing",
        "country_name": "China"
      },
      "banner": "SSH-2.0-OpenSSH_7.4"
    }
  ]
}
```

## Use Cases

### 1. Attack Source Analysis

When investigating an attack, lookup the source IP to understand:
- What services the attacker is running
- Known vulnerabilities on their system
- Their infrastructure provider
- Other exposed services

### 2. Threat Hunting

Search for specific threats:
```bash
# Find MongoDB instances without authentication
curl "http://localhost:5000/api/osint/search?q=product:MongoDB+-authentication"

# Find systems with specific CVEs
curl "http://localhost:5000/api/osint/search?q=vuln:CVE-2021-44228"

# Find exposed RDP servers
curl "http://localhost:5000/api/osint/search?q=port:3389+country:US"
```

### 3. Infrastructure Mapping

Identify exposed infrastructure in your organization:
```bash
# Find your organization's exposed services
curl "http://localhost:5000/api/osint/search?q=org:\"Your+Organization\""
```

## Rate Limiting

To protect your Shodan API credits, the application implements strict rate limits:

- **IP Lookup:** 20 requests/hour
- **Threat Search:** 10 requests/hour

These limits are independent of the application's general rate limits.

## Caching

Results are cached for 1 hour (configurable) to:
- Reduce API credit usage
- Improve response times
- Stay within rate limits

Modify `cache_duration` in `config.yaml` to adjust:
```yaml
osint:
  shodan:
    cache_duration: 7200  # 2 hours
```

## Security Considerations

1. **API Key Protection:**
   - Never commit API keys to version control
   - Use environment variables in production
   - Rotate keys regularly

2. **Rate Limiting:**
   - Monitor credit usage via `/api/osint/status`
   - Implement additional limits if needed
   - Consider upgrading plan for production use

3. **Data Privacy:**
   - Shodan queries are logged by Shodan
   - Be mindful of what IPs you query
   - Consider privacy implications

## Troubleshooting

### Integration Not Available

**Error:** `Shodan OSINT integration not available`

**Solutions:**
1. Verify API key is set correctly
2. Check `enabled: true` in config
3. Restart the application
4. Check logs for initialization errors

### API Credit Exhausted

**Error:** 401 Unauthorized from Shodan

**Solutions:**
1. Check credit balance: `GET /api/osint/status`
2. Wait for monthly reset (free plan)
3. Upgrade to paid plan
4. Reduce query frequency

### Timeout Errors

**Error:** Request timeout

**Solutions:**
1. Increase timeout in config:
```yaml
osint:
  shodan:
    timeout: 20  # Increase to 20 seconds
```
2. Check network connectivity
3. Verify Shodan API status

## Advanced Configuration

```yaml
osint:
  shodan:
    enabled: true
    api_key: "YOUR_API_KEY"
    cache_duration: 3600      # 1 hour cache
    timeout: 15               # 15 second timeout
    max_results: 20           # Return up to 20 search results
```

## Future Enhancements

Planned features:
- Automatic enrichment of attack source IPs
- Vulnerability correlation with attacks
- Threat intelligence dashboard
- Integration with additional OSINT sources (AbuseIPDB, VirusTotal)
- Automated threat hunting workflows

## Resources

- [Shodan Official Documentation](https://developer.shodan.io/)
- [Shodan Search Guide](https://www.shodan.io/search)
- [Shodan Query Examples](https://github.com/jakejarvis/awesome-shodan-queries)
- [Account Dashboard](https://account.shodan.io/)

## Support

For issues related to:
- **Shodan API:** Contact Shodan support or check their documentation
- **Integration bugs:** Report via `/reportbug` in the application
- **Feature requests:** Submit through project repository

## License & Attribution

This integration uses the Shodan API. Please review Shodan's:
- [Terms of Service](https://account.shodan.io/legal)
- [Privacy Policy](https://account.shodan.io/privacy)
- [API License](https://developer.shodan.io/license)

The DDOS Tracker is an independent project and is not affiliated with Shodan.
