#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════╗
║   🛒  全自動アフィリエイト・セールサイト生成システム  v2.0     ║
╠════════════════════════════════════════════════════════════════╣
║  楽天市場の高報酬セール品を自動収集 → サイト自動生成           ║
║  → GitHub Pages で公開 → 購入されるたびに報酬が入る            ║
╠════════════════════════════════════════════════════════════════╣
║  【お金の流れ】                                                 ║
║  訪問者がサイトを見る                                           ║
║    → 商品リンクをクリック（楽天市場へ）                         ║
║    → 楽天で購入                                                 ║
║    → あなたに報酬（商品代金の1〜15%）が入る ✅                  ║
║  ※ 在庫不要・仕入れ不要・自動で毎日更新                        ║
╠════════════════════════════════════════════════════════════════╣
║  【報酬率の目安（楽天アフィリエイト）】                         ║
║  食品・日用品    : 1〜5%                                        ║
║  ファッション    : 5〜10%                                       ║
║  美容・健康      : 5〜15%                                       ║
║  ※ もしもアフィリエイト経由だと +12%ボーナスあり               ║
╠════════════════════════════════════════════════════════════════╣
║  【必要なもの（すべて無料）】                                   ║
║  1. 楽天Webサービス APP_ID                                      ║
║       https://webservice.rakuten.co.jp/                         ║
║  2. 楽天アフィリエイト AFFILIATE_ID                             ║
║       https://affiliate.rakuten.co.jp/                          ║
║  3. GitHubアカウント → GitHub Pages でサイト公開               ║
╠════════════════════════════════════════════════════════════════╣
║  【セットアップ】                                               ║
║  pip install requests                                           ║
║  export RAKUTEN_APP_ID="あなたのアプリID"                       ║
║  export RAKUTEN_AFFILIATE_ID="あなたのアフィリエイトID"         ║
╠════════════════════════════════════════════════════════════════╣
║  【実行方法】                                                   ║
║  python generate_site.py          # サイト生成                  ║
║  python generate_site.py --open   # 生成後ブラウザで確認        ║
║  python generate_site.py --demo   # APIキーなしで動作確認       ║
╚════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, html, argparse, urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌  pip install requests が必要です")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
# ⚙️ 設定  ← ここをカスタマイズ
# ══════════════════════════════════════════════════════════════
CONFIG = {
    # ── API 認証（環境変数から読み込み）──────────────────────
    "app_id":       os.environ.get("RAKUTEN_APP_ID", ""),
    "access_key":   os.environ.get("RAKUTEN_ACCESS_KEY", ""),
    "affiliate_id": os.environ.get("RAKUTEN_AFFILIATE_ID", ""),

    # ── サイト情報 ───────────────────────────────────────────
    "site_title":    "🛒 今日のお得セール品まとめ【楽天市場】",
    "site_desc":     "楽天市場の高評価・高割引セール品を毎日自動更新！食品・日用品・美容・ファッションまで",
    "site_keywords": "楽天セール,特価,お買い得,割引,日用品,食品",

    # ── 収集設定 ─────────────────────────────────────────────
    # キーワード別に検索。多いほど商品数が増える
    "search_keywords": [
        "セール 食品",
        "特価 日用品 まとめ買い",
        "訳あり 食品 送料無料",
        "在庫処分 お買い得",
        "ポイント10倍",
        "セール 美容",
        "タイムセール 生活雑貨",
        "お試し 送料無料",
    ],

    # 1キーワードあたりの最大取得件数（最大30）
    "max_per_keyword": 20,

    # フィルター条件
    "min_affiliate_rate":  1.0,   # アフィリエイト率の下限 (%)
    "min_review_count":    5,     # 最低レビュー数
    "min_review_avg":      3.8,   # 最低レビュー平均点
    "max_price":           30000, # 表示する最高価格（円）
    "min_price":           100,   # 表示する最低価格（円）

    # ── 出力 ─────────────────────────────────────────────────
    "output_dir":    "docs",  # GitHub Pages は /docs をそのまま公開できる
    "output_html":   "index.html",
    "output_json":   "deals.json",  # データも保存（ログ用）
}


