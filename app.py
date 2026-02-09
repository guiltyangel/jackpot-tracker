import streamlit as st
from jackpot_tracker import scan_latest_jackpot_packs

st.set_page_config(
    page_title="Jackpot-500 Scanner",
    layout="wide"
)

st.title("🎰 Jackpot-500 Scanner (Base)")
st.caption(
    "Scan ngược on-chain cho tới khi tìm đủ số pack jackpot-500 theo yêu cầu."
)

# =========================
# USER INPUT
# =========================

target_count = st.number_input(
    "Số lượng pack jackpot-500 cần quét",
    min_value=1,
    max_value=50,
    value=5,
    step=1
)

scan_btn = st.button("🚀 Bắt đầu scan")

# =========================
# SCAN ACTION
# =========================

if scan_btn:
    st.info("⏳ Đang scan on-chain… việc này có thể mất vài phút.")

    try:
        results = scan_latest_jackpot_packs(target_count)

        if not results:
            st.warning("Không tìm thấy pack nào.")
        else:
            st.success(f"✅ Đã tìm được {len(results)} pack jackpot-500")

            for i, pack in enumerate(results, start=1):
                with st.expander(f"🎁 Pack #{i}", expanded=False):
                    st.write("**Buy TX**:", pack["buy_tx_hash"])
                    st.write("**Buyer**:", pack["buyer"])
                    st.write("**Buy Block**:", pack["buy_block"])

                    reward = pack.get("reward")
                    if reward:
                        st.write("**Reward TX**:", reward["reward_tx_hash"])
                        st.write("**Reward Block**:", reward["reward_block"])
                        st.write("**Delay (blocks)**:", reward["delay_blocks"])

                        st.write("**Reward Tokens:**")
                        for t in reward["reward_tokens"]:
                            st.write(
                                f"- {t['amount']} {t['token_symbol']} "
                                f"({t['token_address']})"
                            )
                    else:
                        st.warning("⚠️ Không tìm thấy reward payout.")

    except Exception as e:
        st.error("❌ Có lỗi xảy ra trong quá trình scan")
        st.exception(e)
