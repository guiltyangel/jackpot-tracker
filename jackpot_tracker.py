import requests
import time
from typing import List, Dict, Optional

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"

USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

PACK_TYPE_TARGET = "jackpot-500"

REQUEST_DELAY = 0.2        # seconds (avoid rate limit)
MAX_LOOKAHEAD_BLOCKS = 50  # payout delay tolerance
MAX_SCAN_BLOCKS = 8000     # safety limit for backward scan

# ============================================================
# HTTP HELPER
# ============================================================

def _get(url: str) -> Dict:
    time.sleep(REQUEST_DELAY)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

# ============================================================
# BLOCKSCOUT HELPERS
# ============================================================

def get_latest_block() -> int:
    data = _get(
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=proxy&action=eth_blockNumber"
    )
    return int(data["result"], 16)

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
# BUY JACKPOT-500 DETECTION
# ============================================================

def is_buy_jackpot_tx(tx_hash: str, buyer: str) -> bool:
    buyer = buyer.lower()

    # Check USDC transfer buyer -> RIPS_MANAGER
    transfers = get_tx_token_transfers(tx_hash)
    usdc_ok = any(
        t["tokenAddress"].lower() == USDC_ADDRESS
        and t["from"].lower() == buyer
        and t["to"].lower() == RIPS_MANAGER
        for t in transfers
    )
    if not usdc_ok:
        return False

    # Heuristic log check for jackpot-500
    logs = get_tx_logs(tx_hash)
    return any(PACK_TYPE_TARGET in str(log).lower() for log in logs)

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

        relevant = [
            t for t in transfers
            if t["to"].lower() == buyer
        ]

        if not relevant:
            continue

        tx_map: Dict[str, List[Dict]] = {}
        for t in relevant:
            tx_map.setdefault(t["hash"], []).append(t)

        payout_tx = list(tx_map.keys())[0]
        reward_transfers = tx_map[payout_tx]

        reward_tokens = []
        for t in reward_transfers:
            amount = int(t["value"]) / (10 ** int(t["tokenDecimal"]))
            reward_tokens.append({
                "token_symbol": t["tokenSymbol"],
                "token_address": t["tokenAddress"],
                "amount": amount,
                "amount_raw": t["value"],
                "decimals": t["tokenDecimal"],
            })

        return {
            "reward_tx_hash": payout_tx,
            "reward_block": block,
            "delay_blocks": block - buy_block,
            "reward_tokens": reward_tokens,
            "confidence": (
                "high" if block - buy_block <= 5
                else "medium" if block - buy_block <= 20
                else "low"
            )
        }

    return None

# ============================================================
# SCANNER: BACKWARD UNTIL N JACKPOT PACKS FOUND
# ============================================================

def scan_latest_jackpot_packs(
    target_count: int
) -> List[Dict]:
    """
    Scan backward from latest block until target_count jackpot-500 packs are found
    """

    latest_block = get_latest_block()
    results: List[Dict] = []

    scanned_blocks = 0
    current_block = latest_block

    while current_block > 0 and len(results) < target_count:
        transfers = get_address_token_transfers(
            RIPS_MANAGER,
            current_block,
            current_block
        )

        for t in transfers:
            # candidate buy tx: USDC -> RIPS_MANAGER
            if t["tokenAddress"].lower() != USDC_ADDRESS:
                continue

            buyer = t["from"].lower()
            tx_hash = t["hash"]
            buy_block = int(t["blockNumber"])

            if not is_buy_jackpot_tx(tx_hash, buyer):
                continue

            reward = find_reward_payout(
                buyer=buyer,
                buy_block=buy_block
            )

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
