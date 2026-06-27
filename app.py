import streamlit as st
import yfinance as yf
import pandas as pd

# Set page configuration
st.set_page_config(page_title="Universal Portfolio Dashboard", layout="wide")
st.title("📊 Universal Investment Dashboard")
st.subheader("Upload your portfolio for instant tracking & automated news")

# 1. Sidebar File Uploader
st.sidebar.header("Upload Portfolio")
uploaded_file = st.sidebar.file_uploader("Upload your Excel (.xlsx) or CSV file", type=["xlsx", "csv"])

# Helper function to match generic uploaded columns to what we need
def clean_uploaded_df(df):
    df.columns = df.columns.astype(str).str.strip().str.title()
    
    # Try to find standard column variations
    stock_col = next((c for c in df.columns if c in ['Instrument', 'Stock', 'Symbol', 'Company', 'Ticker']), None)
    qty_col = next((c for c in df.columns if c in ['Qty', 'Quantity', 'Shares']), None)
    price_col = next((c for c in df.columns if c in ['Avg Price', 'Avg. Price', 'Average Price', 'Buy Price', 'Price']), None)
    
    if stock_col and qty_col and price_col:
        renamed_df = df[[stock_col, qty_col, price_col]].dropna().copy()
        renamed_df.columns = ['Stock', 'Qty', 'Avg Price']
        return renamed_df
    return None

if uploaded_file is not None:
    try:
        # Read file depending on extension
        if uploaded_file.name.endswith('.xlsx'):
            raw_df = pd.read_excel(uploaded_file)
        else:
            raw_df = pd.read_csv(uploaded_file)
            
        clean_df = clean_uploaded_df(raw_df)
        
        if clean_df is None:
            st.error("❌ Could not automatically detect columns. Ensure your file contains columns named 'Stock' (or 'Instrument'), 'Qty', and 'Avg Price'.")
        else:
            # Prepare ticker formatting (Appends .NS assuming NSE by default)
            clean_df['Ticker'] = clean_df['Stock'].astype(str).apply(
                lambda x: x if x.endswith('.NS') or x.endswith('.BO') else f"{x.split('-')[0].strip()}.NS"
            )
            
            # 2. Dynamic Live Fetching
            tickers = clean_df['Ticker'].tolist()
            
            @st.cache_data(ttl=1800) # Cache for 30 minutes to speed up multi-user performance
            def fetch_bulk_market_data(ticker_list):
                data = {}
                for ticker in ticker_list:
                    try:
                        t = yf.Ticker(ticker)
                        info = t.fast_info
                        data[ticker] = {
                            'LTP': info['last_price'],
                            'Prev_Close': info['previous_close'],
                            'News': t.news[:3]
                        }
                    except:
                        data[ticker] = {'LTP': None, 'Prev_Close': None, 'News': []}
                return data

            st.info("🔄 Fetching live market data for uploaded stocks...")
            live_market_data = fetch_bulk_market_data(tickers)
            
            # 3. Calculate metrics dynamically
            rows = []
            total_invested = 0.0
            total_current = 0.0
            total_day_pl = 0.0
            
            for _, row in clean_df.iterrows():
                tk = row['Ticker']
                qty = float(str(row['Qty']).replace(',', ''))
                avg_p = float(str(row['Avg Price']).replace(',', ''))
                
                market = live_market_data.get(tk, {'LTP': None, 'Prev_Close': None})
                ltp = market['LTP'] if market['LTP'] is not None else avg_p
                prev_close = market['Prev_Close'] if market['Prev_Close'] is not None else avg_p
                
                invested_val = qty * avg_p
                current_val = qty * ltp
                net_pl = current_val - invested_val
                net_chg_pct = (net_pl / invested_val) * 100 if invested_val > 0 else 0
                day_pl = qty * (ltp - prev_close)
                
                total_invested += invested_val
                total_current += current_val
                total_day_pl += day_pl
                
                rows.append({
                    'Stock': row['Stock'],
                    'Qty': qty,
                    'Avg Price': f"₹{avg_p:,.2f}",
                    'LTP': f"₹{ltp:,.2f}",
                    'Invested Value': invested_val,
                    'Current Value': current_val,
                    'Net P&L': net_pl,
                    'Net Chg %': f"{net_chg_pct:.2f}%"
                })
                
            total_net_pl = total_current - total_invested
            total_net_pct = (total_net_pl / total_invested) * 100 if total_invested > 0 else 0
            
            # 4. Main KPI Cards Display
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Invested", f"₹{total_invested:,.2f}")
            m2.metric("Current Value", f"₹{total_current:,.2f}")
            m3.metric("Total Net P&L", f"₹{total_net_pl:,.2f}", f"{total_net_pct:.2f}%")
            m4.metric("Day's P&L", f"₹{total_day_pl:,.2f}", delta_color="inverse" if total_day_pl < 0 else "normal")
            
            st.markdown("---")
            
            # 5. Display Table
            st.subheader("📋 Holdings Performance")
            res_df = pd.DataFrame(rows)
            st.dataframe(
                res_df.style.format({'Invested Value': '₹{:.2f}', 'Current Value': '₹{:.2f}', 'Net P&L': '₹{:.2f}'}),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            
            # 6. Smart News Section
            st.subheader("📰 Automated Stock News Feed")
            news_found = False
            
            for _, row in clean_df.iterrows():
                tk = row['Ticker']
                articles = live_market_data.get(tk, {}).get('News', [])
                valid_articles = [a for a in articles if isinstance(a, dict)]
                
                if valid_articles:
                    news_found = True
                    with st.expander(f"News for {row['Stock']} ({tk})"):
                        for article in valid_articles:
                            content = article.get('content', article)
                            title = content.get('title', article.get('title', 'No Title Available'))
                            link = article.get('link', '#')
                            if isinstance(content.get('clickThroughUrl'), dict):
                                link = content['clickThroughUrl'].get('url', link)
                            elif 'url' in content:
                                link = content.get('url')
                                
                            publisher = article.get('publisher', 'Financial News')
                            if isinstance(content.get('provider'), dict):
                                publisher = content['provider'].get('displayName', publisher)
                                
                            st.markdown(f"**[{title}]({link})**")
                            st.caption(f"Source: {publisher}")
                            
            if not news_found:
                st.info("No fresh news headlines available for your portfolio's tickers right now.")
                
    except Exception as e:
        st.error(f"Error parsing file: {e}")
else:
    # Instructions displayed before user uploads a file
    st.info("💡 **Welcome!** Please upload an Excel sheet or CSV containing your portfolio columns. Ensure your table has clear column headers like: **Instrument/Stock, Qty, and Avg Price** to begin.")
