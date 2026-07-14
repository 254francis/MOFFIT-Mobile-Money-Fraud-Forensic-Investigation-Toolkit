import pytest
import pandas as pd
import networkx as nx
import os
from moffit.detection.graph_builder import TransactionGraph

@pytest.fixture
def synthetic_df():
    """Generates a 100-row synthetic PaySim-like DataFrame for testing."""
    data = []

    # 1. Normal transactions (step 1 to 50)
    for i in range(1, 51):
        data.append({
            'step': i,
            'tx_type': 'PAYMENT',
            'amount': 100.0 * i,
            'sender_id': f'C{i}',
            'sender_balance_before': 1000.0 * i,
            'sender_balance_after': 900.0 * i,
            'receiver_id': f'M{i}',
            'receiver_balance_before': 0.0,
            'receiver_balance_after': 100.0 * i,
            'is_fraud': False,
            'is_flagged': False
        })

    # 2. High velocity account (Account H1 sends 10 transactions in a window of 5 steps)
    for i in range(51, 61):
        data.append({
            'step': 55 + (i - 51) // 2, # steps 55, 55, 56, 56, 57, 57, 58, 58, 59, 59
            'tx_type': 'TRANSFER',
            'amount': 50.0,
            'sender_id': 'H1',
            'sender_balance_before': 1000.0,
            'sender_balance_after': 950.0,
            'receiver_id': f'C{i}',
            'receiver_balance_before': 0.0,
            'receiver_balance_after': 50.0,
            'is_fraud': True,
            'is_flagged': True
        })

    # 3. Some multi-hop transactions for ego network (H1 -> C61 -> C62 -> C63)
    data.append({
        'step': 60, 'tx_type': 'TRANSFER', 'amount': 200.0, 'sender_id': 'H1', 'receiver_id': 'C61',
        'is_fraud': False, 'is_flagged': False
    })
    data.append({
        'step': 61, 'tx_type': 'TRANSFER', 'amount': 150.0, 'sender_id': 'C61', 'receiver_id': 'C62',
        'is_fraud': False, 'is_flagged': False
    })
    data.append({
        'step': 62, 'tx_type': 'TRANSFER', 'amount': 100.0, 'sender_id': 'C62', 'receiver_id': 'C63',
        'is_fraud': False, 'is_flagged': False
    })

    # Fill remaining to make 100 rows
    for i in range(63, 100):
        data.append({
            'step': i,
            'tx_type': 'CASH_IN',
            'amount': 500.0,
            'sender_id': f'C{i}',
            'sender_balance_before': 0.0,
            'sender_balance_after': 500.0,
            'receiver_id': 'BANK',
            'receiver_balance_before': 100000.0,
            'receiver_balance_after': 99500.0,
            'is_fraud': False,
            'is_flagged': False
        })

    df = pd.DataFrame(data)

    # Fill missing columns with defaults for consistency
    for col in ['sender_balance_before', 'sender_balance_after', 'receiver_balance_before', 'receiver_balance_after']:
        if col not in df.columns:
            df[col] = 0.0

    return df

@pytest.fixture
def graph_builder():
    return TransactionGraph()

def test_build_graph(graph_builder, synthetic_df):
    G = graph_builder.build(synthetic_df)

    assert isinstance(G, nx.DiGraph)

    # Check if a specific node has the correct attributes
    assert 'H1' in G.nodes
    node_H1 = G.nodes['H1']
    assert node_H1['tx_count'] == 11 # 10 high velocity + 1 to C61
    assert node_H1['total_sent'] == 50.0 * 10 + 200.0
    assert node_H1['total_received'] == 0.0
    assert node_H1['is_flagged'] == True

    assert 'C1' in G.nodes
    node_C1 = G.nodes['C1']
    assert node_C1['tx_count'] == 1
    assert node_C1['total_sent'] == 100.0
    assert node_C1['total_received'] == 0.0
    assert node_C1['is_flagged'] == False

    # Check edges
    assert G.has_edge('H1', 'C61')
    edge_data = G.edges['H1', 'C61']
    assert edge_data['amount'] == 200.0
    assert edge_data['step'] == 60
    assert edge_data['tx_type'] == 'TRANSFER'

def test_get_ego_network(graph_builder, synthetic_df):
    G = graph_builder.build(synthetic_df)

    # Depth 1 from C61 should include H1 and C62
    ego_1 = graph_builder.get_ego_network(G, 'C61', depth=1)
    assert set(ego_1.nodes) == {'C61', 'H1', 'C62'}

    # Depth 2 from C61 should include C63, and all receivers of H1
    ego_2 = graph_builder.get_ego_network(G, 'C61', depth=2)
    assert 'C63' in ego_2.nodes
    # Check one of H1's other receivers is in depth 2
    assert 'C51' in ego_2.nodes

def test_compute_centrality(graph_builder, synthetic_df):
    G = graph_builder.build(synthetic_df)
    centrality = graph_builder.compute_centrality(G)

    assert 'H1' in centrality
    assert 'BANK' in centrality

    # H1 should have a high out_degree
    assert centrality['H1']['out_degree'] > 0
    assert centrality['H1']['in_degree'] == 0

    # BANK should have a high in_degree
    assert centrality['BANK']['in_degree'] > 0
    assert centrality['BANK']['out_degree'] == 0

def test_find_high_velocity_accounts(graph_builder, synthetic_df):
    G = graph_builder.build(synthetic_df)

    # Window of 10, threshold 8
    # H1 has 10 transactions between step 55 and 59. This fits within a window of 10 steps.
    high_velocity = graph_builder.find_high_velocity_accounts(G, synthetic_df, window=10, threshold=8)

    assert 'H1' in high_velocity
    # Ensure a normal account is not in there
    assert 'C1' not in high_velocity

def test_visualize_ego_network(graph_builder, synthetic_df, tmp_path):
    G = graph_builder.build(synthetic_df)

    output_path = tmp_path / "ego_network.png"
    graph_builder.visualize_ego_network(G, 'H1', str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 0
