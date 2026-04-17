Import os
from flask import Flask, request, jsonify
from notion_client import Client

app = Flask(__name__)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")


def search_notion(stock_name: str):
    notion = Client(auth=NOTION_TOKEN)

    # 1. DB에서 종목명 검색
    results = notion.databases.query(
        database_id=NOTION_DB_ID,
        filter={
            "property": "이름",
            "title": {"contains": stock_name}
        }
    )

    if not results["results"]:
        return None

    page = results["results"][0]
    page_id = page["id"]
    props = page["properties"]

    # 2. 태그 (텍스트 컬럼 = 멀티셀렉트) 추출
    tags = []
    if "텍스트" in props:
        prop = props["텍스트"]
        if prop["type"] == "multi_select":
            tags = [s["name"] for s in prop["multi_select"]]
        elif prop["type"] == "rich_text":
            tags = ["".join([t["plain_text"] for t in prop["rich_text"]])]

    # 3. 날짜 추출
    date_str = ""
    if "날짜" in props and props["날짜"]["date"]:
        date_str = props["날짜"]["date"]["start"]

    # 4. 페이지 본문 블록 전체 읽기 (모든 텍스트 그대로)
    blocks = notion.blocks.children.list(block_id=page_id)
    body_lines = []
    for block in blocks["results"]:
        btype = block["type"]
        rich = block.get(btype, {}).get("rich_text", [])
        text = "".join([t["plain_text"] for t in rich]).strip()
        if text:
            body_lines.append(text)

    return {
        "name": stock_name,
        "date": date_str,
        "tags": tags,
        "body": body_lines,
        "notion_url": f"https://www.notion.so/{page_id.replace('-', '')}"
    }


@app.route("/query", methods=["GET"])
def query():
    stock_name = (request.args.get("stock") or "").strip()
    if not stock_name:
        return jsonify({"status": "error", "message": "종목명을 입력해주세요"}), 400

    data = search_notion(stock_name)
    if data is None:
        return jsonify({
            "status": "not_found",
            "message": f"'{stock_name}' 을 노션 DB에서 찾을 수 없습니다"
        }), 404

    # 네이버 금융 검색 URL
    naver_url = f"https://finance.naver.com/search/search.naver?query={stock_name}"

    # 단축어 화면에 표시할 텍스트 구성
    lines = []
    lines.append(f"📈 {data['name']}")
    if data["date"]:
        lines.append(f"📅 등록일: {data['date']}")
    lines.append("")
    lines.append(f"🔗 네이버 금융: {naver_url}")
    lines.append("")

    if data["tags"]:
        lines.append(f"🏷 테마: {', '.join(data['tags'])}")
        lines.append("")

    if data["body"]:
        lines.append("📝 분석 내용")
        lines.append("--------------------")
        for line in data["body"]:
            lines.append(line)
    else:
        lines.append("(본문 내용 없음)")

    lines.append("")
    lines.append(f"📎 노션 원문: {data['notion_url']}")

    return jsonify({
        "status": "ok",
        "text": "\n".join(lines)
    })


@app.route("/health")
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
여기서 네이버 금융의 url이 잘못된거 같은데? 확인해봐