import requests
import time
from typing import List, Dict, Optional
from requests.exceptions import ReadTimeout, ConnectionError

# ============================================================
# CONFIGURATION
# ============================================================
BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"
USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

# Topic0 của event RipsPurchased dựa trên ảnh bạn cung cấp
JACKPOT_EVENT_TOPIC0 = "0xb16657efe1c32e9466b9cad76b02443daaf97b7c78fc84eca8dea2775c0eef7c".lower()
# Hex của chuỗi "jackpot-500" để nhận diện trong data log
JACKPOT_500_HEX = "6a61636b706f742d353030" 

REQUEST_DELAY = 0.5  # Giãn cách giữa các request để tránh rate-limit
MAX_RETRIES = 3      # Thử lại nếu timeout
MAX_LOOKAHEAD_BLOCKS = 50 

# ============================================================
# HTTP HELPERS (WITH RETRY LOGIC)
# ============================================================
def _get(url: str) -> Dict:
    for i in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except (ReadTimeout, ConnectionError):
            if i == MAX_RETRIES - 1: raise
            time.sleep(2)
    return {}

def get_tx_logs(tx_hash: str) -> List[Dict]:
    url = f"{BASE_BLOCKSCOUT_API}?module=logs&action=getLogs&txhash={tx_hash}"
    data = _get(url)
    result = data.get("result", [])
    return result if isinstance(result, list) else []

# ============================================================
# LOGIC: CHECK JACKPOT-500 TYPE
# ============================================================
def is_buy_jackpot_500(tx_hash: str) -> bool:
    """Kiểm tra log để tìm đúng loại pack jackpot-500."""
    logs = get_tx_logs(tx_hash)
    for log in logs:
        topics = log.get("topics", [])
        data = log.get("data", "").lower()
        
        # Kiểm tra Topic0 của RipsPurchased
        if topics and topics[0].lower() == JACKPOT_EVENT_TOPIC0:
            # Kiểm tra xem trong phần Data có chứa chuỗi "jackpot-500" (dạng hex) hay không
            if JACKPOT_500_HEX in data:
                return True
    return False

def find_reward_payout(buyer: str, buy_block: int) -> Optional[Dict]:
    """Tìm giao dịch trả thưởng trong 50 block tiếp theo."""
    start = buy_block + 1
    end = buy_block + MAX_LOOKAHEAD_BLOCKS
    url = (f"{BASE_BLOCKSCOUT_API}?module=account&action=tokentx"
           f"&address={RIPS_MANAGER}&startblock={start}&endblock={end}&sort=asc")
    
    data = _get(url)
    transfers = data.get("result", [])
    if not isinstance(transfers, list): return None

    # Lọc các transfer gửi từ Manager tới Buyer
    payouts = [t for t in transfers if t.get("to", "").lower() == buyer.lower()]
    if not payouts: return None

    payout_tx = payouts[0].get("hash")
    reward_tokens = []
    for t in payouts:
        if t.get("hash") == payout_tx:
            decimal = int(t.get("tokenDecimal", 18))
            amount = int(t.get("value", 0)) / (10 ** decimal)
            reward_tokens.append({
                "token_symbol": t.get("tokenSymbol", "Unknown"),
                "amount": amount
            })

    return {
        "reward_tx_hash": payout_tx,
        "reward_block": int(payouts[0].get("blockNumber", 0)),
        "reward_tokens": reward_tokens
    }

# ============================================================
# MAIN SCANNER (PAGE-BASED)
# ============================================================
def scan_latest_jackpot_packs(target_count: int) -> List[Dict]:
    results = []
    page = 1
    processed_txs = set()

    while len(results) < target_count and page <= 40:
        url = (f"{BASE_BLOCKSCOUT_API}?module=account&action=tokentx"
               f"&address={RIPS_MANAGER}&page={page}&offset=50&sort=desc")
        
        data = _get(url)
        transfers = data.get("result", [])
        if not isinstance(transfers, list) or not transfers: break

        for t in transfers:
            tx_hash = t.get("hash")
            if not tx_hash or tx_hash in processed_txs: continue
            processed_txs.add(tx_hash)

            # Điều kiện: Gửi USDC đến Manager
            if (t.get("tokenAddress", "").lower() == USDC_ADDRESS and 
                t.get("to", "").lower() == RIPS_MANAGER):
                
                # Bước quan trọng: Kiểm tra đúng loại jackpot-500 trong logs
                if is_buy_jackpot_500(tx_hash):
                    buyer = t.get("from", "").lower()
                    buy_block = int(t.get("blockNumber", 0))
                    reward = find_reward_payout(buyer, buy_block)

                    results.append({
                        "buy_tx_hash": tx_hash,
                        "buy_block": buy_block,
                        "buyer": buyer,
                        "reward": reward
                    })
                    if len(results) >= target_count: break
        page += 1
    return results
