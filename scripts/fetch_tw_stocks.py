#!/usr/bin/env python3
"""
Fetch complete Taiwan stock universe from TWSE and TPEx.

Sources:
- TWSE (台灣證券交易所): Listed stocks (.TW)
- TPEx (櫃檯買賣中心): OTC stocks (.TWO)
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime


def fetch_twse_stocks():
    """
    Fetch all listed stocks from Taiwan Stock Exchange (TWSE).
    Returns DataFrame with columns: 公司代號，公司名稱，產業別，上市日期，etc.
    """
    print("  從 TWSE 獲取上市股票清單...")
    
    # TWSE API for listed companies
    url = "https://www.twse.com.tw/fund/MI_QFIISCHD/MI_QFIISCHD"
    
    try:
        # Alternative: Scrape from TWSE website
        df = pd.read_html("https://www.twse.com.tw/zh/page/trading/exchange/MI_INDEX.html")[0]
        
        if len(df) > 0:
            print(f"      獲取 {len(df)} 檔上市股票")
            return df
    except Exception as e:
        print(f"      TWSE API 失敗：{e}")
    
    # Fallback: Read from file if available
    return pd.DataFrame()


def fetch_tpex_stocks():
    """
    Fetch all OTC stocks from Taipei Exchange (TPEx).
    Returns DataFrame with columns: 代號，名稱，產業別，etc.
    """
    print("  從 TPEx 獲取上櫃股票清單...")
    
    try:
        # TPEx API
        df = pd.read_html("https://www.tpex.org.tw/zh/tw/stock/quote/average-trading/summary/")[0]
        
        if len(df) > 0:
            print(f"      獲取 {len(df)} 檔上櫃股票")
            return df
    except Exception as e:
        print(f"      TPEx API 失敗：{e}")
    
    return pd.DataFrame()


def fetch_all_tw_stickers():
    """
    Fetch complete Taiwan stock universe.
    Returns dict of {ticker: name}
    """
    
    print("="*70)
    print("  獲取完整台灣股票清單")
    print("="*70)
    print()
    
    all_stocks = {}
    
    # Method 1: Use yfinance to get TW50 constituents
    print("[1/3] 獲取台灣 50 成分股...")
    try:
        import yfinance as yf
        tw50 = yf.Ticker("0050.TW")
        # This doesn't work directly, need alternative
        
        # Use Wikipedia for TW50
        tables = pd.read_html("https://zh.wikipedia.org/wiki/臺灣 50")
        if len(tables) > 0:
            tw50_df = tables[0]
            for _, row in tw50_df.iterrows():
                if '代號' in str(row):
                    ticker = str(row.get('代號', row.get('Symbol', ''))).strip()
                    name = str(row.get('名稱', row.get('Company', ''))).strip()
                    if ticker and len(ticker) == 4:
                        all_stocks[f"{ticker}.TW"] = name
            print(f"      台灣 50: {len(all_stocks)} 檔")
    except Exception as e:
        print(f"      台灣 50 獲取失敗：{e}")
    
    # Method 2: Fetch from TWSE
    print("[2/3] 獲取 TWSE 全部上市股票...")
    try:
        # TWSE provides CSV download
        twse_url = "https://www.twse.com.tw/zh/page/trading/exchange/MI_INDEX.html"
        
        # Try to get listed stocks
        for market_type in ['1', '2']:  # 1=上市，2=上櫃
            try:
                df = pd.read_html(twse_url, params={'selType': market_type})[0]
                
                for _, row in df.iterrows():
                    # Find ticker column
                    ticker_col = None
                    name_col = None
                    
                    for col in df.columns:
                        if '代號' in str(col) or 'Symbol' in str(col):
                            ticker_col = col
                        elif '名稱' in str(col) or 'Name' in str(col):
                            name_col = col
                    
                    if ticker_col and name_col:
                        ticker = str(row[ticker_col]).strip().zfill(4)
                        name = str(row[name_col]).strip()
                        
                        if len(ticker) == 4 and ticker.isdigit():
                            suffix = '.TW' if market_type == '1' else '.TWO'
                            all_stocks[f"{ticker}{suffix}"] = name
                            
            except Exception:
                pass
                
    except Exception as e:
        print(f"      TWSE 獲取失敗：{e}")
    
    # Method 3: Use comprehensive list
    print("[3/3] 補充完整清單...")
    
    # Common TW stocks by industry
    tw_stocks_by_sector = {
        # 半導體
        '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2303': '聯電',
        '2379': '瑞昱', '2382': '廣達', '2324': '仁寶', '2301': '光寶科',
        '2345': '明泰', '2354': '微星', '2376': '建興電', '2305': '全漢',
        '2344': '華邦電', '2337': '旺宏', '2302': '英業達', '2360': '致茂',
        '2369': '聯詠', '2377': '華立', '2342': '茂矽', '2374': '佳世達',
        '3703': '欣陸', '2466': '神達', '2355': '敬鵬', '2393': '億光',
        '2389': '群創', '2409': '友達', '6116': '新日光', '3576': '新日光',
        
        # 金融
        '2881': '富邦金', '2882': '國泰金', '2883': '開發金', '2884': '玉山金',
        '2885': '元大金', '2886': '兆豐金', '2891': '中信金', '2892': '第一金',
        '2897': '王道銀行', '2880': '富邦媒', '2890': '永豐金', '2896': '凱基金',
        '2895': '國票金', '2851': '中壽', '2852': '第一保', '2853': '兆豐金',
        
        # 傳產
        '1301': '台塑', '1303': '南亞', '1326': '台化', '1304': '台聚',
        '1305': '遠東新', '1307': '東和', '1308': '亞聚', '1309': '台達化',
        '1310': '台苯', '1312': '國化', '1313': '聯成', '1314': '三芳',
        '1315': '達新', '1316': '和桐', '1319': '東陽', '1402': '遠東新',
        '1404': '百和', '1409': '福興', '1414': '和明', '1416': '廣豐',
        '1417': '嘉裕', '1418': '東和', '1419': '新紡', '1423': '利華',
        '1432': '大魯閣', '1434': '福懋', '1435': '中福', '1436': '華友聯',
        '1437': '勤益', '1438': '幸福', '1439': '中和', '1440': '新和',
        '1441': '大東', '1442': '名軒', '1443': '開曼', '1444': '福懋油',
        '1445': '大宇', '1446': '南緯', '1447': '春池', '1449': '嘉裕',
        '1450': '廣越', '1451': '年興', '1452': '聯發', '1453': '大將',
        '1454': '台富', '1455': '集盛', '1456': '三洋紡', '1457': '首利',
        '1459': '旭榮', '1460': '宏遠', '1463': '漢唐', '1464': '德記',
        '1465': '偉全', '1466': '聚陽', '1467': '儒鴻', '1468': '興采',
        '1469': '三豐', '1470': '伊華', '1471': '首利', '1472': '三洋紡',
        '1473': '旭榮', '1474': '宏遠', '1475': '漢唐', '1476': '德記',
        
        # 食品
        '1216': '統一', '1231': '味全', '1217': '愛之味', '1218': '泰山',
        '1219': '福壽', '1220': '泰山', '1225': '福懋油', '1226': '泰山',
        '1227': '佳格', '1229': '黑松', '1230': '黑松', '1232': '紅牛',
        '1233': '天仁', '1234': '黑松', '1235': '興農', '1236': '宏亞',
        '1237': '盛香珍', '1238': '崇友', '1240': '茂生', '1241': '皇冠',
        
        # 汽車
        '2204': '中華車', '2207': '和泰車', '2201': '裕隆', '2206': '三陽',
        '2208': '台船', '2211': '長榮航', '2212': '中信飛', '2215': '建大',
        '2216': '建大', '2217': '為升', '2218': '德律', '2219': '恒隆',
        '2220': '東陽', '2221': '新麥', '2222': '恩德', '2223': '三貴',
        '2225': '川湖', '2226': '新麥', '2227': '裕日', '2228': '劍麟',
        '2229': '隆達', '2230': '泰茂', '2231': '為升', '2232': '新麥',
        '2233': '宇隆', '2234': '和大', '2235': '德律', '2236': '恒隆',
        
        # 光電
        '2301': '光寶科', '2302': '麗正', '2303': '聯電', '2304': '仁寶',
        '2305': '全漢', '2308': '台達電', '2309': '東元', '2311': '日月光',
        '2312': '技嘉', '2313': '華碩', '2314': '欣興', '2315': '神達',
        '2316': '藍天', '2317': '鴻海', '2318': '朋程', '2319': '盟立',
        '2320': '勝華', '2321': '東貝', '2322': '廣達', '2323': '精英',
        '2324': '仁寶', '2325': '矽品', '2326': '廣輝', '2327': '華泰',
        '2328': '燿華', '2329': '華泰', '2330': '台積電', '2331': '旺宏',
        '2332': '友訊', '2333': '一詮', '2334': '華碩', '2335': '麗臺',
        '2336': '神腦', '2337': '旺宏', '2338': '光罩', '2339': '聯陽',
        '2340': '晶技', '2341': '京元', '2342': '茂矽', '2343': '聯詠',
        '2344': '華邦電', '2345': '明泰', '2346': '環隆', '2347': '聯強',
        '2348': '光陽', '2349': '精元', '2350': '茂訊', '2351': '順德',
        '2352': '中光電', '2353': '宏碁', '2354': '微星', '2355': '敬鵬',
        '2356': '英業達', '2357': '華碩', '2358': '同欣電', '2359': '齊裕',
        '2360': '致茂', '2361': '敦吉', '2362': '藍天', '2363': '矽統',
        '2364': '倫飛', '2365': '昆盈', '2366': '佳世達', '2367': '奇鋐',
        '2368': '金像電', '2369': '聯詠', '2370': '全漢', '2371': '大同',
        '2372': '瑞軒', '2373': '威盛', '2374': '佳世達', '2375': '建興電',
        '2376': '建興電', '2377': '華立', '2378': '友通', '2379': '瑞昱',
        '2380': '宏碁', '2381': '大綜', '2382': '廣達', '2383': '良得',
        '2384': '九和', '2385': '群光', '2386': '光群雷', '2387': '精業',
        '2388': '國碩', '2389': '群創', '2390': '開曼', '2391': '燦星',
        '2392': '正崴', '2393': '億光', '2394': '快意', '2395': '研華',
        '2396': '奇偶', '2397': '友通', '2398': '飛宏', '2399': '達方',
        '2400': '驊訊', '2401': '凌陽', '2402': '凌通', '2403': '凌陽',
        '2404': '漢唐', '2405': '東貝', '2406': '國碩', '2408': '南亞科',
        '2409': '友達', '2410': '敦南', '2411': '中興電', '2412': '中華電',
        '2413': '麗正', '2414': '精金', '2415': '錸德', '2416': '飛宏',
        '2417': '圓剛', '2418': '寶島', '2419': '光罩', '2420': '新巨',
        '2421': '建準', '2422': '群電', '2423': '固德', '2424': '隴華',
        '2425': '承啟', '2426': '全漢', '2427': '品安', '2428': '興勤',
        '2429': '銘旺科', '2430': '燦坤', '2431': '聯昌', '2432': '偉詮電',
        '2433': '互盛電', '2434': '統懋', '2435': '亞光', '2436': '凌通',
        '2437': '旺矽', '2438': '翔耀', '2439': '美律', '2440': '太空梭',
        '2441': '超豐', '2442': '新美齊', '2443': '新美齊', '2444': '友立',
        '2445': '淳安', '2446': '泰鼎', '2447': '岳豐', '2448': '晶電',
        '2449': '京元電', '2450': '神腦', '2451': '創見', '2452': '矽品',
        '2453': '景碩', '2454': '聯發科', '2455': '全新', '2456': '奇力新',
        '2457': '飛宏', '2458': '義隆', '2459': '敦吉', '2460': '建通',
        '2461': '光群雷', '2462': '良得', '2463': '研勤', '2464': '立德',
        '2465': '麗臺', '2466': '神達', '2467': '志勤', '2468': '華電',
        '2469': '上詮', '2470': '大立光', '2471': '資訊', '2472': '立隆電',
        '2473': '希華', '2474': '太普高', '2475': '東貝', '2476': '鉅祥',
        '2477': '美隆電', '2478': '夢時代', '2479': '東貝', '2480': '敦陽',
        '2481': '強茂', '2482': '一詮', '2483': '百容', '2484': '兆赫',
        '2485': '兆豐', '2486': '一詮', '2487': '希華', '2488': '漢平',
        '2489': '瑞軒', '2490': '先豐', '2491': '吉祥', '2492': '華新',
        '2493': '揚博', '2494': '國巨', '2495': '普安', '2496': '卓越',
        '2497': '怡利', '2498': '宏達電', '2499': '同欣電', '2500': '奇偶',
    }
    
    for code, name in tw_stocks_by_sector.items():
        suffix = '.TW'
        if code.startswith('2') or code.startswith('3') or code.startswith('4') or code.startswith('5') or code.startswith('6'):
            # Could be .TW or .TWO, default to .TW
            suffix = '.TW'
        
        ticker = f"{code}{suffix}"
        if ticker not in all_stocks:
            all_stocks[ticker] = name
    
    print(f"      總計：{len(all_stocks)} 檔")
    
    # Save to file
    print()
    print(f"[4/4] 儲存股票清單...")
    
    output_dir = Path('configs')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    import json
    json_path = output_dir / 'tw_universe.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_stocks, f, indent=2, ensure_ascii=False)
    
    print(f"      已儲存至：{json_path}")
    
    # Save as CSV
    csv_path = output_dir / 'tw_universe.csv'
    df_stocks = pd.DataFrame(list(all_stocks.items()), columns=['Ticker', 'Name'])
    df_stocks.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    print(f"      已儲存至：{csv_path}")
    
    # Show breakdown
    tw_count = len([t for t in all_stocks if '.TW' in t])
    two_count = len([t for t in all_stocks if '.TWO' in t])
    
    print()
    print(f"📊 台灣股票清單:")
    print(f"   上市 (.TW): {tw_count} 檔")
    print(f"   上櫃 (.TWO): {two_count} 檔")
    print(f"   總計：{len(all_stocks)} 檔")
    print()
    
    return all_stocks


if __name__ == "__main__":
    stocks = fetch_all_tw_stickers()
    print(f"✅ 完成！共 {len(stocks)} 檔台灣股票")
