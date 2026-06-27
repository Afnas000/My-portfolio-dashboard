import streamlit as st
import yfinance as yf
import pandas as pd

# Set page configuration
st.set_page_config(page_title="My Automated Portfolio Dashboard", layout="wide")
st.title("📊 Personal Investment Dashboard")
st.subheader("Real-time Tracking & Automated News Aggregator")

# 1. Hardcoded Portfolio Data from your sheet (Instruments mapped to NSE Yahoo Tickers)
# 1. Corrected Portfolio Data
portfolio_data = {
    'LT.NS': {'Name': 'Larsen & Toubro', 'Qty': 4, 'Avg Price': 4036.89},
    'HAL.NS': {'Name': 'Hindustan Aeronautics', 'Qty': 1, 'Avg Price': 3603.07},
    'SAIL.NS': {'Name': 'Steel Authority of India', 'Qty': 30, 'Avg Price': 161.22},
    'AXISBANK.NS': {'Name': 'Axis Bank', 'Qty': 4, 'Avg Price': 1371.88},
    'ANANTRAJ.NS': {'Name': 'Anant Raj', 'Qty': 10, 'Avg Price': 521.56},
    'WAAREEENER.NS': {'Name': 'Waaree Energies', 'Qty': 2, 'Avg Price': 3216.85},
    'HINDCOPPER.NS': {'Name': 'Hindustan Copper', 'Qty': 16, 'Avg Price': 545.50},
    'COFORGE.NS': {'Name': 'Coforge', 'Qty': 5, 'Avg Price': 1296.89},
    'CDSL.NS': {'Name': 'CDSL', 'Qty': 7, 'Avg Price': 1274.24},
    'TRENT.NS': {'Name': 'Trent Limited', 'Qty': 3, 'Avg Price': 3101.51},
    'DEVYANI.NS': {'Name': 'Devyani International', 'Qty': 43, 'Avg Price': 116.21},
    'HNGSNGBEES.NS': {'Name': 'Hang Seng BeES', 'Qty': 13, 'Avg Price': 520.04}
}

# 2. Fetch Live Market Data dynamically
tickers = list(portfolio_data.keys())

@st.cache_data(ttl=3600)  # Refresh data cache every hour
def fetch_market_data(ticker_list):
    data = {}
    for ticker in ticker_list:
        try:
            t = yf.Ticker(ticker)
            # Fetch current live price and previous close for day's change
            info = t.fast_info
            current_price = info['last_price']
            prev_close = info['previous_close']
            news = t.news[:3] # Get top 3 recent news articles
            data[ticker] = {
                'LTP': current_price,
                'Prev_Close': prev_close,
                'News': news
            }
        except Exception:
            # Fallback values if API fails temporarily
            data[ticker] = {'LTP': portfolio_data[ticker]['Avg Price'], 'Prev_Close': portfolio_data[ticker]['Avg Price'], 'News': []}
    return data

live_data = fetch_market_data(tickers)

# 3. Process and Calculate Portfolio Metrics
rows = []
total_invested = 0.0
total_current = 0.0
total_day_pl = 0.0

for ticker, holdings in portfolio_data.items():
    ltp = live_data[ticker]['LTP']
    prev_close = live_data[ticker]['Prev_Close']
    
    invested_val = holdings['Qty'] * holdings['Avg Price']
    current_val = holdings['Qty'] * ltp
    net_pl = current_val - invested_val
    net_chg_pct = (net_pl / invested_val) * 100
    
    day_pl = holdings['Qty'] * (ltp - prev_close)
    
    total_invested += invested_val
    total_current += current_val
    total_day_pl += day_pl
    
    rows.append({
        'Stock': holdings['Name'],
        'Ticker': ticker,
        'Qty': holdings['Qty'],
        'Avg Price': f"₹{holdings['Avg Price']:.2f}",
        'LTP': f"₹{ltp:.2f}",
        'Invested Value': invested_val,
        'Current Value': current_val,
        'Net P&L': net_pl,
        'Net Chg %': f"{net_chg_pct:.2f}%"
    })

total_net_pl = total_current - total_invested
total_net_pct = (total_net_pl / total_invested) * 100

# 4. Render KPI Cards on Top
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Invested", f"₹{total_invested:,.2f}")
m2.metric("Current Value", f"₹{total_current:,.2f}")
m3.metric("Total Net P&L", f"₹{total_net_pl:,.2f}", f"{total_net_pct:.2f}%")
m4.metric("Day's P&L", f"₹{total_day_pl:,.2f}", delta_color="inverse" if total_day_pl < 0 else "normal")

st.markdown("---")

# 5. Render Breakdown Table
st.subheader("📋 Holdings Breakdown")
df = pd.DataFrame(rows)
st.dataframe(
    df.style.format({'Invested Value': '₹{:.2f}', 'Current Value': '₹{:.2f}', 'Net P&L': '₹{:.2f}'}),
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# 6. Automated News Section
# 6. Automated News Section
# 6. Automated News Section
st.subheader("📰 Automated Stock News Feed")
news_found = False

def extract_news_info(article):
    """Smart function to hunt down the title and link no matter where Yahoo hides it."""
    # 1. Try standard locations first
    title = article.get('title', '')
    link = article.get('link', article.get('url', ''))
    publisher = article.get('publisher', article.get('source', ''))
    
    # 2. Check inside the new 'content' folder if Yahoo changed the structure
    if not title and 'content' in article and isinstance(article['content'], dict):
        content = article['content']
        title = content.get('title', '')
        link = content.get('canonicalUrl', content.get('url', link))
        provider = content.get('provider', {})
        if isinstance(provider, dict):
            publisher = provider.get('displayName', publisher)
            
    return title, link, publisher

for ticker in tickers:
    articles = live_data[ticker].get('News', [])
    if articles:
        valid_articles = [a for a in articles if isinstance(a, dict)]
        if valid_articles:
            # We will only open the expander if we actually find real news
            real_news_count = 0
            news_ui = []
            
            for article in valid_articles:
                title, link, publisher = extract_news_info(article)
                
                # Only display if it actually found a real title
                if title and title != 'No Title Available':
                    real_news_count += 1
                    news_ui.append(f"**[{title}]({link})**\n\n<small style='color:gray;'>Source: {publisher}</small>")
            
            # If we found at least one real article, show it!
            if real_news_count > 0:
                news_found = True
                with st.expander(f"News for {portfolio_data[ticker]['Name']} ({ticker})"):
                    for news_item in news_ui:
                        st.markdown(news_item, unsafe_allow_html=True)
                        st.markdown("---")

if not news_found:
    st.info("No active market news found for your specific stock symbols in the last 24 hours. (Check back later!)")
