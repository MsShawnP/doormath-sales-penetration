# Cinderhaven Store Universe

Shared synthetic data package for the Cinderhaven CPG analytics suite.
Provides a deterministic 640-door store universe with authorization matrices,
weekly POS scan data, and slow-leak story configurations.

## Install

```bash
pip install -e packages/cinderhaven-store-universe
```

## Public API

```python
from cinderhaven_store_universe import (
    DEMO_AS_OF_DATE,   # pd.Timestamp('2025-12-29')
    get_stores,        # -> DataFrame: 640 stores across 6 retailers
    get_auth_matrix,   # -> DataFrame: SKU x store authorization flags
    get_scan_data,     # -> DataFrame: weekly POS scan flags (2024-W01 – 2025-W52)
    get_slow_leak_config,  # -> dict: leak story parameters
)
```

All data is seeded (SEED=42) for full reproducibility.

Built by [Lailara LLC](https://lailarallc.com) -- data hygiene and analytics consulting for specialty food brands scaling into national retail.
