import streamlit as st
from jackpot_tracker import process_buy_rips_event

st.set_page_config(page_title="Jackpot-500 Tracker", layout="centered")

st.title("🎰 Jackpot-500 Reward Tracker (Base)")
st.markdown("Scan **jackpot-500 pack** reward from a buy transaction")

buy_tx = st.text_input("Buy Transaction Hash")
buy_block = st.number_input("Buy Block Number", min_value=0, step=1)

if st.button("Scan Pack"):
    if not buy_tx or not buy_block:
        st.error("Please fill all fields.")
    else:
        with st.spinner("Scanning Base blocks..."):
            try:
                # buyer is auto-detected inside tracker in next version
                result = process_buy_rips_event(
                    buy_tx_hash=buy_tx,
                    buyer_address="",  # placeholder (will auto-detect next step)
                    buy_block=int(buy_block)
                )

                st.success("Scan completed")
                st.json(result)

                reward = result.get("reward")
                if reward:
                    st.subheader("Reward Tokens")
                    st.table(reward["reward_tokens"])
                else:
                    st.warning("Reward not found yet.")

            except Exception as e:
                st.error(str(e))
