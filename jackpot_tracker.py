import requests
import time
from typing import List, Dict, Optional

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"

USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

# PackPurchased(address,string,string)
JACKPOT_EVENT_TOPIC0 = (
    "0xb46ce08eb89d4239a12b7d0a46b94864"
    "a9d6875da7b8828f7e0d1e3b058d487c"
)

REQUEST_DELAY = 0.5
MAX_LOOKAHEAD_BLOCKS = 5
MAX_SCAN_BLOCKS = 1000

# ============================================================
# HTTP HELPERS
# ============================================================

def _get(url: str) -> Dict:
    time.sleep(REQUEST_DELAY)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# ============================================================
# LATEST BLOCK (STABLE METHOD)
# ============================================================

def get_latest_block() -> int:
    """
    Get latest block via most recent token transfer
    (stable on Blockscout Base)
    """
    url = (
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=account"
        f"&action=tokentx"
        f"&address={RIPS_MANAGER}"
        f"&page=1"
        f"&offset=1"
        f"&sort=desc"
    )
    data = _get(url)
    items = data.get("result", [])
    if not items:
        raise RuntimeError("Cannot determine latest block")
    return int(items[0]["blockNumber"])

# ============================================================
# BLOCKSCOUT HELPERS
# ============================================================

def get_tx_token_transfers(tx_hash: str) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=account&action=tokentx&txhash={tx_hash}"
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

# ============================================================
# BUY JACKPOT PACK DETECTION (EVENT-BASED)
# ============================================================

def is_buy_jackpot_tx(tx_hash: str, buyer: str) -> bool:
    buyer = buyer.lower()

    # 1) USDC -> RIPS_MANAGER
    transfers = get_tx_token_transfers(tx_hash)
    usdc_ok = any(
        t.get("tokenAddress", "").lower() == USDC_ADDRESS
        and t.get("from", "").lower() == buyer
        and t.get("to", "").lower() == RIPS_MANAGER
        for t in transfers
    )
    if not usdc_ok:
        return False

    # 2) PackPurchased event (topic0)
    logs = get_tx_logs(tx_hash)
    for log in logs:
        topics = log.get("topics", [])
        if topics and topics[0].lower() == JACKPOT_EVENT_TOPIC0:
            return True

    return False

# ============================================================
# REWARD PAYOUT MATCHING
# ============================================================

def find_reward_payout(
    buyer: str,
    buy_block: int
) -> Optional[Dict]:

    buyer = buyer.lower()

    for block in range(buy_block + 1, buy_block + MAX_LOOKAHEAD_BLOCKS + 1):
        transfers = get_address_token_transfers(
            RIPS_MANAGER,
            block,
            block
        )

        payouts = [
            t for t in transfers
            if t.get("to", "").lower() == buyer
            and t.get("tokenAddress")
        ]

        if not payouts:
            continue

        payout_tx = payouts[0]["hash"]
        reward_tokens = []

        for t in payouts:
            if not t.get("tokenDecimal"):
                continue

            amount = int(t["value"]) / (10 ** int(t["tokenDecimal"]))
            reward_tokens.append({
                "token_symbol": t.get("tokenSymbol"),
                "token_address": t.get("tokenAddress"),
                "amount": amount,
            })

        return {
            "reward_tx_hash": payout_tx,
            "reward_block": block,
            "delay_blocks": block - buy_block,
            "reward_tokens": reward_tokens,
        }

    return None

# ============================================================
# MAIN SCANNER – BACKWARD UNTIL N PACKS FOUND
# ============================================================

def scan_latest_jackpot_packs(
    target_count: int
) -> List[Dict]:

    latest_block = get_latest_block()
    results: List[Dict] = []

    current_block = latest_block
    scanned_blocks = 0

    while current_block > 0 and len(results) < target_count:
        transfers = get_address_token_transfers(
            RIPS_MANAGER,
            current_block,
            current_block
        )

        for t in transfers:
            token_address = t.get("tokenAddress")
            if not token_address or token_address.lower() != USDC_ADDRESS:
                continue

            buyer = t.get("from", "").lower()
            tx_hash = t.get("hash")
            buy_block = int(t.get("blockNumber", 0))

            if not buyer or not tx_hash:
                continue

            if not is_buy_jackpot_tx(tx_hash, buyer):
                continue

            reward = find_reward_payout(buyer, buy_block)

            results.append({
                "buy_tx_hash": tx_hash,
                "buy_block": buy_block,
                "buyer": buyer,
                "reward": reward
            })

            if len(results) >= target_count:
                break

        current_block -= 1
        scanned_blocks += 1

        if scanned_blocks >= MAX_SCAN_BLOCKS:
            break

    return results

