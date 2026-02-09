import requests
import time
import csv
from typing import List, Dict, Optional

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"

USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

PACK_TYPE_TARGET = "jackpot-500"
MAX_LOOKAHEAD_BLOCKS = 50
REQUEST_DELAY = 0.2  # seconds

# ============================================================
# HTTP HELPERS
# ============================================================

def _get(url: str) -> Dict:
    time.sleep(REQUEST_DELAY)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

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

def get_address_token_transfers(address: str, start_block: int, end_block: int) -> List[Dict]:
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
# 1️⃣ BUY RIPS DETECTION
# ============================================================

def is_buy_rips_tx(tx_hash: str, buyer_address: str) -> bool:
    buyer_address = buyer_address.lower()

    # Check USDC transfer
    transfers = get_tx_token_transfers(tx_hash)
    usdc_ok = any(
        t["tokenAddress"].lower() == USDC_ADDRESS
        and t["from"].lower() == buyer_address
        and t["to"].lower() == RIPS_MANAGER
        for t in transfers
    )
    if not usdc_ok:
        return False

    # Heuristic log check
    logs = get_tx_logs(tx_hash)
    return any(PACK_TYPE_TARGET in str(log).lower() for log in logs)

# ============================================================
# 2️⃣ REWARD PAYOUT MATCHING
# ============================================================

def find_reward_payout(buyer_address: str, buy_block: int) -> Optional[Dict]:
    buyer_address = buyer_address.lower()

    transfers = get_address_token_transfers(
        RIPS_MANAGER,
        buy_block + 1,
        buy_block + MAX_LOOKAHEAD_BLOCKS
    )

    relevant = [
        t for t in transfers
        if t["to"].lower() == buyer_address
    ]

    if not relevant:
        return None

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

    block_numbers = {int(t["blockNumber"]) for t in reward_transfers}
    reward_block = min(block_numbers)

    return {
        "reward_tx_hash": payout_tx,
        "reward_block": reward_block,
        "delay_blocks": reward_block - buy_block,
        "reward_tokens": reward_tokens,
        "confidence": (
            "high" if reward_block - buy_block <= 5
            else "medium" if reward_block - buy_block <= 20
            else "low"
        )
    }

# ============================================================
# MAIN FLOW
# ============================================================

def process_buy_rips_event(buy_tx_hash: str, buyer_address: str, buy_block: int) -> Dict:
    if not is_buy_rips_tx(buy_tx_hash, buyer_address):
        raise ValueError("Not a valid BUY RIPS (jackpot-500) transaction")

    reward = find_reward_payout(buyer_address, buy_block)

    return {
        "buy_tx_hash": buy_tx_hash,
        "buy_block": buy_block,
        "buyer": buyer_address,
        "rips_manager": RIPS_MANAGER,
        "reward": reward
    }

# ============================================================
# EXPORT
# ============================================================

def export_reward_csv(result: Dict, filename: str = "reward.csv"):
    reward = result.get("reward")
    if not reward:
        print("No reward found, nothing to export.")
        return

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["token", "amount", "tx_hash"])
        for r in reward["reward_tokens"]:
            writer.writerow([
                r["token_symbol"],
                r["amount"],
                reward["reward_tx_hash"]
            ])

    print(f"CSV exported → {filename}")

# ============================================================
# RUNNER
# ============================================================

if __name__ == "__main__":
    BUY_TX = "0xYOUR_BUY_TX_HASH"
    BUYER = "0xYOUR_WALLET"
    BUY_BLOCK = 12345678

    result = process_buy_rips_event(BUY_TX, BUYER, BUY_BLOCK)
    print(result)

    export_reward_csv(result)
