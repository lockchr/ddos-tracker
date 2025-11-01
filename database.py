import sqlite3
from datetime import datetime
import json

class AttackDatabase:
    def __init__(self, db_path='attacks.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                source_city TEXT,
                source_country TEXT,
                source_lat REAL,
                source_lon REAL,
                dest_ip TEXT NOT NULL,
                dest_city TEXT,
                dest_country TEXT,
                dest_lat REAL,
                dest_lon REAL,
                attack_type TEXT,
                severity TEXT,
                packets INTEGER,
                bandwidth TEXT
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON attacks(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_severity ON attacks(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_country ON attacks(source_country)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dest_country ON attacks(dest_country)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attack_type ON attacks(attack_type)')
        
        conn.commit()
        conn.close()
        print("✓ Database initialized")
    
    def save_attack(self, attack):
        """Save an attack to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO attacks (
                timestamp, source_ip, source_city, source_country, source_lat, source_lon,
                dest_ip, dest_city, dest_country, dest_lat, dest_lon,
                attack_type, severity, packets, bandwidth
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            attack['timestamp'],
            attack.get('source_ip'),
            attack['origin']['name'],
            attack['origin']['country'],
            attack['origin']['lat'],
            attack['origin']['lon'],
            attack.get('destination_ip'),
            attack['destination']['name'],
            attack['destination']['country'],
            attack['destination']['lat'],
            attack['destination']['lon'],
            attack['attack_type'],
            attack['severity'],
            attack['packets'],
            attack['bandwidth']
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_attacks(self, limit=100):
        """Get recent attacks from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM attacks 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        attacks = []
        for row in rows:
            attacks.append({
                'id': row[0],
                'timestamp': row[1],
                'origin': {
                    'name': row[3],
                    'country': row[4],
                    'lat': row[5],
                    'lon': row[6]
                },
                'destination': {
                    'name': row[8],
                    'country': row[9],
                    'lat': row[10],
                    'lon': row[11]
                },
                'source_ip': row[2],
                'destination_ip': row[7],
                'attack_type': row[12],
                'severity': row[13],
                'packets': row[14],
                'bandwidth': row[15],
                'real_data': True
            })
        
        return attacks
    
    def get_filtered_attacks(self, country=None, severity=None, attack_type=None, limit=100):
        """Get filtered attacks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM attacks WHERE 1=1'
        params = []
        
        if country:
            query += ' AND (source_country = ? OR dest_country = ?)'
            params.extend([country, country])
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        if attack_type:
            query += ' AND attack_type = ?'
            params.append(attack_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        attacks = []
        for row in rows:
            attacks.append({
                'id': row[0],
                'timestamp': row[1],
                'origin': {
                    'name': row[3],
                    'country': row[4],
                    'lat': row[5],
                    'lon': row[6]
                },
                'destination': {
                    'name': row[8],
                    'country': row[9],
                    'lat': row[10],
                    'lon': row[11]
                },
                'source_ip': row[2],
                'destination_ip': row[7],
                'attack_type': row[12],
                'severity': row[13],
                'packets': row[14],
                'bandwidth': row[15],
                'real_data': True
            })
        
        return attacks
    
    def get_stats(self):
        """Get attack statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total attacks
        cursor.execute('SELECT COUNT(*) FROM attacks')
        total = cursor.fetchone()[0]
        
        # By severity - ensure all severity levels are represented
        cursor.execute('SELECT severity, COUNT(*) FROM attacks GROUP BY severity')
        severity_results = cursor.fetchall()
        by_severity = {
            'Critical': 0,
            'High': 0,
            'Medium': 0,
            'Low': 0
        }
        for severity, count in severity_results:
            if severity in by_severity:
                by_severity[severity] = count
        
        # By type
        cursor.execute('SELECT attack_type, COUNT(*) FROM attacks GROUP BY attack_type ORDER BY COUNT(*) DESC')
        by_type = dict(cursor.fetchall())
        
        # Top source locations (cities)
        cursor.execute('''
            SELECT source_city, source_country, COUNT(*) as count 
            FROM attacks 
            GROUP BY source_city, source_country 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_sources = [{'name': row[0], 'country': row[1], 'count': row[2]} for row in cursor.fetchall()]
        
        # Top target locations (cities)
        cursor.execute('''
            SELECT dest_city, dest_country, COUNT(*) as count 
            FROM attacks 
            GROUP BY dest_city, dest_country 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_targets = [{'name': row[0], 'country': row[1], 'count': row[2]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_attacks': total,
            'by_severity': by_severity,
            'by_type': by_type,
            'top_sources': top_sources,
            'top_targets': top_targets
        }
    
    def export_to_dict(self, limit=None):
        """Export attacks as list of dicts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if limit:
            cursor.execute('SELECT * FROM attacks ORDER BY timestamp DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM attacks ORDER BY timestamp DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        attacks = []
        for row in rows:
            attacks.append({
                'id': row[0],
                'timestamp': row[1],
                'source_ip': row[2],
                'source_city': row[3],
                'source_country': row[4],
                'source_lat': row[5],
                'source_lon': row[6],
                'destination_ip': row[7],
                'destination_city': row[8],
                'destination_country': row[9],
                'destination_lat': row[10],
                'destination_lon': row[11],
                'attack_type': row[12],
                'severity': row[13],
                'packets': row[14],
                'bandwidth': row[15]
            })
        
        return attacks
