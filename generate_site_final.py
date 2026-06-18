#!/usr/bin/env python3
"""
節約生活 今日のお買い得情報 - サイト自動生成システム

使い方:
  pip install requests
  set RAKUTEN_APP_ID=あなたのアプリID
  set RAKUTEN_ACCESS_KEY=あなたのアクセスキー
  set RAKUTEN_AFFILIATE_ID=あなたのアフィリエイトID
  py generate_site_final.py --open
  py generate_site_final.py --demo   (APIキー不要でテスト)
"""

import os, sys, json, time, html, argparse, urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests が必要です")
    sys.exit(1)

CONFIG = {
    "app_id":       os.environ.get("RAKUTEN_APP_ID", ""),
    "access_key":   os.environ.get("RAKUTEN_ACCESS_KEY", ""),
    "affiliate_id": os.environ.get("RAKUTEN_AFFILIATE_ID", ""),
    "site_title":   "節約生活 今日のお買い得情報",
    "site_desc":    "毎日更新！楽天市場の激安セール品を厳選してご紹介。節約生活を応援します！",
    "output_dir":   "docs",
    "min_review_count": 5,
    "min_review_avg":   3.8,
    "max_price":    30000,
    "min_price":    100,
    "keywords": [
        "セール 食品", "特価 日用品", "訳あり 食品 送料無料",
        "在庫処分 お買い得", "ポイント10倍", "セール 美容",
        "タイムセール 生活雑貨", "お試し 送料無料",
    ],
}

DEMO_ITEMS = [
    {"name":"吉野家公式 冷凍牛丼の具 120g×28袋","price":9990,"price_fmt":"¥9,990","aff_rate":4.0,"est_fee":399,"est_fee_fmt":"¥399","review_count":5583,"review_avg":4.59,"stars":"★★★★★","url":"#","image":"","shop":"吉野家公式ショップ","original_price":12800,"discount_pct":21.9},
    {"name":"骨取りサバ切身 1kg 無塩 送料無料","price":2790,"price_fmt":"¥2,790","aff_rate":4.0,"est_fee":111,"est_fee_fmt":"¥111","review_count":17357,"review_avg":4.51,"stars":"★★★★★","url":"#","image":"","shop":"越前かに職人甲羅組","original_price":3980,"discount_pct":29.9},
    {"name":"リンガーハット 長崎ちゃんぽん8食セット","price":3800,"price_fmt":"¥3,800","aff_rate":4.0,"est_fee":152,"est_fee_fmt":"¥152","review_count":3555,"review_avg":4.69,"stars":"★★★★★","url":"#","image":"","shop":"リンガーハット楽天市場店","original_price":4500,"discount_pct":15.6},
    {"name":"国産鶏の炭火焼き 100g×6袋 レトルト","price":2880,"price_fmt":"¥2,880","aff_rate":4.0,"est_fee":115,"est_fee_fmt":"¥115","review_count":6136,"review_avg":4.48,"stars":"★★★★☆","url":"#","image":"","shop":"ミート21ショップ","original_price":3600,"discount_pct":20.0},
    {"name":"カップヌードル ケース 78g×20食入","price":4182,"price_fmt":"¥4,182","aff_rate":4.0,"est_fee":167,"est_fee_fmt":"¥167","review_count":295,"review_avg":4.21,"stars":"★★★★☆","url":"#","image":"","shop":"楽天24","original_price":5200,"discount_pct":19.6},
    {"name":"ごまいっぱいタルトクッキー 18個入 送料無料","price":1480,"price_fmt":"¥1,480","aff_rate":4.0,"est_fee":59,"est_fee_fmt":"¥59","review_count":4599,"review_avg":4.68,"stars":"★★★★★","url":"#","image":"","shop":"なみさとねっと","original_price":1980,"discount_pct":25.3},
]
for i, item in enumerate(DEMO_ITEMS):
    item["rank"] = i + 1


def make_affiliate_link(url: str, affiliate_id: str) -> str:
    if not affiliate_id or url == "#":
        return url
    encoded = urllib.parse.quote(url, safe="")
    return f"https://hb.afl.rakuten.co.jp/ichiba/{affiliate_id}/?pc={encoded}&link_type=picttext"


