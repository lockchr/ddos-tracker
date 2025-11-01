"""Threat scoring service for DDOS Tracker.

This module provides threat score calculation functionality,
isolated from the main application for better maintainability.
"""

from typing import List, Dict, Any
from collections import Counter, deque
from datetime import datetime, timezone
import time
import logging
from models.types import ThreatScoreResult, ThreatScoreFactors

logger = logging.getLogger(__name__)


class ThreatScoringService:
    """Service for calculating threat scores from attack data."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize threat scoring service.
        
        Args:
            config: Configuration dictionary with threat_scoring section
        """
        self.config = config
        self.score_precision = config.get('score_precision', 1)
        self.analysis_window = config.get('analysis_window_seconds', 300)
        self.threshold_critical = config.get('thresholds', {}).get('critical', 80)
        self.threshold_high = config.get('thresholds', {}).get('high', 60)
        self.threshold_medium = config.get('thresholds', {}).get('medium', 35)
        self.escalation_threshold = config.get('trend_detection', {}).get('escalation_threshold', 10)
        self.de_escalation_threshold = config.get('trend_detection', {}).get('de_escalation_threshold', 10)
    
    def calculate_score(
        self,
        recent_attacks: List[Dict[str, Any]],
        score_history: deque
    ) -> ThreatScoreResult:
        """Calculate overall threat score based on recent attacks.
        
        Args:
            recent_attacks: List of recent attack dictionaries
            score_history: Historical scores for trend analysis
            
        Returns:
            Complete threat score result with all factors
        """
        try:
            if not recent_attacks:
                return self._empty_score_result()
            
            # Filter attacks within analysis window
            recent_time = time.time() - self.analysis_window
            filtered_attacks = [
                a for a in recent_attacks
                if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')).timestamp() > recent_time
            ]
            
            if not filtered_attacks:
                filtered_attacks = list(recent_attacks)[-10:]  # At least last 10
            
            if not filtered_attacks:
                return self._empty_score_result()
            
            # Calculate individual factors
            frequency_score = self._calculate_frequency(filtered_attacks)
            severity_score = self._calculate_severity(filtered_attacks)
            diversity_score = self._calculate_diversity(filtered_attacks)
            concentration_score = self._calculate_concentration(filtered_attacks)
            
            # Total score
            total_score = min(100, int(
                frequency_score + severity_score + diversity_score + concentration_score
            ))
            
            # Classify and determine trend
            threat_level = self._classify_level(total_score)
            trend = self._calculate_trend(score_history, total_score)
            
            result: ThreatScoreResult = {
                'score': total_score,
                'level': threat_level,
                'trend': trend,
                'factors': self._round_factors({
                    'frequency': frequency_score,
                    'severity': severity_score,
                    'diversity': diversity_score,
                    'concentration': concentration_score
                }),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Calculated threat score: {total_score} ({threat_level})")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating threat score: {e}")
            return self._empty_score_result()
    
    def _calculate_frequency(self, attacks: List[Dict[str, Any]]) -> float:
        """Calculate frequency score (0-30 points)."""
        return min(30.0, len(attacks) * 1.5)
    
    def _calculate_severity(self, attacks: List[Dict[str, Any]]) -> float:
        """Calculate severity distribution score (0-40 points)."""
        severity_weights = {'Critical': 10, 'High': 6, 'Medium': 3, 'Low': 1}
        severity_sum = sum(
            severity_weights.get(a.get('severity', 'Low'), 1)
            for a in attacks
        )
        return min(40.0, severity_sum / 2.0)
    
    def _calculate_diversity(self, attacks: List[Dict[str, Any]]) -> float:
        """Calculate attack type diversity score (0-15 points)."""
        unique_types = len({a.get('attack_type', 'Unknown') for a in attacks})
        return min(15.0, unique_types * 2.0)
    
    def _calculate_concentration(self, attacks: List[Dict[str, Any]]) -> float:
        """Calculate geographic concentration score (0-15 points)."""
        target_countries = [
            a['destination']['country'] 
            for a in attacks 
            if 'destination' in a
        ]
        
        if not target_countries:
            return 0.0
        
        top_target_count = Counter(target_countries).most_common(1)[0][1]
        return min(15.0, (top_target_count / len(target_countries)) * 20.0)
    
    def _classify_level(self, score: int) -> str:
        """Classify threat level based on score."""
        if score >= self.threshold_critical:
            return 'Critical'
        elif score >= self.threshold_high:
            return 'High'
        elif score >= self.threshold_medium:
            return 'Medium'
        else:
            return 'Low'
    
    def _calculate_trend(self, history: deque, current_score: int) -> str:
        """Calculate threat score trend."""
        if len(history) < 5:
            return 'stable'
        
        recent_scores = [record['score'] for record in list(history)[-5:]]
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        if current_score > avg_recent + self.escalation_threshold:
            return 'escalating'
        elif current_score < avg_recent - self.de_escalation_threshold:
            return 'de-escalating'
        else:
            return 'stable'
    
    def _round_factors(self, factors: Dict[str, float]) -> ThreatScoreFactors:
        """Round score factors to configured precision."""
        return {
            key: round(value, self.score_precision)
            for key, value in factors.items()
        }
    
    def _empty_score_result(self) -> ThreatScoreResult:
        """Return empty/zero score result."""
        return {
            'score': 0,
            'level': 'Low',
            'trend': 'stable',
            'factors': {
                'frequency': 0.0,
                'severity': 0.0,
                'diversity': 0.0,
                'concentration': 0.0
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
