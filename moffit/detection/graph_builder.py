import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any

class TransactionGraph:
    """
    Builder and analyzer for mobile money transaction graphs.
    """

    def build(self, df: pd.DataFrame) -> nx.DiGraph:
        """
        Builds a directed graph from a normalized PaySim DataFrame.

        Nodes represent account IDs, with attributes for total sent,
        total received, transaction count, and whether they were ever flagged.
        Edges represent transactions, with attributes for amount, step, and type.

        Args:
            df (pd.DataFrame): Normalized pandas DataFrame of transactions.

        Returns:
            nx.DiGraph: A NetworkX DiGraph.
        """
        G = nx.DiGraph()

        node_stats = {}

        for _, row in df.iterrows():
            sender = row['sender_id']
            receiver = row['receiver_id']
            amount = float(row['amount'])
            step = int(row['step'])
            tx_type = str(row['tx_type'])
            is_flagged = bool(row.get('is_flagged', False))

            # Update sender stats
            if sender not in node_stats:
                node_stats[sender] = {'total_sent': 0.0, 'total_received': 0.0, 'tx_count': 0, 'is_flagged': False}
            node_stats[sender]['total_sent'] += amount
            node_stats[sender]['tx_count'] += 1
            if is_flagged:
                node_stats[sender]['is_flagged'] = True

            # Update receiver stats
            if receiver not in node_stats:
                node_stats[receiver] = {'total_sent': 0.0, 'total_received': 0.0, 'tx_count': 0, 'is_flagged': False}
            node_stats[receiver]['total_received'] += amount
            node_stats[receiver]['tx_count'] += 1
            if is_flagged:
                node_stats[receiver]['is_flagged'] = True

            # Add edge
            G.add_edge(sender, receiver, amount=amount, step=step, tx_type=tx_type)

        # Add nodes with attributes
        for node, stats in node_stats.items():
            G.add_node(node, **stats)

        return G

    def get_ego_network(self, graph: nx.DiGraph, account_id: str, depth: int = 2) -> nx.DiGraph:
        """
        Returns a subgraph of all nodes within 'depth' hops of account_id.

        Args:
            graph (nx.DiGraph): The complete transaction graph.
            account_id (str): The central account ID.
            depth (int): The radius of the ego network.

        Returns:
            nx.DiGraph: The ego network subgraph.
        """
        # Undirected radius check is typically used for ego networks,
        # nx.ego_graph defaults to directed distance if graph is directed.
        # But for transaction graphs, we often want nodes within 'depth' hops ignoring direction.
        # nx.ego_graph has `undirected=True` to compute distances in the undirected graph.
        # The prompt doesn't specify. I will use undirected=True for full context.
        return nx.ego_graph(graph, account_id, radius=depth, undirected=True)

    def compute_centrality(self, graph: nx.DiGraph) -> Dict[str, Dict[str, float]]:
        """
        Computes various centrality metrics for the graph nodes.

        Args:
            graph (nx.DiGraph): The transaction graph.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping account ID to centrality metrics
                                        (degree, betweenness, in_degree, out_degree).
        """
        degree_cent = nx.degree_centrality(graph)
        betweenness_cent = nx.betweenness_centrality(graph)
        in_degree_cent = nx.in_degree_centrality(graph)
        out_degree_cent = nx.out_degree_centrality(graph)

        centrality = {}
        for node in graph.nodes():
            centrality[node] = {
                'degree': degree_cent.get(node, 0.0),
                'betweenness': betweenness_cent.get(node, 0.0),
                'in_degree': in_degree_cent.get(node, 0.0),
                'out_degree': out_degree_cent.get(node, 0.0)
            }
        return centrality

    def find_high_velocity_accounts(self, graph: nx.DiGraph, df: pd.DataFrame, window: int = 10, threshold: int = 8) -> List[str]:
        """
        Finds accounts with more than 'threshold' transactions in any 'window' of steps.

        Args:
            graph (nx.DiGraph): The transaction graph.
            df (pd.DataFrame): The transaction DataFrame.
            window (int): Number of steps for the rolling window.
            threshold (int): Minimum number of transactions in a window to be flagged.

        Returns:
            List[str]: List of account IDs exceeding the velocity threshold.
        """
        high_velocity_accounts = set()

        senders = df[['sender_id', 'step']].rename(columns={'sender_id': 'account_id'})
        receivers = df[['receiver_id', 'step']].rename(columns={'receiver_id': 'account_id'})

        all_txs = pd.concat([senders, receivers])
        all_txs = all_txs.sort_values(by=['account_id', 'step'])

        for account_id, group in all_txs.groupby('account_id'):
            steps = group['step'].values
            n = len(steps)
            if n > threshold:
                left = 0
                for right in range(n):
                    while steps[right] - steps[left] >= window:
                        left += 1
                    if right - left + 1 > threshold:
                        high_velocity_accounts.add(account_id)
                        break

        return list(high_velocity_accounts)

    def visualize_ego_network(self, graph: nx.DiGraph, account_id: str, output_path: str) -> None:
        """
        Visualizes the ego network of a specific account and saves it as a PNG.
        Colors nodes: red if is_flagged, steelblue otherwise.
        Edge width = log(amount).

        Args:
            graph (nx.DiGraph): The complete transaction graph.
            account_id (str): The central account ID.
            output_path (str): File path to save the PNG image.
        """
        ego_net = self.get_ego_network(graph, account_id)

        pos = nx.spring_layout(ego_net, seed=42)

        node_colors = []
        for node in ego_net.nodes():
            is_flagged = ego_net.nodes[node].get('is_flagged', False)
            if is_flagged:
                node_colors.append('red')
            else:
                node_colors.append('steelblue')

        edge_widths = []
        for u, v, data in ego_net.edges(data=True):
            amount = data.get('amount', 1.0)
            # Use math.log but fallback securely
            # width = log(amount) as specified, we'll use np.log(amount) or fallback
            width = np.log(amount) if amount > 1 else 0.5
            edge_widths.append(width)

        plt.figure(figsize=(10, 8))
        nx.draw(ego_net, pos, node_color=node_colors, width=edge_widths, with_labels=True,
                node_size=600, font_size=10, font_color='white', edge_color='gray')
        plt.savefig(output_path)
        plt.close()