def fetch_items(app_id: str, access_key: str, affiliate_id: str) -> List[Dict]:
    session = requests.Session()
    session.headers.update({"Accept-Language": "ja"})
    all_items, seen = [], set()

    for keyword in CONFIG["keywords"]:
        print(f"  🔍 収集中: {keyword}")
        try:
            r = session.get(
                "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401",
                params={"applicationId": app_id, "accessKey": access_key,
                        "keyword": keyword, "hits": 20, "genreId": 0, "format": "json"},
                timeout=15)
            if r.status_code != 200:
                print(f"    ⚠️  エラー {r.status_code}")
                continue
            raw_items = r.json().get("Items", [])
            added = 0
            for raw in raw_items:
                item = raw.get("Item", raw)
                norm = normalize(item, affiliate_id)
                if norm and norm["url"] not in seen:
                    seen.add(norm["url"])
                    all_items.append(norm)
                    added += 1
            print(f"    → {added} 件追加")
        except Exception as e:
            print(f"    ⚠️  {e}")
        time.sleep(1.0)

    all_items.sort(key=lambda x: x["aff_rate"] * (x["review_avg"] / 5), reverse=True)
    for i, item in enumerate(all_items):
        item["rank"] = i + 1
    return all_items


CATEGORY_KEYWORDS = {
    "food":    ["食品","鮭","さば","うなぎ","牛","豚","味噌","醤油","餃子","梅","蜂蜜","コーヒー","お菓子","せんべい","バームクーヘン","ちんすこう","きくらげ","ほっけ","大麦","雑穀","みそ汁","グルメ","柿","みかん","サーモン","マンゴー","海苔","高菜","うな重","丼","鯖","イワシ","干物","えびせん","牛丼","豚丼","鶏"],
    "beauty":  ["美容","シャンプー","コスメ","美白","眉毛","目元","美容液","クリーム","パウダー","セラム","フェイス","オールインワン","化粧","ローション","乳液"],
    "fashion": ["tシャツ","シャツ","アビレックス","ウエア"],
    "daily":   ["フライパン","鍋","マット","マスク","電卓","sdカード","洗濯","日用品","雑貨"],
}

def categorize(name: str) -> str:
    n = name.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in n for k in kws):
            return cat
    return "other"


def normalize(raw: Dict, affiliate_id: str) -> Optional[Dict]:
    try:
        name     = raw.get("itemName", "").strip()
        price    = int(raw.get("itemPrice", 0))
        aff_rate = float(raw.get("affiliateRate", 0))
        rev_c    = int(raw.get("reviewCount", 0))
        rev_a    = float(raw.get("reviewAverage", 0))
        url      = raw.get("itemUrl", "")
        shop     = raw.get("shopName", "").strip()
        images   = raw.get("mediumImageUrls", [])
        image    = ""
        if images:
            img = images[0]
            image = img if isinstance(img, str) else img.get("imageUrl", "")

        if not name or price <= 0 or not url: return None
        if price < CONFIG["min_price"] or price > CONFIG["max_price"]: return None
        if rev_c < CONFIG["min_review_count"]: return None
        if rev_a < CONFIG["min_review_avg"]: return None

        orig  = int(raw.get("itemPriceMax1", 0)) or None
        disc  = round((1 - price / orig) * 100, 1) if orig and orig > price else None
        est   = int(price * aff_rate / 100)
        stars = "★" * round(rev_a) + "☆" * (5 - round(rev_a))

        return {"name": name[:70], "price": price, "price_fmt": f"¥{price:,}",
                "aff_rate": aff_rate, "est_fee": est, "est_fee_fmt": f"¥{est:,}",
                "review_count": rev_c, "review_avg": rev_a, "stars": stars,
                "url": make_affiliate_link(url, affiliate_id),
                "image": image, "shop": shop,
                "original_price": orig, "discount_pct": disc}
    except Exception:
        return None


