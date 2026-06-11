import os, requests, json

app_id    = os.environ.get("RAKUTEN_APP_ID", "")
access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")

r = requests.get(
    "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401",
    params={
        "applicationId": app_id,
        "accessKey":     access_key,
        "keyword":       "食品",
        "hits":          2,
        "genreId":       0,
        "format":        "json",
    }
)
print(f"ステータス: {r.status_code}")
data = r.json()
print(f"トップキー: {list(data.keys())}")

items = data.get("Items", data.get("items", data.get("アイテム", [])))
print(f"件数: {len(items)}")

if items:
    first = items[0]
    print(f"最初の要素のキー: {list(first.keys())}")
    inner_key = list(first.keys())[0]
    inner = first[inner_key]
    if isinstance(inner, dict):
        print(f"内側のキー: {list(inner.keys())[:8]}")
    else:
        print(f"内側の値: {str(inner)[:200]}")
else:
    print(f"レスポンス全体:\n{json.dumps(data, ensure_ascii=False)[:800]}")
