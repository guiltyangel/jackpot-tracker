import requests
import time
from typing import List, Dict, Optional
from requests.exceptions import ReadTimeout, ConnectionError

# ============================================================
# CONFIG
# ============================================================
BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"
USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()
JACKPOT_EVENT_TOPIC0 = "0xb46ce08eb89d4239a12b7d0a46b94864a9d6875da7b8828f7e0d1e3b058d487c"

REQUEST_DELAY = 0.5  
MAX_RETRIES = 3      
MAX_LOOKAHEAD_BLOCKS = 50
MAX_PAGES_TO_SCAN = 30 

# ============================================================
# HTTP HELPERS
# ============================================================
def _get(url: str) -> Dict:
    """Hàm gọi API có cơ chế thử lại khi bị Timeout."""
    for i in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except (ReadTimeout, ConnectionError):
            if i == MAX_RETRIES - 1:
                raise 
            time.sleep(2) 
    return {}

def get_tx_logs(tx_hash: str) -> List[Dict]:
    url = f"{BASE_BLOCKSCOUT_API}?module=logs&action=getLogs&txhash={tx_hash}"
    data = _get(url)
    result = data.get("result", [])
    return result if isinstance(result, list) else []

# ============================================================
# LOGIC FUNCTIONS
# ============================================================
def is_buy_jackpot_tx(tx_hash: str) -> bool:
    logs = get_tx_logs(tx_hash)
    for log in logs:
        topics = log.get("topics", [])
        if topics and topics[0].lower() == JACKPOT_EVENT_TOPIC0:
            return True
    return False

def find_reward_payout(buyer: str, buy_block: int) -> Optional[Dict]:
    buyer = buyer.lower()
    start_block = buy_block + 1
    end_block = buy_block + MAX_LOOKAHEAD_BLOCKS

    url = (
        f"{BASE_BLOCKSCOUT_API}"
        f"?module=account&action=tokentx"
        f"&address={RIPS_MANAGER}"
        f"&startblock={start_block}"
        f"&endblock={end_block}"
        f"&sort=asc"
    )
    
    data = _get(url)
    transfers = data.get("result", [])
    if not isinstance(transfers, list) or not transfers:
        return None

    payouts = [t for t in transfers if t.get("to", "").lower() == buyer]
    if not payouts:
        return None

    payout_tx = payouts[0].get("hash")
    reward_block = int(payouts[0].get("blockNumber", 0))
    reward_tokens = []

    for t in payouts:
        if t.get("hash") == payout_tx:
            decimal = int(t.get("tokenDecimal", 18))
            amount = int(t.get("value", 0)) / (10 ** decimal)
            reward_tokens.append({
                "token_symbol": t.get("tokenSymbol", "Unknown"),
                "token_address": t.get("tokenAddress", ""),
                "amount": amount,
            })

    return {
        "reward_tx_hash": payout_tx,
        "reward_block": reward_block,
        "delay_blocks": reward_block - buy_block,
        "reward_tokens": reward_tokens,
    }

def scan_latest_jackpot_packs(target_count: int) -> List[Dict]:
    results: List[Dict] = []
    page = 1
    processed_txs = set()

    while len(results) < target_count and page <= MAX_PAGES_TO_SCAN:
        url = (
            f"{BASE_BLOCKSCOUT_API}"
            f"?module=account&action=tokentx"
            f"&address={RIPS_MANAGER}"
            f"&page={page}"
            f"&offset=50"
            f"&sort=desc"
        )
        
        data = _get(url)
        transfers = data.get("result", [])
        if not isinstance(transfers, list) or not transfers:
            break

        for t in transfers:
            tx_hash = t.get("hash")
            if not tx_hash or tx_hash in processed_txs:
                continue
            processed_txs.add(tx_hash)

            if (t.get("tokenAddress", "").lower() == USDC_ADDRESS and 
                t.get("to", "").lower() == RIPS_MANAGER):
                
                if is_buy_jackpot_tx(tx_hash):
                    buyer = t.get("from", "").lower()
                    buy_block = int(t.get("blockNumber", 0))
                    reward = find_reward_payout(buyer, buy_block)

                    results.append({
                        "buy_tx_hash": tx_hash,
                        "buy_block": buy_block,
                        "buyer": buyer,
                        "reward": reward
                    })
                    if len(results) >= target_count:
                        break
        page += 1
    return results
