#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""カテゴリフィルター機能追加パッチ
使い方: py patch_categories.py
"""
import re

print("📂 generate_site_final.py を読み込み中...")
with open('generate_site_final.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ===== 1. categorize関数を追加 =====
if 'def categorize(' not in src:
    cat_func = """
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

"""
    src = src.replace('\ndef normalize(raw: Dict', cat_func + '\ndef normalize(raw: Dict', 1)
    print("✅ categorize関数を追加")
else:
    print("⏭️  categorize関数は既に存在")

# ===== 2. render_cardにdata-cat追加 =====
old_article = '      <article class="card">'
new_article = '      <article class="card" data-cat="{categorize(item[\'name\'])}">'
if 'data-cat=' not in src:
    src = src.replace(old_article, new_article, 1)
    print("✅ articleタグにdata-cat追加")
else:
    print("⏭️  data-catは既に存在")

# ===== 3. サイドバーのカテゴリULを置換 =====
new_ul = """<ul id="cat-list">
            <li class="cat-item active" onclick="filterCat('all')" data-cat="all">📋 すべて表示</li>
            <li class="cat-item" onclick="filterCat('food')" data-cat="food">🍱 食品・グルメ</li>
            <li class="cat-item" onclick="filterCat('beauty')" data-cat="beauty">💄 美容・健康</li>
            <li class="cat-item" onclick="filterCat('fashion')" data-cat="fashion">👕 ファッション</li>
            <li class="cat-item" onclick="filterCat('daily')" data-cat="daily">🧴 日用品・雑貨</li>
          </ul>"""

if 'id="cat-list"' not in src:
    src = re.sub(r'<ul>\s*<li>.*?</ul>', new_ul, src, count=1, flags=re.DOTALL)
    print("✅ カテゴリULをクリッカブルに変更")
else:
    print("⏭️  カテゴリULは既に更新済み")

# ===== 4. CSS追加 =====
old_css = '    footer{{'
new_css = """    .cat-item{{cursor:pointer;padding:.35rem .5rem;border-radius:8px;transition:background .15s;list-style:none;}}
    .cat-item:hover{{background:#fff0f0;color:var(--red);}}
    .cat-item.active{{background:var(--red)!important;color:#fff!important;font-weight:900;}}
    .cat-item::before{{content:none!important;}}
    footer{{"""
if '.cat-item{{' not in src:
    src = src.replace(old_css, new_css, 1)
    print("✅ CSSを追加")
else:
    print("⏭️  CSSは既に存在")

# ===== 5. JS追加 =====
old_js = '    setInterval(tick, 1000); tick();'
new_js = """    setInterval(tick, 1000); tick();

    function filterCat(cat) {{
      document.querySelectorAll('.card').forEach(function(c) {{
        c.style.display = (cat==='all' || c.dataset.cat===cat) ? '' : 'none';
      }});
      document.querySelectorAll('.cat-item').forEach(function(li) {{
        li.classList.toggle('active', li.dataset.cat===cat);
      }});
    }}"""

if 'function filterCat(' not in src:
    src = src.replace(old_js, new_js, 1)
    print("✅ filterCat JS関数を追加")
else:
    print("⏭️  filterCat関数は既に存在")

# ===== 書き込み =====
with open('generate_site_final.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("\n🎉 パッチ完了！次のコマンドでサイトを再生成してね:")
print("   py generate_site_final.py")
