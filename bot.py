import os
import time
import json
import requests
from datetime import datetime, timedelta
from google import genai

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_GO_KR_API_KEY = os.environ.get("GONGGONGDATA_API")

CROP_CODE_MAP = [
    {"name": "배추", "cat_code": "200", "item_code": "211", "kind_code": "01", "keyword": "배추"},
    {"name": "무", "cat_code": "200", "item_code": "231", "kind_code": "01", "keyword": "무"},
    {"name": "양배추", "cat_code": "200", "item_code": "212", "kind_code": "00", "keyword": "양배추"},
    {"name": "백다다기오이", "cat_code": "200", "item_code": "223", "kind_code": "02", "keyword": "다다기"},
    {"name": "일반토마토", "cat_code": "200", "item_code": "225", "kind_code": "00", "keyword": "토마토"},
    {"name": "홍고추", "cat_code": "200", "item_code": "243", "kind_code": "00", "keyword": "홍고추"},
    {"name": "신미계 풋고추(청양)", "cat_code": "200", "item_code": "242", "kind_code": "02", "keyword": "청양"},
    {"name": "오이맛고추", "cat_code": "200", "item_code": "242", "kind_code": "03", "keyword": "오이맛"},
    {"name": "모닝고추(일반/아삭이계)", "cat_code": "200", "item_code": "242", "kind_code": "00", "keyword": "모닝"}
]

def get_market_data_by_codes():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    collected_data = []
    url = "http://apis.data.go.kr/B552895/openapi/service/OrgPriceAuctionService/getExactProdPriceList"
    
    for crop in CROP_CODE_MAP:
        params = {
            "serviceKey": DATA_GO_KR_API_KEY,
            "numOfRows": "20",
            "pageNo": "1",
            "_type": "json",
            "saleDate": yesterday,
            "large": "02",
            "PrdlstCd": crop["item_code"],
            "SpciesCd": crop["kind_code"]
        }
        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200 and ("item" in res.text or "price" in res.text.lower()):
                collected_data.append(f"[{crop['name']} (품목코드:{crop['item_code']}/품종:{crop['kind_code']})]\n{res.text[:800]}")
        except Exception:
            pass

    if not collected_data:
        return "데이터 수집 원시 샘플"
    return "\n\n".join(collected_data)

def generate_briefing(raw_data):
    client = genai.Client(api_key=GEMINI_API_KEY)
    crop_list_str = "\n".join([f"- {c['name']} (품목코드 {c['item_code']}-{c['kind_code']})" for c in CROP_CODE_MAP])
    
    prompt = f"""
    당신은 베테랑 원예 농산물 및 종자 영업 전문가입니다.
    현재 날짜 기준으로 직전 주간 및 전날의 국내 주요 산지(강원, 영남, 호남 등)의 기상 상황(기온, 일조량, 강수, 일교차 등)과 계절적 생육 특성을 입체적으로 연계하여, 가락시장 경매 데이터에 훌륭한 스토리와 분석을 살 붙여 브리핑을 작성해 주세요.

    [필수 분류 대상 및 품목코드]:
    {crop_list_str}

    [수집된 경매 데이터(물량 및 금액 팩트)]:
    {raw_data}

    [작성 규칙]:
    1. 9가지 작물을 각각 빠짐없이 개별 항목으로 나누어 작성할 것
    2. 각 품목별로 규격, 평균가, 최고가, 그리고 해당 거래 물량(반입량)을 명확히 기재할 것
    3. 최근 산지의 날씨 흐름(일조량 부족, 일교차 큰 환절기, 강수 영향, 저온 기조 등)이 해당 작물의 생육과 출하량에 미친 인과관계를 전문적이고 설득력 있게 1~2줄의 분석 스토리로 녹여낼 것
    4. 별표(**)를 사용한 강조 문법은 절대 사용하지 말 것
    """
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(3)

def send_telegram_message(text_content):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": text_content
    }
    res = requests.post(send_url, data=payload)
    if res.status_code == 200:
        print("텔레그램 자동 브리핑 전송 완료!")
    else:
        print(f"전송 실패: {res.text}")

if __name__ == "__main__":
    print("데이터 수집 및 제미나이 기후 연계 분석 브리핑 생성 시작...")
    market_data = get_market_data_by_codes()
    briefing = generate_briefing(market_data)
    send_telegram_message(briefing)
