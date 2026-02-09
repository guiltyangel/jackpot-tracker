import requests
import time
from typing import List, Dict, Optional

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"

RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()
USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()

PACK_TYPE_TARGET = "jackpot-500"

USDC_AMOUNT_TARGET = 5
USDC_AMOUNT_TOLERANCE = 0.10   # ±10%

PACK_SCAN_LIMIT = 20           # số pack jackpot-500 muốn lấy
MAX_LOOKAHEAD_BLOCKS = 50
REQUEST_DELAY = 0.25

# ============================================================
# HTTP
# ============================================================

def _get(url: str) -> Dict:
    time.sleep(REQUEST_DELAY)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# ============================================================
# BLOCKSCOUT HELPERS
# ============================================================

def get_manager_token_txs(limit=300) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=account&action=tokentx"
        f"&address={RIPS_MANAGER}"
        f"&sort=desc"
        f"&page=1&offset={limit}"
    )
    return data.get("result", [])

def get_tx_logs(tx_hash: str) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=logs&action=getLogs&txhash={tx_hash}"
    )
    return data.get("result", [])

def get_address_token_transfers(
    address: str,
    start_block: int,
    end_block: int
) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=account&action=tokentx"
        f"&address={address}"
        f"&startblock={start_block}"
        f"&endblock={end_block}"
        f"&sort=asc"
    )
    return data.get("result", [])

# ======================
