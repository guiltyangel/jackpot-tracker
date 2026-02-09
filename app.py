import streamlit as st
from jackpot_tracker import scan_latest_jackpot_packs

st.set_page_config(page_title="Jackpot-500 Scanner", layout="centered")

st.title("🎰 Jackpot-500 Pack Scanner (Base)")
st.markdown("Scan backward until enough **jackpot-500 packs** are found")

target_count = st.number_input(
    "Number of jackpot-500 packs to scan",
    min_value=1,
    step=1
)

if st.button("Start Scan"):
    with st.spinner("Scanning backward from latest block..."):
        try:
            results = scan_latest_jackpot_packs(
                target_count=int(target_count)
            )

            st.success(f"Found {len(results)} jackpot-500 packs")

            for i, r in enumerate(results, 1):
                st.subheader(f"Pack #{i}")
                st.json(r)

        except Exception as e:
            st.error(str(e))
