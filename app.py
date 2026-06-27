import streamlit as st
import yfinance as yf
import pandas as pd
import re

# Set page configuration
st.set_page_config(page_title="Universal Portfolio Dashboard", layout="wide")
st.title("📊 Universal Investment Dashboard")
st.subheader("Your personalized, auto-updating market feed")

# 1. Handle URL Parameters for "Memory"
# Check if this user already has a saved sheet in their link
saved_sheet = st.query_params.get("sheet", "")

st.sidebar.header("User Setup")
if not saved_sheet:
    st.sidebar.info("👋 Welcome! Paste your Google Sheet link below to create your permanent dashboard.")

# Text input for the Google Sheet Link
sheet_link = st.sidebar.text_input("Google Sheet Share Link:", value=saved_sheet, type="password")

# Update the URL so they can bookmark it
if sheet_link and sheet_link != saved_sheet:
    st.query_params["sheet"] = sheet_link
    st.rerun()

if sheet_link:
    st.sidebar.success("✅ Link saved! **Bookmark this webpage now.** Every time you open this bookmark, your portfolio will load automatically.")
    
    # 2. Convert Google Sheet link to a readable CSV link
    try:
        # Changes standard share link to a direct CSV download link
        csv_url = re.sub(r'/edit.*$', '/export?format=csv', sheet_link)
        
        # Read the Google Sheet directly from the web
        raw_df = pd.read_csv(csv_url)
        
        # Clean columns to find the right data
        raw_df.columns = raw_df.columns.astype(str).str.strip().str.title()
        stock_col = next((c for c in raw_df.columns if c in ['Instrument', 'Stock', 'Symbol', 'Company', 'Ticker']), None)
        qty_col = next((c for c in raw_df.columns if c in ['Qty', 'Quantity', 'Shares']), None)
        price_col = next((c for c in raw_df.columns if c in ['Avg Price', 'Avg. Price', 'Average Price', 'Buy Price', 'Price']), None)
        
        if not (stock_col and qty_col and price_col):
            st.error("❌ Could not find the right columns. Make sure your Google Sheet has 'Stock', 'Qty', and 'Avg Price'.")
        else:
            clean_df = raw_df[[stock_col, qty_col, price_col]].dropna().copy()
            clean_df.columns = ['Stock', 'Qty', 'Avg Price']
            
            clean_df['Ticker'] = clean_df['Stock'].astype(str).apply(
                lambda x: x if x.endswith('.NS') or x.endswith('.BO') else f"{x.split('-')[0].strip()}.NS"
            )
            
            tickers = clean_df['Ticker'].tolist()
            
            # 3. Dynamic Live Fetching
            @st.cache_data(ttl=1800)
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

            with st.spinner("Fetching live market data..."):
                live_market_data = fetch_bulk_market_data(tickers)
            
            # 4. Calculate metrics
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
            
            # 5. Main KPI Cards Display
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Invested", f"₹{total_invested:,.2f}")
            m2.metric("Current Value", f"₹{total_current:,.2f}")
            m3.metric("Total Net P&L", f"₹{total_net_pl:,.2f}", f"{total_net_pct:.2f}%")
            m4.metric("Day's P&L", f"₹{total_day_pl:,.2f}", delta_color="inverse" if total_day_pl < 0 else "normal")
            
            st.markdown("---")
            
            # 6. Display Table
            st.subheader("📋 Holdings Performance")
            res_df = pd.DataFrame(rows)
            st.dataframe(
                res_df.style.format({'Invested Value': '₹{:.2f}', 'Current Value': '₹{:.2f}', 'Net P&L': '₹{:.2f}'}),
                use_container_width=True, hide_index=True
            )
            
            st.markdown("---")
            
            # 7. Smart News Section
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
        st.error(f"Could not read the Google Sheet. Please ensure it is set to 'Anyone with the link can view'. Error: {e}")
else:
    # Instructions displayed before user enters link
    st.info("""
    ### How to use this dashboard:
    1. Create a Google Sheet with your portfolio (Columns must be: **Stock**, **Qty**, **Avg Price**).
    2. Click 'Share' in Google Sheets and set general access to **'Anyone with the link'** (Viewer).
    3. Copy that link and paste it in the sidebar on the left. 
    """)
