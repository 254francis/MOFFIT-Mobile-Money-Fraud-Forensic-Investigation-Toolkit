import pytest
import pandas as pd
from moffit.detection.pattern_detector import FraudPatternDetector

def test_rapid_drain():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1, 2, 3, 4],
        'sender_id': ['A', 'A', 'A', 'A'],
        'receiver_id': ['B', 'C', 'D', 'E'],
        'amount': [200, 300, 400, 50],
        'sender_balance_before': [1000, 800, 500, 100],
        'sender_balance_after': [800, 500, 100, 50]
    })
    findings = detector.rapid_drain(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'rapid_drain'
    assert findings[0]['account_id'] == 'A'
    assert findings[0]['confidence'] == 0.90

def test_round_trip():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1, 5],
        'sender_id': ['A', 'B'],
        'receiver_id': ['B', 'A'],
        'amount': [1000, 980],  # Within 5%
        'sender_balance_before': [1000, 1000],
        'sender_balance_after': [0, 20]
    })
    findings = detector.round_trip(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'round_trip'
    assert findings[0]['account_id'] == 'A'
    assert findings[0]['confidence'] == 0.85

def test_fan_out():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1, 2, 3, 4, 5, 6],
        'sender_id': ['A']*6,
        'receiver_id': ['B', 'C', 'D', 'E', 'F', 'G'],
        'amount': [10]*6,
        'sender_balance_before': [100, 90, 80, 70, 60, 50],
        'sender_balance_after': [90, 80, 70, 60, 50, 40]
    })
    findings = detector.fan_out(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'fan_out'
    assert findings[0]['account_id'] == 'A'
    assert findings[0]['confidence'] == 0.75

def test_fan_in():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1, 2, 3, 4, 5, 6],
        'sender_id': ['B', 'C', 'D', 'E', 'F', 'G'],
        'receiver_id': ['A']*6,
        'amount': [10]*6,
        'sender_balance_before': [10]*6,
        'sender_balance_after': [0]*6
    })
    findings = detector.fan_in(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'fan_in'
    assert findings[0]['account_id'] == 'A'
    assert findings[0]['confidence'] == 0.70

def test_dormant_activation():
    detector = FraudPatternDetector()
    # Need global median to be calculated correctly
    # Let's say median is 100.
    df = pd.DataFrame({
        'step': [1, 2, 3, 4, 5],
        'sender_id': ['A', 'A', 'B', 'C', 'D'],
        'receiver_id': ['B', 'C', 'A', 'D', 'A'],
        'amount': [10, 20, 100, 100, 300], # Global median = 100. Threshold = 200.
        'sender_balance_before': [100, 90, 100, 100, 300],
        'sender_balance_after': [90, 70, 0, 0, 0]
    })
    # D sends 300 to A. D has 0 prior txns. 300 > 200.
    findings = detector.dormant_activation(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'dormant_activation'
    assert findings[0]['account_id'] == 'D'
    assert findings[0]['confidence'] == 0.80

def test_balance_inconsistency():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1],
        'sender_id': ['A'],
        'receiver_id': ['B'],
        'amount': [100],
        'sender_balance_before': [1000],
        'sender_balance_after': [800] # should be 900
    })
    findings = detector.balance_inconsistency(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'balance_inconsistency'
    assert findings[0]['account_id'] == 'A'
    assert findings[0]['confidence'] == 1.0

def test_analyze():
    detector = FraudPatternDetector()
    df = pd.DataFrame({
        'step': [1],
        'sender_id': ['A'],
        'receiver_id': ['B'],
        'amount': [100],
        'sender_balance_before': [1000],
        'sender_balance_after': [800] # triggers balance inconsistency
    })
    findings = detector.analyze(df)
    assert len(findings) == 1
    assert findings[0]['pattern'] == 'balance_inconsistency'