# ══════════════════════════════════════════════════════════════
# 📡 楽天 API クライアント
# ══════════════════════════════════════════════════════════════
class RakutenAPI:
    SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"

    def __init__(self, app_id: str, access_key: str = ""):
        self.app_id     = app_id
        self.access_key = access_key
        self.session    = requests.Session()
        self.session.headers.update({"Accept-Language": "ja"})

    def search(self, keyword: str, hits: int = 20) -> List[Dict]:
        """楽天市場で商品検索（最小限のパラメータ）"""
        params = {
            "applicationId": self.app_id,
            "accessKey":     self.access_key,
            "keyword":       keyword,
            "hits":          min(hits, 30),
            "genreId":       0,
            "format":        "json",
        }
        try:
            r = self.session.get(self.SEARCH_URL, params=params, timeout=15)
            if r.status_code != 200:
                print(f"  ⚠️  APIエラー {r.status_code}: {r.text[:300]}")
                return []
            data = r.json()
            raw_items = data.get("Items", [])
            if not raw_items:
                print(f"  DEBUG: レスポンスキー = {list(data.keys())}")
                return []
            # 最初のアイテムのキーを確認してネスト構造に対応
            first = raw_items[0]
            first_keys = list(first.keys())
            result = []
            for i in raw_items:
                # "item" または "アイテム" キーでネストされている場合
                inner = i.get("item") or i.get("アイテム") or i
                result.append(inner)
            return result
        except Exception as e:
            print(f"  ⚠️  通信エラー ({keyword}): {e}")
            return []


# ══════════════════════════════════════════════════════════════
# 🔗 アフィリエイトリンク生成
# ══════════════════════════════════════════════════════════════
class AffiliateLink:
    def __init__(self, affiliate_id: str):
        self.affiliate_id = affiliate_id

    def make(self, product_url: str) -> str:
        """楽天アフィリエイトリンクを生成"""
        if not self.affiliate_id:
            return product_url  # IDなしの場合はそのままのURLを使用
        encoded = urllib.parse.quote(product_url, safe="")
        # 楽天アフィリエイト公式のURL形式
        return (
            f"https://hb.afl.rakuten.co.jp/ichiba/{self.affiliate_id}/"
            f"?pc={encoded}&link_type=picttext"
        )


