import streamlit as st
from jackpot_tracker import process_buy_rips_event

st.set_page_config(page_title="Jackpot-500 Tracker", layout="centered")

st.title("🎰 Jackpot-500 Reward Tracker (Base)")

st.markdown("Track reward payout after a **jackpot-500** buy on Base.")

buy_tx = st.text_input("Buy Transaction Hash")
buyer = st.text_input("Buyer Address")
buy_block = st.number_input("Buy Block Number", min_value=0, step=1)

if st.button("Track Reward"):
    if not buy_tx or not buyer or not buy_block:
        st.error("Please fill all fields.")
    else:
        with st.spinner("Scanning Base blocks..."):
            try:
                result = process_buy_rips_event(
                    buy_tx_hash=buy_tx,
                    buyer_address=buyer,
                    buy_block=int(buy_block)
                )

                st.success("Done!")

                st.subheader("Result")
                st.json(result)

                reward = result.get("reward")
                if reward:
                    st.subheader("Reward Tokens")
                    st.table(reward["reward_tokens"])
                else:
                    st.warning("Reward not found yet.")

            except Exception as e:
                st.error(str(e))
