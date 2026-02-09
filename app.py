import streamlit as st
from jackpot_tracker import scan_jackpot_packs, normalize_results

st.set_page_config(
    page_title="Jackpot-500 Dashboard",
    layout="wide"
)

st.title("🎰 Jackpot-500 Analytics Dashboard (Base)")

st.caption("Auto-scan jackpot-500 pack purchases and rewards from Base")

# ============================================================
# SIDEBAR CONTROLS
# ============================================================

st.sidebar.header("Scan Settings")

pack_limit = st.sidebar.number_input(
    "Number of recent packs to scan",
    min_value=1,
    max_value=100,
    value=20
)

refresh = st.sidebar.button("🔄 Run Scan")

# ============================================================
# DATA LOAD
# ============================================================

@st.cache_data(show_spinner=False)
def load_data():
    scan_results = scan_jackpot_packs()
    pack_rows, reward_rows = normalize_results(scan_results)
    return pack_rows, reward_rows

if refresh:
    st.cache_data.clear()

with st.spinner("Scanning Base blockchain..."):
    pack_rows, reward_rows = load_data()

# ============================================================
# KPI ROW
# ============================================================

total_packs = len(pack_rows)
rewarded = sum(1 for r in pack_rows if r["reward_tx_hash"])
avg_delay = (
    sum(r["delay_blocks"] for r in pack_rows if r["delay_blocks"] is not None)
    / rewarded if rewarded else 0
)

col1, col2, col3 = st.columns(3)

col1.metric("Total Packs", total_packs)
col2.metric("Rewarded Packs", rewarded)
col3.metric("Avg Reward Delay (blocks)", round(avg_delay, 2))

# ============================================================
# PACK TABLE
# ============================================================

st.subheader("📦 Pack Purchases")

st.dataframe(
    pack_rows,
    use_container_width=True
)

# ============================================================
# FILTER + REWARD TABLE
# ============================================================

st.subheader("🎁 Reward Tokens")

buyers = sorted({r["buyer"] for r in pack_rows})
selected_buyer = st.selectbox("Filter by Buyer", ["All"] + buyers)

filtered_rewards = reward_rows
if selected_buyer != "All":
    filtered_rewards = [
        r for r in reward_rows if r["buy_tx_hash"] in {
            p["buy_tx_hash"] for p in pack_rows if p["buyer"] == selected_buyer
        }
    ]

st.dataframe(
    filtered_rewards,
    use_container_width=True
)

# ============================================================
# FOOTER
# ============================================================

st.caption("Data source: Base Blockscout | Built with Streamlit")