# ══════════════════════════════════════════════════════════════
# 🧹 データ整形
# ══════════════════════════════════════════════════════════════
def normalize(raw: Dict, affiliate: AffiliateLink) -> Optional[Dict]:
    """楽天APIのレスポンスを使いやすい形に整形してフィルタリング"""
    try:
        name      = raw.get("itemName", "").strip()
        price     = int(raw.get("itemPrice", 0))
        aff_rate  = float(raw.get("affiliateRate", 0))
        review_c  = int(raw.get("reviewCount", 0))
        review_a  = float(raw.get("reviewAverage", 0))
        url       = raw.get("itemUrl", "")
        shop      = raw.get("shopName", "").strip()
        caption   = raw.get("itemCaption", "")[:120]

        # 画像URL取得
        images = raw.get("mediumImageUrls", [])
        image  = ""
        if images:
            img = images[0]
            image = img if isinstance(img, str) else img.get("imageUrl", "")

        # ── フィルタリング ──────────────────────────────────
        if not name or not url or price <= 0:
            return None
        if price < CONFIG["min_price"] or price > CONFIG["max_price"]:
            return None
        if aff_rate < CONFIG["min_affiliate_rate"]:
            return None
        if review_c < CONFIG["min_review_count"]:
            return None
        if review_a < CONFIG["min_review_avg"]:
            return None

        # 報酬額の試算（表示用）
        estimated_fee = int(price * aff_rate / 100)

        return {
            "name":          name[:70],
            "price":         price,
            "price_fmt":     f"¥{price:,}",
            "aff_rate":      aff_rate,
            "est_fee":       estimated_fee,
            "est_fee_fmt":   f"¥{estimated_fee:,}",
            "review_count":  review_c,
            "review_avg":    review_a,
            "stars":         "★" * round(review_a) + "☆" * (5 - round(review_a)),
            "url":           affiliate.make(url),
            "image":         image,
            "shop":          shop,
            "caption":       caption,
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# 🎨 HTML テンプレート
# ══════════════════════════════════════════════════════════════
def build_html(items: List[Dict], updated: str) -> str:
    cards_html = "\n".join(_card(i) for i in items)
    total      = len(items)
    avg_rate   = (sum(i["aff_rate"] for i in items) / total) if total else 0

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{html.escape(CONFIG['site_title'])}</title>
  <meta name="description" content="{html.escape(CONFIG['site_desc'])}">
  <meta name="keywords"    content="{html.escape(CONFIG['site_keywords'])}">
  <meta property="og:title"       content="{html.escape(CONFIG['site_title'])}">
  <meta property="og:description" content="{html.escape(CONFIG['site_desc'])}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --red:#e63946; --red-dark:#c1121f;
      --bg:#f0f4f8; --white:#fff;
      --text:#1a202c; --muted:#718096;
      --radius:12px; --shadow:0 2px 10px rgba(0,0,0,.08);
    }}
    body{{font-family:'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;
          background:var(--bg);color:var(--text);min-height:100vh}}

    /* ヘッダー */
    header{{
      background:linear-gradient(135deg,var(--red) 0%,var(--red-dark) 100%);
      color:#fff;padding:2.5rem 1rem;text-align:center
    }}
    .site-title{{font-size:clamp(1.3rem,4.5vw,2rem);font-weight:900;letter-spacing:-.02em}}
    .site-desc {{opacity:.85;margin-top:.4rem;font-size:.9rem}}
    .stats-bar {{
      display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;
      margin-top:1.2rem
    }}
    .stat{{
      background:rgba(255,255,255,.2);padding:.35rem .9rem;
      border-radius:999px;font-size:.8rem;font-weight:600
    }}

    /* グリッド */
    main{{max-width:1180px;margin:2rem auto;padding:0 1rem}}
    .section-title{{
      font-size:1.1rem;font-weight:800;margin-bottom:1rem;
      display:flex;align-items:center;gap:.5rem
    }}
    .grid{{
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
      gap:1.25rem
    }}

    /* カード */
    .card{{
      background:var(--white);border-radius:var(--radius);
      overflow:hidden;box-shadow:var(--shadow);
      display:flex;flex-direction:column;
      transition:transform .18s,box-shadow .18s
    }}
    .card:hover{{transform:translateY(-5px);box-shadow:0 12px 28px rgba(0,0,0,.14)}}
    .card-img{{
      width:100%;aspect-ratio:1;object-fit:contain;
      background:#f7f8fa;padding:.6rem
    }}
    .no-img{{
      width:100%;aspect-ratio:1;background:linear-gradient(135deg,#edf2f7,#e2e8f0);
      display:flex;align-items:center;justify-content:center;font-size:3rem
    }}
    .card-body{{padding:.9rem;flex:1;display:flex;flex-direction:column;gap:.45rem}}
    .card-name{{font-size:.83rem;font-weight:600;line-height:1.45;
                display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
    .card-shop{{font-size:.72rem;color:var(--muted)}}
    .card-price{{font-size:1.35rem;font-weight:900;color:var(--red);margin-top:auto}}
    .badges{{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.2rem}}
    .badge{{font-size:.68rem;font-weight:700;padding:.18rem .55rem;border-radius:999px}}
    .badge-fee {{background:#fef9c3;color:#854d0e}}
    .badge-star{{background:#fef9c3;color:#854d0e}}
    .badge-rate{{background:#dcfce7;color:#166534}}
    .btn{{
      display:block;text-align:center;text-decoration:none;
      background:var(--red);color:#fff;
      padding:.65rem;border-radius:8px;font-weight:700;font-size:.85rem;
      margin-top:.65rem;transition:background .15s
    }}
    .btn:hover{{background:var(--red-dark)}}

    /* フッター */
    footer{{
      text-align:center;padding:2.5rem 1rem;
      font-size:.75rem;color:var(--muted);
      border-top:1px solid #e2e8f0;margin-top:3rem;line-height:1.9
    }}

    @media(max-width:480px){{
      .grid{{grid-template-columns:repeat(2,1fr);gap:.75rem}}
      .card-name{{font-size:.78rem}}
    }}
  </style>
</head>
<body>
  <header>
    <h1 class="site-title">{html.escape(CONFIG['site_title'])}</h1>
    <p class="site-desc">{html.escape(CONFIG['site_desc'])}</p>
    <div class="stats-bar">
      <span class="stat">📦 {total}件</span>
      <span class="stat">💰 平均報酬率 {avg_rate:.1f}%</span>
      <span class="stat">🕐 {updated} 更新</span>
    </div>
  </header>

  <main>
    <p class="section-title">🔥 今日のお得ピックアップ</p>
    <div class="grid">
{cards_html}
    </div>
  </main>

  <footer>
    <p>当サイトは楽天アフィリエイトプログラムに参加しており、リンクを経由した購入で報酬を得ることがあります。</p>
    <p>商品の価格・在庫・送料は変動する場合があります。購入前に楽天市場でご確認ください。</p>
    <p>© {datetime.now().year} Deal Hunter — 毎日自動更新</p>
  </footer>
</body>
</html>"""


def _card(item: Dict) -> str:
    img_tag = (
        f'<img class="card-img" src="{html.escape(item["image"])}" '
        f'alt="{html.escape(item["name"])}" loading="lazy">'
        if item["image"] else
        '<div class="no-img">🛍️</div>'
    )
    return f"""      <article class="card">
        {img_tag}
        <div class="card-body">
          <p class="card-name">{html.escape(item["name"])}</p>
          <p class="card-shop">{html.escape(item["shop"])}</p>
          <p class="card-price">{item["price_fmt"]}</p>
          <div class="badges">
            <span class="badge badge-rate">報酬率 {item["aff_rate"]}%</span>
            <span class="badge badge-fee">1件 {item["est_fee_fmt"]} 入る</span>
            <span class="badge badge-star">{item["stars"]} ({item["review_count"]}件)</span>
          </div>
          <a class="btn" href="{html.escape(item['url'])}" target="_blank" rel="noopener sponsored">
            楽天市場で見る →
          </a>
        </div>
      </article>"""


# ══════════════════════════════════════════════════════════════
# 🎭 デモ用ダミーデータ（--demo フラグ時に使用）
# ══════════════════════════════════════════════════════════════
DEMO_ITEMS = [
    {"name":"【訳あり】九州産 黒豚しゃぶしゃぶセット 500g","price":1980,"price_fmt":"¥1,980",
     "aff_rate":4.5,"est_fee":89,"est_fee_fmt":"¥89","review_count":342,"review_avg":4.3,
     "stars":"★★★★☆","url":"#","image":"","shop":"九州うまか亭","caption":""},
    {"name":"シャンプー 詰替 超特大 900ml 2個セット","price":1280,"price_fmt":"¥1,280",
     "aff_rate":5.0,"est_fee":64,"est_fee_fmt":"¥64","review_count":1203,"review_avg":4.6,
     "stars":"★★★★★","url":"#","image":"","shop":"コスメコム楽天市場店","caption":""},
    {"name":"国産 ひのき まな板 36×24cm","price":2480,"price_fmt":"¥2,480",
     "aff_rate":6.2,"est_fee":153,"est_fee_fmt":"¥153","review_count":89,"review_avg":4.4,
     "stars":"★★★★☆","url":"#","image":"","shop":"木のぬくもり屋","caption":""},
    {"name":"【送料無料】カゴメ 野菜生活100 200ml×24本","price":1980,"price_fmt":"¥1,980",
     "aff_rate":3.0,"est_fee":59,"est_fee_fmt":"¥59","review_count":4521,"review_avg":4.5,
     "stars":"★★★★★","url":"#","image":"","shop":"カゴメ公式楽天市場店","caption":""},
    {"name":"【まとめ買い】ティッシュペーパー 5箱×6セット","price":2680,"price_fmt":"¥2,680",
     "aff_rate":2.5,"est_fee":67,"est_fee_fmt":"¥67","review_count":782,"review_avg":4.2,
     "stars":"★★★★☆","url":"#","image":"","shop":"日用品ストア","caption":""},
    {"name":"有機 ドリップコーヒー 30袋入り コロンビア","price":1580,"price_fmt":"¥1,580",
     "aff_rate":7.0,"est_fee":110,"est_fee_fmt":"¥110","review_count":234,"review_avg":4.7,
     "stars":"★★★★★","url":"#","image":"","shop":"スペシャルティコーヒー専門店","caption":""},
    {"name":"日清 カップヌードル シーフード 20個入り","price":2180,"price_fmt":"¥2,180",
     "aff_rate":2.0,"est_fee":43,"est_fee_fmt":"¥43","review_count":1892,"review_avg":4.5,
     "stars":"★★★★★","url":"#","image":"","shop":"ニッシンフーズ直営店","caption":""},
    {"name":"UVカット 日焼け止めスプレー SPF50+ 250ml","price":1980,"price_fmt":"¥1,980",
     "aff_rate":8.0,"est_fee":158,"est_fee_fmt":"¥158","review_count":567,"review_avg":4.4,
     "stars":"★★★★☆","url":"#","image":"","shop":"美容ドラッグストア","caption":""},
]


# ══════════════════════════════════════════════════════════════
# 🚀 メイン処理
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="アフィリエイト型セールサイト自動生成")
    parser.add_argument("--open", action="store_true", help="生成後ブラウザで開く")
    parser.add_argument("--demo", action="store_true", help="デモモード（APIキー不要）")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║  🛒 アフィリエイトサイト生成システム  ║")
    print("╚══════════════════════════════════════╝\n")

    app_id    = CONFIG["app_id"]
    aff_id    = CONFIG["affiliate_id"]
    affiliate = AffiliateLink(aff_id)

    # ── 商品収集 ────────────────────────────────────────────
    if args.demo:
        print("  [デモモード] ダミーデータを使用します\n")
        items = DEMO_ITEMS
    else:
        if not app_id:
            print("❌  RAKUTEN_APP_ID が設定されていません")
            print("   👉 https://webservice.rakuten.co.jp/ で無料取得")
            print("   👉 export RAKUTEN_APP_ID='取得したID'\n")
            print("   ※ まず動作確認したい場合: python generate_site.py --demo\n")
            sys.exit(1)

        if not aff_id:
            print("⚠️  RAKUTEN_AFFILIATE_ID が未設定")
            print("   アフィリリンクなしで実行します")
            print("   👉 https://affiliate.rakuten.co.jp/ で無料取得推奨\n")

        api       = RakutenAPI(app_id, CONFIG["access_key"])
        raw_items = []
        seen_urls = set()

        for keyword in CONFIG["search_keywords"]:
            print(f"  🔍 収集中: {keyword}")
            raws = api.search(keyword, hits=CONFIG["max_per_keyword"])
            added = 0
            for r in raws:
                norm = normalize(r, affiliate)
                if norm and norm["url"] not in seen_urls:
                    seen_urls.add(norm["url"])
                    raw_items.append(norm)
                    added += 1
            print(f"       → {added} 件追加")
            time.sleep(1.0)  # API制限対策（1秒ウェイト）

        # 報酬率 × レビュー数 でスコアリングしてソート
        items = sorted(
            raw_items,
            key=lambda x: x["aff_rate"] * (x["review_avg"] / 5),
            reverse=True
        )

    if not items:
        print("⚠️  商品を取得できませんでした")
        sys.exit(1)

    print(f"\n  ✅ {len(items)} 件の商品を取得")
    print(f"  💰 平均報酬率: {sum(i['aff_rate'] for i in items)/len(items):.1f}%")

    # ── HTML生成 ────────────────────────────────────────────
    updated  = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    out_dir  = Path(CONFIG["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    html_out = out_dir / CONFIG["output_html"]
    json_out = out_dir / CONFIG["output_json"]

    html_out.write_text(build_html(items, updated), encoding="utf-8")
    json_out.write_text(
        json.dumps({"generated_at": datetime.now().isoformat(),
                    "count": len(items), "items": items},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n  🌐 サイト生成完了!")
    print(f"     HTML : {html_out}")
    print(f"     JSON : {json_out}")

    # ── デプロイ手順 ────────────────────────────────────────
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦  GitHub Pages で無料公開する手順
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① GitHubで新しいリポジトリを作成

② このフォルダをプッシュ:
   git init
   git add .
   git commit -m "初回デプロイ"
   git remote add origin https://github.com/ユーザー名/リポジトリ名.git
   git push -u origin main

③ GitHubのリポジトリ画面で:
   Settings → Pages → Source: main / docs → Save

④ 数分後に https://ユーザー名.github.io/リポジトリ名/ で公開！

🤖  自動更新は .github/workflows/auto_update.yml が毎日実行します
    GitHub Secrets に RAKUTEN_APP_ID と RAKUTEN_AFFILIATE_ID を設定してください
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

    if args.open:
        import webbrowser
        webbrowser.open(html_out.resolve().as_uri())


if __name__ == "__main__":
    main()
