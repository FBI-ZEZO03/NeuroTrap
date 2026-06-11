# FHIM — Federated Honeypot Intelligence Mesh

The Federated Honeypot Intelligence Mesh (FHIM) enables multiple organizations to collaboratively improve their shared threat classifier without exposing their raw attacker data. Each node trains locally on its own honeypot telemetry and shares only noisy weight updates, preserving privacy while contributing to a globally stronger model.

---

## Architecture

```
Organization A           Organization B           Organization C
(Cairo Uni)              (Acme Financial)         (Fraunhofer FKIE)
    │                         │                         │
    ▼                         ▼                         ▼
FederatedNode             FederatedNode             FederatedNode
  train locally              train locally              train locally
  add DP noise               add DP noise               add DP noise
    │                         │                         │
    └──────────┬──────────────┘──────────────────────────┘
               ▼
        FedAvgServer
         (NeuroTrap)
          FedAvg()
          updated global model → broadcast back
```

---

## Components

| Component | File | Role |
|-----------|------|------|
| `FederatedNode` | `src/fhim/federated_node.py` | Local trainer + differential privacy noise injection |
| `FedAvgServer` | `src/fhim/aggregation_server.py` | Receives deltas, averages via FedAvg, broadcasts global model |

---

## FederatedNode

Each node operates independently:

```python
class FederatedNode:
    def train_local(self, sessions: list) -> None:
        """Train RF + SVM on local session data."""
        X, y = self.feature_extractor.transform(sessions)
        self.local_model.fit(X, y)
        self.local_f1 = f1_score(y_test, self.local_model.predict(X_test), average="macro")

    def compute_delta(self) -> dict:
        """Compute weight delta vs. global model weights."""
        return {k: local[k] - global[k] for k in local.keys()}

    def apply_differential_privacy(self, delta: dict) -> dict:
        """Add Gaussian noise to delta (epsilon-delta DP)."""
        noise_scale = self.sensitivity / self.epsilon
        return {k: v + np.random.normal(0, noise_scale, v.shape)
                for k, v in delta.items()}

    def submit_update(self) -> None:
        """Send noisy delta to the aggregation server."""
        delta = self.compute_delta()
        noisy_delta = self.apply_differential_privacy(delta)
        server.receive_update(self.node_id, noisy_delta)
```

### Privacy Parameters

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `epsilon` | 1.0 | Privacy budget (smaller = more private, less accurate) |
| `delta` | 1e-5 | Probability of privacy breach |
| `sensitivity` | 1.0 | L2 sensitivity of the model weights |

---

## FedAvgServer

The aggregation server collects weight deltas from participating nodes and averages them:

```python
class FedAvgServer:
    def receive_update(self, node_id: str, delta: dict) -> None:
        self.pending_updates[node_id] = delta
        if len(self.pending_updates) >= self.min_nodes:
            self.aggregate()

    def aggregate(self) -> None:
        """Federated Averaging (FedAvg)."""
        avg_delta = {}
        for key in self.global_weights.keys():
            avg_delta[key] = np.mean([u[key] for u in self.pending_updates.values()], axis=0)

        # Apply averaged delta to global model
        for key in self.global_weights.keys():
            self.global_weights[key] += avg_delta[key]

        round_doc = {
            "round": self.round_count,
            "participants": list(self.pending_updates.keys()),
            "global_f1": self.evaluate_global(),
            "timestamp": time.time(),
        }
        db.fhim_aggregation_rounds.insert_one(round_doc)
        self.pending_updates.clear()
        self.round_count += 1
```

Aggregation fires when `min_nodes` (default: 2) have submitted updates.

---

## Demo Organizations

The server is pre-seeded with 4 demo nodes to demonstrate the federated mesh without requiring real external participants:

| Node ID | Organization | Status |
|---------|-------------|--------|
| `cairo-uni-01` | Cairo University | active |
| `acme-financial-01` | Acme Financial | active |
| `fraunhofer-fkie-01` | Fraunhofer FKIE | active |
| `saudi-telecom-01` | SaudiTelecom | standby |

---

## Metrics

The FHIM dashboard section shows:

- **Node table** — node ID, organization, status, last seen, local F1
- **Aggregation rounds** — round number, participants, global F1 evolution over time
- **Privacy summary** — epsilon/delta values in use

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fhim/nodes` | GET | Node status + global F1 |
| `/api/fhim/rounds` | GET | Aggregation round history |

---

## Known Limitations

- **Aggregation rounds = 0 by default** — the FHIM runs in demo mode. Real FedAvg rounds require organizations to submit real updates from their own datasets.
- **Demo deltas only** — the demo nodes submit pre-computed deltas that simulate a round but don't use real honeypot data.
- **No TLS between nodes** — the inter-node protocol is not production-hardened; add mutual TLS for real deployments.

---

## Enabling Real Federation

To add a real external node:

```python
from src.fhim.federated_node import FederatedNode

node = FederatedNode(
    node_id="my-org-01",
    server_url="https://neurotrap-server:5000/api/fhim",
    epsilon=0.5,           # stricter privacy
    delta=1e-6,
)
# Train on your local sessions
node.train_local(your_sessions)
# Submit noisy delta to NeuroTrap
node.submit_update()
```