def render_card(item: Dict) -> str:
    rank = item.get("rank", 99)

    # 閲覧者数
    base_w = max(3, 50 - rank * 3)
    w_id   = f"wc{abs(hash(item['name'])) % 9999}"
    watcher = f'<div class="watching"><span class="dot"></span>今 <span id="{w_id}">{base_w}</span>人がチェック中！</div>'

    # ランクバッジ
    rank_map = {1:("rank1","🥇 ランキング 1位"), 2:("rank2","🥈 ランキング 2位"), 3:("rank3","🥉 ランキング 3位")}
    rank_html = f'<div class="{rank_map[rank][0]}">{rank_map[rank][1]}</div>' if rank in rank_map else ""

    # 煽りバッジ
    hypes = ["🔥 本日限定！","⚡ 今だけ！","💥 激安特価！","✨ 人気急上昇！","🎯 注目商品！"]
    hype  = hypes[abs(hash(item["name"])) % len(hypes)]
    hype_class = ["h1","h2","h3","h1","h2"][abs(hash(item["name"])) % 5]

    # 画像
    if item["image"]:
        img_tag = f'<img class="card-img" src="{html.escape(item["image"])}" alt="{html.escape(item["name"])}" loading="lazy">'
    else:
        img_tag = '<div class="no-img">🛍️</div>'

    # 価格ゾーン
    if item.get("original_price") and item["original_price"] > item["price"]:
        disc_str = f'<span class="off-badge">{item["discount_pct"]:.0f}%OFF</span>' if item.get("discount_pct") else ""
        price_html = f'<div class="price-zone"><span class="orig-price">¥{item["original_price"]:,}</span>{disc_str}<div class="card-price">{item["price_fmt"]}</div></div>'
    else:
        est_orig = int(item["price"] * 1.25)
        price_html = f'<div class="price-zone"><span class="orig-price">¥{est_orig:,}</span><span class="off-badge">お得！</span><div class="card-price">{item["price_fmt"]}</div></div>'

    # 在庫アラート
    stock_num  = (abs(hash(item["name"])) % 15) + 3
    show_stock = (abs(hash(item["name"])) % 3 == 0)
    stock_html = f'<span class="badge badge-stock">⚠️ 残り{stock_num}点！</span>' if show_stock else ""

    return f"""      <article class="card" data-cat="{categorize(item['name'])}">
        {watcher}
        {rank_html}
        <div class="hype {hype_class}">{hype}</div>
        {img_tag}
        <div class="card-body">
          <p class="card-name">{html.escape(item["name"])}</p>
          <p class="card-shop">{html.escape(item["shop"])}</p>
          {price_html}
          <div class="star-row">
            <span class="big-stars">{item["stars"]}</span>
            <span class="rev-count">({item["review_count"]:,}件のレビュー)</span>
          </div>
          <div class="badges">
            {stock_html}
          </div>
          <a class="btn" href="{html.escape(item['url'])}" target="_blank" rel="noopener sponsored">
            🛒 今すぐ楽天で見る →
          </a>
        </div>
      </article>"""


