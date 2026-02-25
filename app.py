import streamlit as st
from jackpot_tracker import scan_latest_jackpot_packs

st.set_page_config(
    page_title="Jackpot-500 Scanner",
    page_icon="🎰",
    layout="wide"
)

st.title("🎰 Jackpot-500 Scanner (Base)")
st.caption("Quét on-chain API để tìm thông tin các pack jackpot-500 đã được mua và trả thưởng.")

# =========================
# USER INPUT
# =========================
col1, col2 = st.columns([1, 2])
with col1:
    target_count = st.number_input(
        "Số lượng pack jackpot-500 cần quét",
        min_value=1,
        max_value=50,
        value=5,
        step=1
    )
    scan_btn = st.button("🚀 Bắt đầu scan", type="primary")

# =========================
# SCAN ACTION
# =========================
if scan_btn:
    with st.spinner("⏳ Đang quét dữ liệu on-chain... việc này có thể mất vài chục giây."):
        try:
            results = scan_latest_jackpot_packs(target_count)

            if not results:
                st.warning("⚠️ Không tìm thấy pack nào hoặc API đang bị giới hạn.")
            else:
                st.success(f"✅ Đã tìm được {len(results)} pack jackpot-500")

                for i, pack in enumerate(results, start=1):
                    with st.expander(f"🎁 Pack #{i} - Block: {pack['buy_block']}", expanded=False):
                        st.markdown(f"**Buyer**: `{pack['buyer']}`")
                        st.markdown(f"**Buy TX**: `{pack['buy_tx_hash']}`")

                        reward = pack.get("reward")
                        if reward:
                            st.write("---")
                            st.markdown(f"**Reward TX**: `{reward['reward_tx_hash']}`")
                            st.markdown(f"**Reward Block**: `{reward['reward_block']}` _(Delay: {reward['delay_blocks']} blocks)_")
                            
                            st.write("**Reward Tokens:**")
                            for t in reward["reward_tokens"]:
                                st.success(f"💰 {t['amount']:,.4f} **{t['token_symbol']}**")
                        else:
                            st.warning("⚠️ Không tìm thấy reward payout (có thể delay quá lâu hoặc lỗi hợp đồng).")

        except Exception as e:
            st.error("❌ Có lỗi xảy ra kết nối với Blockscout API.")
            st.exception(e)