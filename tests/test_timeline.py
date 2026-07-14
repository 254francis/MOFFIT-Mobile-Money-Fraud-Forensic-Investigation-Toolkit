import pytest
import pandas as pd
from moffit.timeline.reconstructor import TimelineReconstructor, TimelineEvent

def test_build_account_timeline():
    df = pd.DataFrame({
        'step': [1, 2, 3],
        'tx_type': ['CASH_IN', 'TRANSFER', 'CASH_OUT'],
        'amount': [1000.0, 500.0, 200.0],
        'sender_id': ['A', 'A', 'B'],
        'sender_balance_before': [0.0, 1000.0, 500.0],
        'sender_balance_after': [1000.0, 500.0, 300.0],
        'receiver_id': ['B', 'C', 'A'],
        'receiver_balance_before': [0.0, 0.0, 500.0],
        'receiver_balance_after': [0.0, 500.0, 700.0],
        'is_fraud': [False, False, False],
        'is_flagged': [False, True, False]
    })

    reconstructor = TimelineReconstructor()

    # Test for Account A
    events_A = reconstructor.build_account_timeline(df, 'A')
    assert len(events_A) == 3

    assert events_A[0].step == 1
    assert events_A[0].event_type == 'CASH_IN'
    assert events_A[0].counterparty == 'B'
    assert events_A[0].balance_before == 0.0
    assert events_A[0].balance_after == 1000.0
    assert events_A[0].is_flagged == False

    assert events_A[1].step == 2
    assert events_A[1].event_type == 'TRANSFER'
    assert events_A[1].counterparty == 'C'
    assert events_A[1].balance_before == 1000.0
    assert events_A[1].balance_after == 500.0
    assert events_A[1].is_flagged == True

    assert events_A[2].step == 3
    assert events_A[2].event_type == 'CASH_OUT'
    assert events_A[2].counterparty == 'B'
    assert events_A[2].balance_before == 500.0
    assert events_A[2].balance_after == 700.0
    assert events_A[2].is_flagged == False

def test_annotate_events():
    events = [
        TimelineEvent(1, 'TRANSFER', 100.0, 'B', 100.0, 0.0, "", True),
        TimelineEvent(2, 'CASH_OUT', 50.0, 'C', 100.0, 0.0, "", False),
        TimelineEvent(3, 'CASH_IN', 200.0, 'D', 0.0, 200.0, "", False)
    ]

    findings = [
        {"pattern": "rapid_drain", "step_start": 1, "step_end": 2},
        {"pattern": "dormant_activation", "step_start": 3, "step_end": 3}
    ]

    reconstructor = TimelineReconstructor()
    annotated = reconstructor.annotate_events(events, findings)

    assert "[RAPID DRAIN]" in annotated[0].annotation
    assert "[ACCOUNT DRAINED]" in annotated[0].annotation
    assert "[FLAGGED BY PAYSIM]" in annotated[0].annotation

    assert "[RAPID DRAIN]" in annotated[1].annotation
    assert "[ACCOUNT DRAINED]" in annotated[1].annotation

    assert "[DORMANT ACTIVATION]" in annotated[2].annotation
    assert "[ACCOUNT DRAINED]" not in annotated[2].annotation

def test_generate_narrative():
    events = [
        TimelineEvent(1, 'CASH_IN', 1000.0, 'B', 0.0, 1000.0, "", False),
        TimelineEvent(2, 'TRANSFER', 1000.0, 'C', 1000.0, 0.0, "", True)
    ]
    findings = [{"pattern": "rapid_drain", "step_start": 1, "step_end": 2}]

    reconstructor = TimelineReconstructor()
    narrative = reconstructor.generate_narrative(events, 'A', findings)

    assert 'A' in narrative
    assert 'step 1' in narrative
    assert '2000.00' in narrative
    assert 'rapid drain' in narrative

def test_to_dict_list():
    events = [
        TimelineEvent(1, 'CASH_IN', 1000.0, 'B', 0.0, 1000.0, "Test", False)
    ]
    reconstructor = TimelineReconstructor()
    dicts = reconstructor.to_dict_list(events)

    assert len(dicts) == 1
    assert dicts[0]['step'] == 1
    assert dicts[0]['event_type'] == 'CASH_IN'
    assert dicts[0]['amount'] == 1000.0
    assert dicts[0]['counterparty'] == 'B'
    assert dicts[0]['balance_before'] == 0.0
    assert dicts[0]['balance_after'] == 1000.0
    assert dicts[0]['annotation'] == 'Test'
    assert dicts[0]['is_flagged'] == False