def build_html(items: List[Dict], updated: str) -> str:
    cards = "\n".join(render_card(i) for i in items)
    total = len(items)
    avg_r = (sum(i["aff_rate"] for i in items) / total) if total else 0

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{html.escape(CONFIG['site_title'])}</title>
  <meta name="description" content="{html.escape(CONFIG['site_desc'])}">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--red:#e63946;--red2:#ff6b35;--bg:#f0f4f8;--white:#fff;--text:#1a202c;--muted:#718096;--radius:16px;--shadow:0 4px 16px rgba(0,0,0,.09);}}
    body{{font-family:'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}

    /* ── アニメーション ── */
    @keyframes rainbow{{0%{{background-position:0%}}100%{{background-position:200%}}}}
    @keyframes flash{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
    @keyframes ticker{{0%{{transform:translateX(100vw)}}100%{{transform:translateX(-100%)}}}}
    @keyframes shine{{0%{{left:-100%}}100%{{left:200%}}}}
    @keyframes wiggle{{0%,100%{{transform:rotate(0deg)}}25%{{transform:rotate(-1.5deg)}}75%{{transform:rotate(1.5deg)}}}}
    @keyframes pulse-card{{0%,100%{{box-shadow:0 6px 24px rgba(0,0,0,.1)}}50%{{box-shadow:0 0 0 4px rgba(255,214,0,.5),0 6px 24px rgba(0,0,0,.1)}}}}

    /* ── ヘッダー ── */
    header{{background:linear-gradient(135deg,#0d0221,#4a0080,#e63946,#ff6b35,#FFD600);background-size:300%;animation:rainbow 6s linear infinite;color:#fff;padding:2.5rem 1rem 2rem;text-align:center;position:relative;overflow:hidden;}}
    header::after{{content:"";position:absolute;top:0;left:-100%;width:60%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);animation:shine 4s ease-in-out infinite;}}
    .site-title{{font-size:clamp(1.8rem,5vw,3rem);font-weight:900;letter-spacing:-.03em;text-shadow:0 0 30px rgba(255,214,0,.6);position:relative;}}
    .site-title .y{{color:#FFD600;animation:flash 1.5s infinite;}}
    .site-desc{{opacity:.9;margin-top:.5rem;font-size:1rem;font-weight:700;position:relative;}}
    .stats-bar{{display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap;margin-top:1.2rem;position:relative;}}
    .stat{{background:rgba(255,255,255,.2);border:2px solid rgba(255,214,0,.5);border-radius:999px;padding:.4rem 1rem;font-size:.82rem;font-weight:800;}}

    /* ── ティッカー ── */
    .ticker-wrap{{background:#1a0533;overflow:hidden;padding:.45rem 0;}}
    .ticker{{display:inline-block;white-space:nowrap;color:#FFD600;font-size:.85rem;font-weight:800;animation:ticker 25s linear infinite;letter-spacing:.05em;padding-left:100%;}}

    /* ── バナー ── */
    .banner-area{{max-width:900px;margin:1.5rem auto 0;padding:0 1rem;}}

    /* ── レイアウト ── */
    main{{max-width:960px;margin:1.5rem auto;padding:0 1rem;}}
    .layout{{display:flex;gap:1.2rem;align-items:flex-start;}}
    .sidebar{{width:175px;flex-shrink:0;display:flex;flex-direction:column;gap:.9rem;}}
    .sbox{{background:var(--white);border-radius:14px;padding:.9rem;box-shadow:var(--shadow);border-left:4px solid var(--red);}}
    .sbox h3{{font-size:.84rem;font-weight:900;color:var(--red);border-bottom:2px solid var(--red);padding-bottom:.3rem;margin-bottom:.65rem;}}
    .sbox ul{{list-style:none;display:flex;flex-direction:column;gap:.3rem;}}
    .sbox li{{font-size:.78rem;padding:.28rem .4rem;color:#1a0533;font-weight:600;}}
    .sbox li::before{{content:"▶ ";color:var(--red);font-size:.65rem;}}
    .sbox p{{font-size:.76rem;color:var(--muted);line-height:1.65;}}
    .sns-btn{{display:block;text-align:center;background:#000;color:#FFD600;padding:.5rem;border-radius:8px;font-size:.8rem;font-weight:900;text-decoration:none;margin-bottom:.45rem;}}
    .sale-b{{background:linear-gradient(135deg,var(--red),var(--red2));color:#fff;border-radius:10px;padding:.65rem;text-align:center;margin-bottom:.5rem;}}
    .sale-b .t{{font-size:.7rem;font-weight:700;opacity:.9;}}
    .sale-b .d{{font-size:.95rem;font-weight:900;}}
    .main-col{{flex:1;min-width:0;}}
    .section-title{{font-size:1.15rem;font-weight:900;margin-bottom:.9rem;background:linear-gradient(90deg,var(--red),var(--red2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}

    /* ── グリッド ── */
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;}}

    /* ── カード ── */
    .card{{background:var(--white);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s;border:2px solid transparent;}}
    .card:nth-child(1){{border-color:#FFD600;animation:pulse-card 2s infinite;}}
    .card:nth-child(2){{border-color:#aaa;}}
    .card:nth-child(3){{border-color:#cd7f32;}}
    .card:hover{{transform:translateY(-7px) scale(1.02);box-shadow:0 20px 50px rgba(230,57,70,.25);}}

    .watching{{background:#fff3e0;color:#c45000;font-size:.7rem;font-weight:800;padding:.22rem .6rem;text-align:center;display:flex;align-items:center;justify-content:center;gap:.35rem;}}
    .dot{{width:7px;height:7px;background:var(--red);border-radius:50%;display:inline-block;animation:flash .8s infinite;flex-shrink:0;}}
    .rank1{{background:linear-gradient(90deg,#1a0533,#4a0080);color:#FFD600;font-size:.75rem;font-weight:900;padding:.28rem .6rem;text-align:center;letter-spacing:.05em;}}
    .rank2{{background:linear-gradient(90deg,#2a2a2a,#555);color:#e8e8e8;font-size:.75rem;font-weight:900;padding:.28rem .6rem;text-align:center;}}
    .rank3{{background:linear-gradient(90deg,#3d1a00,#7a3a00);color:#ffb347;font-size:.75rem;font-weight:900;padding:.28rem .6rem;text-align:center;}}
    .hype{{font-size:.72rem;font-weight:900;padding:.26rem .6rem;text-align:center;letter-spacing:.08em;color:#fff;}}
    .h1{{background:linear-gradient(90deg,var(--red),var(--red2));}}
    .h2{{background:linear-gradient(90deg,#7209b7,var(--red));}}
    .h3{{background:linear-gradient(90deg,#0077b6,#00b4d8);}}

    .card-img{{width:100%;aspect-ratio:1;object-fit:contain;background:linear-gradient(135deg,#f7f8fa,#edf2f7);padding:.7rem;}}
    .no-img{{width:100%;aspect-ratio:1;background:linear-gradient(135deg,#edf2f7,#e2e8f0);display:flex;align-items:center;justify-content:center;font-size:3rem;}}
    .card-body{{padding:.9rem;flex:1;display:flex;flex-direction:column;gap:.4rem;}}
    .card-name{{font-size:.87rem;font-weight:800;line-height:1.45;color:#0d0221;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}}
    .card-shop{{font-size:.7rem;color:var(--muted);font-weight:600;}}
    .price-zone{{margin:.25rem 0;}}
    .orig-price{{font-size:.8rem;color:#aaa;text-decoration:line-through;font-weight:600;}}
    .off-badge{{display:inline-block;background:var(--red);color:#fff;font-size:.68rem;font-weight:900;padding:.06rem .38rem;border-radius:4px;margin-left:.3rem;}}
    .card-price{{font-size:1.55rem;font-weight:900;color:var(--red);letter-spacing:-.03em;}}
    .star-row{{display:flex;align-items:center;gap:.4rem;}}
    .big-stars{{font-size:.95rem;color:#f5a623;}}
    .rev-count{{font-size:.7rem;color:var(--muted);font-weight:600;}}
    .badges{{display:flex;gap:.3rem;flex-wrap:wrap;margin-top:.15rem;}}
    .badge{{font-size:.68rem;font-weight:700;padding:.15rem .5rem;border-radius:999px;}}
    .badge-rate{{background:#dcfce7;color:#166534;}}
    .badge-stock{{background:#fff0f3;color:#c0182a;animation:flash 1s infinite;}}

    .btn{{display:block;text-align:center;text-decoration:none;background:linear-gradient(135deg,var(--red),var(--red2));color:#fff;padding:.88rem;border-radius:12px;font-weight:900;font-size:.95rem;margin-top:.55rem;box-shadow:0 5px 18px rgba(230,57,70,.45);letter-spacing:.03em;position:relative;overflow:hidden;animation:wiggle 3s ease-in-out infinite;}}
    .btn::after{{content:"";position:absolute;top:0;left:-100%;width:60%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);animation:shine 2s ease-in-out infinite;}}

    .cat-item{{cursor:pointer;padding:.35rem .5rem;border-radius:8px;transition:background .15s;list-style:none;}}
    .cat-item:hover{{background:#fff0f0;color:var(--red);}}
    .cat-item.active{{background:var(--red)!important;color:#fff!important;font-weight:900;}}
    .cat-item::before{{content:none!important;}}
    footer{{text-align:center;padding:2.5rem 1rem;font-size:.75rem;color:var(--muted);border-top:1px solid #e2e8f0;margin-top:3rem;line-height:1.9;}}

    @media(max-width:640px){{
      .layout{{flex-direction:column;}}
      .sidebar{{width:100%;}}
      .grid{{grid-template-columns:repeat(2,1fr);gap:.75rem;}}
    }}
  </style>
</head>
<body>
  <header>
    <h1 class="site-title">🛒 節約生活 <span class="y">今日の</span>お買い得！</h1>
    <p class="site-desc">⚡ 毎朝9時自動更新 ✨ 楽天市場 高評価セール品 厳選まとめ ⚡</p>
    <div class="stats-bar">
      <span class="stat">📦 {total}件掲載中</span>
      <span class="stat">👥 今 <span id="hw">247</span>人が閲覧中！</span>
      <span class="stat">🕐 {updated} 更新</span>
      <span class="stat" id="countdown">⏰ 計算中...</span>
    </div>
  </header>

  <div class="ticker-wrap">
    <div class="ticker">🔥 セール情報を自動更新中！&nbsp;&nbsp;⚡ ポイント最大10倍の商品あり！&nbsp;&nbsp;💰 今だけ特別価格！&nbsp;&nbsp;🏆 高評価商品のみ厳選！&nbsp;&nbsp;⚠️ 在庫なくなり次第終了！&nbsp;&nbsp;🛒 毎朝9時に新鮮情報をお届け！&nbsp;&nbsp;</div>
  </div>

  <div class="banner-area">
    <a href="https://hb.afl.rakuten.co.jp/ichiba/54d0824b.d9b23123.54d0824c.c43ff40d/?pc=https%3A%2F%2Fevent.rakuten.co.jp%2Fcampaign%2Fpoint-up%2Fmarathon%2F" target="_blank" rel="noopener sponsored" style="display:block;text-decoration:none;">
      <svg width="100%" viewBox="0 0 680 120" role="img">
        <rect x="0" y="0" width="680" height="120" rx="14" fill="#FF3B5C"/>
        <circle cx="50" cy="30" r="22" fill="#FFD600"/>
        <circle cx="630" cy="90" r="28" fill="#00D68F" opacity="0.7"/>
        <circle cx="600" cy="20" r="14" fill="#FFD600" opacity="0.8"/>
        <circle cx="70" cy="100" r="18" fill="#FF8C42" opacity="0.7"/>
        <rect x="20" y="40" width="160" height="32" rx="16" fill="#FFD600"/>
        <text x="100" y="61" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="700" fill="#FF3B5C">🛒 毎日自動更新！</text>
        <text x="340" y="55" text-anchor="middle" font-family="sans-serif" font-size="28" font-weight="900" fill="#fff">節約生活</text>
        <text x="340" y="88" text-anchor="middle" font-family="sans-serif" font-size="17" font-weight="700" fill="#FFD600">今日のお買い得情報</text>
        <rect x="460" y="38" width="180" height="34" rx="17" fill="#fff"/>
        <text x="550" y="60" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="#FF3B5C">楽天セール 厳選まとめ</text>
        <rect x="255" y="92" width="170" height="20" rx="10" fill="#FFD600"/>
        <text x="340" y="106" text-anchor="middle" font-family="sans-serif" font-size="11" font-weight="800" fill="#FF3B5C">今すぐチェック →</text>
      </svg>
    </a>
  </div>

  <main>
    <div class="layout">
      <aside class="sidebar">
        <div class="sbox">
          <h3>📂 カテゴリ</h3>
          <ul id="cat-list">
            <li class="cat-item active" onclick="filterCat('all')" data-cat="all">📋 すべて表示</li>
            <li class="cat-item" onclick="filterCat('food')" data-cat="food">🍱 食品・グルメ</li>
            <li class="cat-item" onclick="filterCat('beauty')" data-cat="beauty">💄 美容・健康</li>
            <li class="cat-item" onclick="filterCat('fashion')" data-cat="fashion">👕 ファッション</li>
            <li class="cat-item" onclick="filterCat('daily')" data-cat="daily">🧴 日用品・雑貨</li>
          </ul>
        </div>
        <div class="sbox">
          <h3>💡 節約のコツ</h3>
          <p>マラソン期間中は複数店舗でポイント最大10倍！まとめ買いが超お得！</p>
        </div>
      </aside>

      <div class="main-col">
        <p class="section-title">🏆 今日のお得ランキング</p>
        <div class="grid">
{cards}
        </div>
      </div>

      <aside class="sidebar">
        <div class="sbox">
          <h3>🎉 楽天セール情報</h3>
          <div class="sale-b"><div class="t">お買い物マラソン</div><div class="d">6/20(土)20時〜開催！</div></div>
        </div>
        <div class="sbox">
          <h3>📢 SNSフォロー</h3>
          <a class="sns-btn" href="https://www.pinterest.jp/topsecret0116/" target="_blank" style="background:#E60023;">📌 Pinterestでフォロー</a>
          <p>お得情報をピンで毎日更新中！フォローして見逃さないように♪</p>
        </div>
        <div class="sbox">
          <h3>ℹ️ このサイトについて</h3>
          <p>楽天市場の高評価セール品を毎日自動で収集。節約生活を全力応援！</p>
        </div>
      </aside>
    </div>
  </main>

  <footer>
    <p>当サイトは楽天アフィリエイトプログラムに参加しています。</p>
    <p>© {datetime.now().year} 節約生活 今日のお買い得情報</p>
  </footer>

  <script>
    function tick() {{
      var now = new Date(), next = new Date();
      next.setHours(9, 0, 0, 0);
      if (now >= next) next.setDate(next.getDate() + 1);
      var d = next - now;
      var h = Math.floor(d / 3600000);
      var m = Math.floor(d % 3600000 / 60000);
      var s = Math.floor(d % 60000 / 1000);
      var el = document.getElementById("countdown");
      if (el) el.textContent = "⏰ 次の更新まで " + h + "h " + m + "m " + s + "s";
    }}
    setInterval(tick, 1000); tick();

    function filterCat(cat) {{
      document.querySelectorAll('.card').forEach(function(c) {{
        c.style.display = (cat==='all' || c.dataset.cat===cat) ? '' : 'none';
      }});
      document.querySelectorAll('.cat-item').forEach(function(li) {{
        li.classList.toggle('active', li.dataset.cat===cat);
      }});
    }}

    setInterval(function() {{
      document.querySelectorAll("[id^='wc']").forEach(function(el) {{
        var v = parseInt(el.textContent) || 10;
        el.textContent = Math.max(1, v + Math.floor(Math.random() * 3) - 1);
      }});
      var hw = document.getElementById("hw");
      if (hw) hw.textContent = Math.max(100, parseInt(hw.textContent) + Math.floor(Math.random() * 5) - 2);
    }}, 3500);
  </script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║  🛒 節約生活 サイト生成システム      ║")
    print("╚══════════════════════════════════════╝\n")

    if args.demo:
        print("  [デモモード] ダミーデータを使用\n")
        items = DEMO_ITEMS
    else:
        app_id     = CONFIG["app_id"]
        access_key = CONFIG["access_key"]
        aff_id     = CONFIG["affiliate_id"]
        if not app_id:
            print("❌  RAKUTEN_APP_ID が設定されていません")
            print("   set RAKUTEN_APP_ID=あなたのID\n")
            sys.exit(1)
        if not aff_id:
            print("⚠️  RAKUTEN_AFFILIATE_ID が未設定（アフィリリンクなし）\n")
        items = fetch_items(app_id, access_key, aff_id)

    if not items:
        print("⚠️  商品を取得できませんでした")
        sys.exit(1)

    print(f"\n  ✅ {len(items)} 件の商品を取得")

    updated  = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    out_dir  = Path(CONFIG["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    html_content = build_html(items, updated)
    html_path = out_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")

    json_path = out_dir / "deals.json"
    json_path.write_text(json.dumps({"generated_at": datetime.now().isoformat(), "count": len(items), "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  🌐 サイト生成完了: {html_path}\n")

    if args.open:
        import webbrowser
        webbrowser.open(html_path.resolve().as_uri())


if __name__ == "__main__":
    main()
