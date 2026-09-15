import io
import os
import time
import datetime
import sqlite3
import zipfile
import base64
import random
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import streamlit as st
from PIL import Image

# ==========================================
# 1. 페이지 기본 설정 및 스타일
# ==========================================
st.set_page_config(
    page_title="🐷 아기돼지 삼형제의 뚝딱! 주식&채권 집짓기",
    page_icon="🐷",
    layout="centered"
)

# 다크 모드 및 모바일 가독성 방어 CSS
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

html, body, [class*="css"], div, span, h1, h2, h3, h4, h5, h6, p, button, input, li {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif !important;
}

.main-title { font-size: 26px; font-weight: 700; text-align: center; color: #333333 !important; margin-bottom: 20px; }
.question-box { background-color: #f8f9fa !important; padding: 22px; border-radius: 15px; border: 1px solid #e9ecef; margin-bottom: 20px; }
.question-text { font-size: 19px; font-weight: 700; color: #212529 !important; margin: 0; line-height: 1.5; }

.persona-card { background-color: #e7f5ff !important; color: #212529 !important; padding: 20px; border-radius: 15px; border-left: 5px solid #1c7ed6; margin-bottom: 20px; }
.persona-card h2, .persona-card p { color: #212529 !important; }

.portfolio-card { background-color: #f3f0ff !important; color: #212529 !important; padding: 18px; border-radius: 12px; border: 1px solid #d0bfff; margin-bottom: 20px; }
.portfolio-card p, .portfolio-card li { color: #212529 !important; }

.product-card { background-color: #ffffff !important; color: #212529 !important; padding: 18px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.product-card h3, .product-card h4, .product-card p, .product-card span { color: #212529 !important; }

.metric-box { background-color: #f1f3f5 !important; color: #212529 !important; padding: 12px; border-radius: 8px; margin-top: 10px; margin-bottom: 10px; font-size: 14px; }
.etf-metric-box { background-color: #fff5f5 !important; color: #212529 !important; padding: 12px; border-radius: 8px; margin-top: 10px; margin-bottom: 10px; border: 1px solid #ffe3e3; font-size: 14px; }

.biz-desc { font-size: 14px; color: #495057 !important; background-color: #f8f9fa !important; padding: 10px; border-radius: 8px; margin-top: 8px; border-left: 3px solid #ced4da; line-height: 1.5; }
.advice-box { background-color: #fff9db !important; color: #212529 !important; padding: 12px; border-radius: 8px; margin-top: 10px; border-left: 3px solid #fcc419; font-size: 14px; line-height: 1.5; }
.etf-advice-box { background-color: #fff0f6 !important; color: #212529 !important; padding: 12px; border-radius: 8px; margin-top: 10px; border-left: 3px solid #d6336c; font-size: 14px; line-height: 1.5; }

.adjust-box { background-color: #f1f8ff !important; color: #212529 !important; border: 2px dashed #339af0; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.adjust-box h3, .adjust-box p, .adjust-box label { color: #212529 !important; }

.stButton > button {
    font-family: 'Noto Sans KR', sans-serif !important;
    font-size: 15px !important;
    font-weight: 500 !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# API KEY 및 기준 설정
DART_API_KEY = "f80dc14402d19c3d7a3cb9430d63bb1342dd3a72"
MARKET_GOV_BOND_RATE = 3.5  # 기준 국채 10년물 금리 (%)

# ==========================================
# 2. 실시간 재무 데이터 Fetcher 및 동적 조언 생성기
# ==========================================
@st.cache_data(ttl=1800)
def fetch_realtime_metrics(ticker, default_data, is_etf=False):
    if is_etf:
        return {"price": default_data.get("price", 0), "per": 0.0, "pbr": 0.0, "roe": 0.0, "eps": 0}
        
    try:
        url = f"https://finance.naver.com/item/main.naver?code={ticker}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=4)
        
        if res.status_code == 200:
            tables = pd.read_html(io.StringIO(res.text))
            fetched = {}
            
            for df in tables:
                df_str = df.astype(str)
                for idx, row in df_str.iterrows():
                    row_txt = " ".join(row.values)
                    
                    if "PER" in row_txt and "per" not in fetched:
                        for val in row.values:
                            val_clean = str(val).replace(',', '').replace('배', '').strip()
                            try:
                                v = float(val_clean)
                                if v > 0 and v < 2000:
                                    fetched["per"] = v
                                    break
                            except: pass
                            
                    if "PBR" in row_txt and "pbr" not in fetched:
                        for val in row.values:
                            val_clean = str(val).replace(',', '').replace('배', '').strip()
                            try:
                                v = float(val_clean)
                                if v > 0 and v < 100:
                                    fetched["pbr"] = v
                                    break
                            except: pass

                    if "ROE" in row_txt and "roe" not in fetched:
                        for val in row.values:
                            val_clean = str(val).replace(',', '').replace('%', '').strip()
                            try:
                                v = float(val_clean)
                                if -100 < v < 200:
                                    fetched["roe"] = v
                                    break
                            except: pass

                    if "EPS" in row_txt and "eps" not in fetched:
                        for val in row.values:
                            val_clean = str(val).replace(',', '').replace('원', '').strip()
                            try:
                                v = int(float(val_clean))
                                if v != 0:
                                    fetched["eps"] = v
                                    break
                            except: pass

            return {
                "price": default_data.get("price", 50000),
                "per": fetched.get("per", default_data.get("per", 12.5)),
                "pbr": fetched.get("pbr", default_data.get("pbr", 1.2)),
                "roe": fetched.get("roe", default_data.get("roe", 9.5)),
                "eps": fetched.get("eps", default_data.get("eps", 3500))
            }
            
    except Exception as e:
        pass
        
    return default_data


def generate_investment_advice(stock_tag, name, per, pbr, roe, market_rate=3.5):
    if pbr > 0 and pbr < 0.7:
        return f"🔍 <b>저PBR 극심 저평가 분석:</b> 자산가치 대비 PBR({pbr}배)이 매우 낮아 하방 방어력이 강력합니다. 정부의 밸류업 정책 및 자산 가치 재평가 수혜를 기다리는 장기 적립 관점에 최적입니다."
    
    if per > 0 and per < 8.0:
        return f"💵 <b>저PER 실속형 분석:</b> 벌어들이는 이익(PER {per}배) 대비 주가가 저렴하여 실적 안전마블이 탄탄합니다. 현금창출력이 뛰어난 알짜 우량주입니다."
    
    if roe >= 15.0:
        return f"🚀 <b>고ROE 초우량 성장 분석:</b> 자기자본이익률(ROE {roe}%)이 매우 우수하여 주주 자금을 효율적으로 불려나가고 있습니다. 복리 스노우볼 효과를 기대하며 목표 비중을 채워가세요."
    
    if per > 50.0:
        return f"⚡ <b>고PER 성장 기대감 분석:</b> 미래 성장성에 대한 시장 기대로 PER({per}배)이 높게 형성되어 있습니다. 실적 성장 속도가 기대치에 미치지 못할 경우 변동성이 클 수 있으므로 <b>분할 매수 및 손절선 준수</b>가 필수적입니다."

    if stock_tag == "HIGH_DIVIDEND":
        return f"💡 <b>고배당 인컴 조언:</b> 현재 주가수익비율(PER {per}배) 대비 시가배당 매력이 높습니다. 주가 등락보다 꼬박꼬박 들어오는 <b>고정 배당 현금흐름</b>에 집중하세요."
    elif stock_tag == "DIVIDEND_GROWTH":
        return f"🌱 <b>배당성장 복리 조언:</b> 안정적인 이익 성장을 바탕으로 배당금이 우상향하는 구조입니다. <b>배당금 재투자 전략</b>을 통해 장기 복리 효과를 노려보세요."
    elif stock_tag == "SEMICON_TECH":
        return f"💻 <b>AI·반도체 주도주 조언:</b> 글로벌 테크 생태계의 핵심 독점력을 보유하고 있습니다. 업황 순환 사이클에 맞춰 <b>눌림목 중심의 분할 매집</b>이 유효합니다."
    elif stock_tag == "NEXT_GEN_TECH":
        return f"🔋 <b>신기술 모멘텀 조언:</b> 미래 산업 패러다임 전환의 중심에 있는 성장주입니다. 단기 수급 변동성이 크므로 <b>손절선(-7~10%) 기준을 철저히 설정</b>하세요."
    elif stock_tag == "MOMENTUM_SWING":
        return f"🏄‍♂️ <b>수급 스윙 조언:</b> 시장에서 강한 거래대금과 모멘텀을 받고 있습니다. 추세가 꺾일 경우 빠르게 대응하는 <b>기민한 호흡의 트레이딩</b>을 권장합니다."
    elif stock_tag == "MEGA_TREND":
        return f"🤖 <b>메가트렌드 장기 올인 조언:</b> 시대를 거스를 수 없는 거대한 산업 흐름의 1등 기업입니다. 단기 조정에 흔들리지 않고 <b>장기 적립식 구조</b>로 모아가세요."
    elif stock_tag == "INDEX_LEVERAGE":
        return f"⚡ <b>지수 레버리지 파생 조언:</b> 지수 일간 변동의 2배를 추종하므로 횡보장 시 <b>음의 복리 효과(Volatility Drag)</b>로 자산이 깎일 위험이 큽니다. 장기 투자를 금지합니다."
    elif stock_tag == "VENTURE_BIO":
        return f"🧪 <b>바이오/벤처 잭팟 조언:</b> 임상 및 기술 이전 성과에 따라 주가가 극단적으로 움직입니다. 단일 종목 위험을 고려해 <b>포트폴리오의 소액(10% 이내)</b>으로만 접근하세요."

    return f"💡 <b>종목 점검 조언:</b> 무위험 국채 금리({market_rate}%)와 비교하여 기업의 실적 성장성을 꼼꼼히 점검하며 분할 매수하세요."


def generate_bond_advice(bond_name, bond_type):
    if "CD금리" in bond_name:
        return "📌 <b>CD금리 파킹 분석:</b> 매일 이자가 복리로 산정되며 원금 손실 위험이 전혀 없습니다. 주식 매수 대기 자금을 안전하게 보관하는 <b>최적의 단기 파킹 자산</b>입니다."
    elif "KOFR" in bond_name:
        return "📌 <b>KOFR 무위험 금리 분석:</b> 초단기 무위험 지표금리를 추종하여 금융시장 충격에도 흔들림 없이 <b>안전하게 현금을 유동화</b>할 수 있습니다."
    elif "30년국채" in bond_name:
        return "🏛️ <b>장기 국채 듀레이션 분석:</b> 30년 만기 국채 특성상 금리가 하락할 때 <b>채권 가격이 가장 크게 상승(자본 차익 극대화)</b>하는 구조를 가집니다. 금리 인하 사이클에 최적입니다."
    elif "은행채" in bond_name:
        return "🏢 <b>만기매칭 은행채 분석:</b> AA+ 등급 이상의 시중 은행채에 투자하여 만기까지 보유 시 <b>확정된 고정 이자 수익</b>을 안전하게 수취할 수 있습니다."
    return "📌 <b>안전 자산 분석:</b> 원금 보존과 안정적인 이자 수입을 동시에 달성할 수 있는 채권 포트폴리오의 핵심 방어 자산입니다."

# ==========================================
# 3. 성향별 세부 추천 데이터 풀
# ==========================================
TARGET_STOCKS_BY_PERSONA = {
    "PARKING_ETF": [
        {"name": "KODEX CD금리액티브(합성)", "ticker": "459580", "type": "파킹형 ETF", "desc": "CD 91일물 금리를 추종하며 매일 복리 이자가 누적되는 원금 안심 파킹 상품입니다."},
        {"name": "TIGER KOFR금리액티브(합성)", "ticker": "423160", "type": "파킹형 ETF", "desc": "한국 무위험지표금리(KOFR)를 추종하여 예적금 대비 뛰어난 유동성을 제공합니다."}
    ],
    "BOND_INVESTMENT": [
        {"name": "ACE KOREA 30년국채액티브", "ticker": "458650", "type": "장기 국채 ETF", "desc": "대한민국 30년 만기 국채에 투자하여 안정적인 이자와 함께 금리 인하 시 가격 상승 수익을 노립니다."},
        {"name": "KODEX 24-12 은행채(AA+이상)액티브", "ticker": "469180", "type": "만기매칭형 채권 ETF", "desc": "AA+ 등급 이상 초우량 은행채에 집중 투자하여 만기까지 고정 금리 수익을 확실하게 수취합니다."}
    ],
    "HIGH_DIVIDEND": [
        {"name": "기업은행", "ticker": "024110", "price": 14000, "per": 3.4, "pbr": 0.32, "roe": 9.5, "eps": 4117, "desc": "중소기업 국책은행으로 연 7~8% 수준의 압도적 고배당 수익률을 자랑합니다."},
        {"name": "KT&G", "ticker": "033780", "price": 92000, "per": 11.2, "pbr": 1.1, "roe": 10.1, "eps": 8214, "desc": "담배 및 건기식 사업의 탄탄한 독점적 현금흐름으로 대표 고배당주로 꼽힙니다."},
        {"name": "맥쿼리인프라", "ticker": "088980", "price": 12500, "per": 14.2, "pbr": 1.25, "roe": 8.9, "eps": 880, "desc": "국내 인프라 자산 투자로 매년 반기마다 높은 분배금을 지급하는 배당 대표주입니다."}
    ],
    "DIVIDEND_GROWTH": [
        {"name": "현대차", "ticker": "005380", "price": 240000, "per": 5.8, "pbr": 0.65, "roe": 12.4, "eps": 41379, "desc": "실적 성장에 맞춰 주주환원 및 배당금을 지속 상향하는 대표 배당성장주입니다."},
        {"name": "하나금융지주", "ticker": "086790", "price": 61000, "per": 4.8, "pbr": 0.41, "roe": 9.1, "eps": 12708, "desc": "적극적 자사주 매입/소각과 분기 배당 증액을 실천하는 배당 우량주입니다."},
        {"name": "SK텔레콤", "ticker": "017670", "price": 53000, "per": 9.5, "pbr": 0.95, "roe": 9.8, "eps": 5578, "desc": "안정적인 5G 캐시카우를 바탕으로 매년 안정적 배당금을 늘려가는 종목입니다."}
    ],
    "LARGE_CAP": [
        {"name": "삼성전자", "ticker": "005930", "price": 75000, "per": 13.5, "pbr": 1.2, "roe": 9.2, "eps": 5555, "desc": "글로벌 전자기기 및 반도체 1위 대한민국 시가총액 대표 대장주입니다."},
        {"name": "NAVER", "ticker": "035420", "price": 185000, "per": 20.1, "pbr": 1.3, "roe": 6.8, "eps": 9203, "desc": "국내 1위 검색 포털을 기반으로 AI, 웹툰, 클라우드 사업을 지배하는 대형주입니다."},
        {"name": "POSCO홀딩스", "ticker": "005490", "price": 370000, "per": 15.3, "pbr": 0.55, "roe": 3.8, "eps": 24183, "desc": "철강 사업과 함께 친환경 미래소재 사업을 지배하는 지주사입니다."}
    ],
    "SEMICON_TECH": [
        {"name": "SK하이닉스", "ticker": "000660", "price": 180000, "per": 11.8, "pbr": 1.85, "roe": 15.6, "eps": 15254, "desc": "HBM(고대역폭 메모리) 분야 글로벌 1위 핵심 AI 반도체 선도 기업입니다."},
        {"name": "한미반도체", "ticker": "042700", "price": 110000, "per": 48.2, "pbr": 8.5, "roe": 21.4, "eps": 2282, "desc": "HBM 제조 필수 장비인 TC 본더 독점 생산으로 AI 기술을 주도하는 반도체 대표주입니다."},
        {"name": "리노공업", "ticker": "058470", "price": 200000, "per": 24.5, "pbr": 4.6, "roe": 20.1, "eps": 8163, "desc": "반도체 테스트용 핀 및 소켓 기술력으로 글로벌 빅테크 기업들에 공급하는 초우량 기업입니다."}
    ],
    "NEXT_GEN_TECH": [
        {"name": "LG에너지솔루션", "ticker": "373220", "price": 390000, "per": 65.2, "pbr": 4.5, "roe": 7.1, "eps": 5981, "desc": "글로벌 전기차용 배터리 및 에너지 저장장치(ESS) 분야의 2차전지 선도 기업입니다."},
        {"name": "에코프로비엠", "ticker": "247540", "price": 170000, "per": 120.5, "pbr": 6.8, "roe": 4.1, "eps": 1410, "desc": "하이니켈 양극재 제조를 바탕으로 친환경 에너지를 주도하는 대표 2차전지 종목입니다."},
        {"name": "레인보우로보틱스", "ticker": "277810", "price": 160000, "per": 180.0, "pbr": 12.4, "roe": 5.1, "eps": 888, "desc": "협동로봇 및 휴머노이드 로봇 기술을 보유한 미래 차세대 로봇 공학 대표주입니다."}
    ],
    "MOMENTUM_SWING": [
        {"name": "삼양식품", "ticker": "003230", "price": 580000, "per": 22.1, "pbr": 5.8, "roe": 29.4, "eps": 26244, "desc": "글로벌 K-푸드 수출 폭발로 매 분기 강력한 실적 및 주가 모멘텀을 타는 스윙주입니다."},
        {"name": "HD현대일렉트릭", "ticker": "267260", "price": 290000, "per": 22.4, "pbr": 5.1, "roe": 26.8, "eps": 12946, "desc": "북미 전력망 교체 및 변압기 슈퍼사이클 수혜로 강한 상승 파도를 타는 모멘텀주입니다."},
        {"name": "현대오토에버", "ticker": "307950", "price": 165000, "per": 28.5, "pbr": 3.1, "roe": 12.4, "eps": 5780, "desc": "자율주행 소프트웨어 및 그룹 SW 통합 수혜로 가파른 상승 텐션을 지닌 주도주입니다."}
    ],
    "MEGA_TREND": [
        {"name": "NAVER", "ticker": "035420", "price": 185000, "per": 20.1, "pbr": 1.3, "roe": 6.8, "eps": 9203, "desc": "자체 AI 모델 '하이퍼클로바X' 기반으로 대한민국 AI 플랫폼을 주도하는 메가트렌드 핵심주입니다."},
        {"name": "SK하이닉스", "ticker": "000660", "price": 180000, "per": 11.8, "pbr": 1.85, "roe": 15.6, "eps": 15254, "desc": "AI 시대 반도체 뇌 역할을 하는 HBM 독점력을 갖춘 거대 메가트렌드 대표 기업입니다."},
        {"name": "두산로보틱스", "ticker": "454910", "price": 68000, "per": 999.0, "pbr": 7.2, "roe": -8.1, "eps": -320, "desc": "제조 및 서비스업 노동력을 대체할 지능형 협동로봇 메가트렌드 선도 기업입니다."}
    ],
    "INDEX_LEVERAGE": [
        {"name": "KODEX 레버리지", "ticker": "122630", "price": 17500, "per": 0.0, "pbr": 0.0, "roe": 0.0, "eps": 0, "desc": "KOSPI 200 지수의 일간 변동률을 2배 추종하는 지수 레버리지 ETF입니다."},
        {"name": "KODEX 200선물인버스2X", "ticker": "252670", "price": 2200, "per": 0.0, "pbr": 0.0, "roe": 0.0, "eps": 0, "desc": "KOSPI 200 선물 지수 하락 시 2배 수익을 노리는 파생형 곱버스 ETF입니다."},
        {"name": "KODEX 코스닥150레버리지", "ticker": "233740", "price": 9500, "per": 0.0, "pbr": 0.0, "roe": 0.0, "eps": 0, "desc": "코스닥 150 지수의 강한 변동성을 2배 추종하여 고수익을 지향하는 레버리지 상품입니다."}
    ],
    "VENTURE_BIO": [
        {"name": "HLB", "ticker": "028300", "price": 85000, "per": 999.0, "pbr": 14.2, "roe": -12.5, "eps": -1450, "desc": "항암 신약 FDA 승인 모멘텀에 따라 극극단적 시세 변동성을 보이는 대표 제약바이오주입니다."},
        {"name": "루닛", "ticker": "328130", "price": 55000, "per": 999.0, "pbr": 6.2, "roe": -15.2, "eps": -1200, "desc": "딥러닝 기반 AI 의료 영상 진단 및 암 치료 솔루션을 개발하는 헬스케어 AI 혁신 벤처입니다."},
        {"name": "두산로보틱스", "ticker": "454910", "price": 68000, "per": 999.0, "pbr": 7.2, "roe": -8.1, "eps": -320, "desc": "협동로봇 및 스마트 팩토리 시장 팽창 기대감으로 강력한 주가 텐션을 지닌 성장 테마주입니다."}
    ],
    "VALUE_STOCK": [
        {"name": "현대모비스", "ticker": "012330", "price": 230000, "per": 6.2, "pbr": 0.48, "roe": 8.1, "eps": 37096, "desc": "보유 자산 대비 PBR 0.4배 수준으로 극심하게 저평가된 대표 밸류업 종목입니다."},
        {"name": "삼성물산", "ticker": "028260", "price": 145000, "per": 10.4, "pbr": 0.71, "roe": 7.2, "eps": 13942, "desc": "핵심 계열사 지분을 다수 보유한 자산가치 우수 저PBR 가치주입니다."},
        {"name": "GS", "ticker": "078930", "price": 44000, "per": 3.8, "pbr": 0.31, "roe": 8.4, "eps": 11578, "desc": "에너지, 유통 계열사를 지배하며 순자산가치 대비 심하게 저평가된 대표 지주사입니다."}
    ]
}

# ==========================================
# 4. 이미지 렌더링 함수 (PIL 모바일 안정화 및 백업 렌더링)
# ==========================================
def render_three_pigs_crossroads_image():
    full_html = """<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>*{box-sizing:border-box;margin:0;padding:0;}body{background:transparent;display:flex;justify-content:center;align-items:center;font-family:'Noto Sans KR',sans-serif;overflow:hidden;}.scene{position:relative;width:100%;max-width:900px;height:480px;background:linear-gradient(to bottom,#617b8f 0%,#617b8f 78%,#365e34 78%,#365e34 100%);border-radius:12px;box-shadow:0 15px 35px rgba(0,0,0,0.35);display:flex;justify-content:space-around;align-items:flex-end;padding-bottom:25px;box-sizing:border-box;}.pig-column{display:flex;flex-direction:column;align-items:center;position:relative;transform:scale(0.85);transform-origin:bottom center;}.bubble{width:160px;height:160px;background:#ffffff;border-radius:50%;display:flex;justify-content:center;align-items:center;position:relative;box-shadow:0 6px 20px rgba(0,0,0,0.15);margin-bottom:10px;}.wave-left,.wave-right{position:absolute;top:50%;transform:translateY(-50%);width:12px;height:45px;border:solid 2.5px #ffffff;border-color:transparent #ffffff transparent transparent;border-radius:50%;}.wave-left{left:-25px;transform:translateY(-50%) scaleX(-1);}.wave-right{right:-25px;}.bubble-dots{display:flex;flex-direction:column;align-items:center;margin-bottom:10px;}.dot{background:#ffffff;border-radius:50%;margin:2px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1);}.pig-column:nth-child(1) .dot-1{width:10px;height:10px;}.pig-column:nth-child(1) .dot-2{width:6px;height:6px;}.pig-column:nth-child(2) .dot-1{width:12px;height:12px;}.pig-column:nth-child(2) .dot-2{width:8px;height:8px;}.pig-column:nth-child(2) .dot-3{width:5px;height:5px;}.pig-column:nth-child(3) .dot-1{width:10px;height:10px;}.pig-column:nth-child(3) .dot-2{width:6px;height:6px;}.content-box{display:flex;align-items:center;justify-content:center;gap:8px;}.pig-character{width:120px;display:flex;flex-direction:column;align-items:center;}.pig-head{width:115px;height:98px;background:#e8b4a2;border-radius:50% 50% 42% 42%;position:relative;display:flex;justify-content:center;align-items:center;}.ear{position:absolute;width:22px;height:22px;background:#e8b4a2;border-radius:50% 50% 0 0;top:-4px;}.ear.left{left:12px;transform:rotate(-20deg);}.ear.right{right:12px;transform:rotate(20deg);}.snout{position:absolute;top:50px;width:32px;height:20px;background:#d89a84;border-radius:50%;display:flex;justify-content:center;align-items:center;gap:5px;}.nostril{width:4px;height:6px;background:#a06552;border-radius:50%;}.pig-1 .eyes{position:absolute;top:26px;display:flex;justify-content:space-around;width:100%;padding:0 16px;box-sizing:border-box;}.pig-1 .eye{width:16px;height:18px;background:#ffffff;border:2px solid #222;border-radius:50%;position:relative;display:flex;justify-content:center;align-items:center;}.pig-1 .eye::after{content:'';width:6px;height:6px;background:#222;border-radius:50%;position:absolute;}.pig-1 .brow{position:absolute;top:18px;width:100%;display:flex;justify-content:space-around;padding:0 14px;box-sizing:border-box;}.pig-1 .brow span{width:12px;height:3px;background:#222;border-radius:2px;}.pig-1 .brow span:first-child{transform:rotate(-15deg);}.pig-1 .brow span:last-child{transform:rotate(15deg);}.pig-1 .mouth{position:absolute;bottom:12px;width:14px;height:12px;background:#222;border-radius:50%;}.pig-2 .eyes{position:absolute;top:35px;display:flex;justify-content:space-around;width:100%;padding:0 22px;box-sizing:border-box;}.pig-2 .eye{width:7px;height:7px;background:#222;border-radius:50%;}.pig-2 .brow{position:absolute;top:25px;width:100%;display:flex;justify-content:space-around;padding:0 17px;box-sizing:border-box;}.pig-2 .brow span{width:10px;height:3px;background:#222;border-radius:2px;transform:rotate(-25deg);}.pig-2 .brow span:last-child{transform:rotate(25deg);}.pig-2 .mouth{position:absolute;bottom:16px;width:10px;height:3px;background:#a06552;border-radius:50%;border-top:2px solid #222;}.pig-3 .eyes{position:absolute;top:30px;display:flex;justify-content:space-around;width:100%;padding:0 18px;box-sizing:border-box;}.pig-3 .eye{width:12px;height:14px;background:#222;border-radius:50%;}.pig-3 .brow{position:absolute;top:22px;width:100%;display:flex;justify-content:space-around;padding:0 15px;box-sizing:border-box;}.pig-3 .brow span{width:10px;height:3px;background:#222;border-radius:2px;transform:rotate(20deg);}.pig-3 .brow span:last-child{transform:rotate(-20deg);}.pig-3 .mouth{position:absolute;bottom:12px;width:16px;height:14px;background:#b83b3b;border-radius:50%;border:2px solid #222;}.pig-body{width:105px;height:72px;border-radius:16px 16px 0 0;}.shirt-green{background:repeating-linear-gradient(45deg,#fff,#fff 8px,#3d6635 8px,#3d6635 16px);}.shirt-yellow{background:repeating-linear-gradient(45deg,#fff,#fff 8px,#d4af37 8px,#d4af37 16px);}.shirt-red{background:repeating-linear-gradient(45deg,#fff,#fff 8px,#b83b3b 8px,#b83b3b 16px);}.pants{width:85px;height:35px;background:#232d36;border-radius:4px 4px 0 0;}</style></head><body><div class="scene"><div class="pig-column"><div class="bubble"><div class="wave-left"></div><div class="wave-right"></div><div class="content-box" style="flex-direction:column;gap:2px;"><span style="font-size:32px;">📈</span><span style="color:#e74c3c;font-weight:900;font-size:30px;letter-spacing:-2px;">X3</span></div></div><div class="bubble-dots"><div class="dot dot-1"></div><div class="dot dot-2"></div></div><div class="pig-character"><div class="pig-head pig-1"><div class="ear left"></div><div class="ear right"></div><div class="brow"><span></span><span></span></div><div class="eyes"><div class="eye"></div><div class="eye"></div></div><div class="snout"><div class="nostril"></div><div class="nostril"></div></div><div class="mouth"></div></div><div class="pig-body shirt-green"></div><div class="pants"></div></div></div><div class="pig-column"><div class="bubble"><div class="content-box"><span style="font-size:30px;">💵</span><span style="color:#27ae60;font-weight:bold;font-size:36px;">$</span></div></div><div class="bubble-dots"><div class="dot dot-1"></div><div class="dot dot-2"></div><div class="dot dot-3"></div></div><div class="pig-character"><div class="pig-head pig-2"><div class="ear left"></div><div class="ear right"></div><div class="brow"><span></span><span></span></div><div class="eyes"><div class="eye"></div><div class="eye"></div></div><div class="snout"><div class="nostril"></div><div class="nostril"></div></div><div class="mouth"></div></div><div class="pig-body shirt-yellow"></div><div class="pants"></div></div></div><div class="pig-column"><div class="bubble"><div class="content-box" style="flex-direction:column;gap:4px;align-items:flex-end;"><div style="background:#1982c4;color:white;padding:2px 8px;border-radius:4px;font-size:13px;font-weight:bold;transform:rotate(-5deg);">통장</div><div style="font-size:24px;margin-top:-2px;">🪙🪙🪙</div></div></div><div class="bubble-dots"><div class="dot dot-1"></div><div class="dot dot-2"></div></div><div class="pig-character"><div class="pig-head pig-3"><div class="ear left"></div><div class="ear right"></div><div class="brow"><span></span><span></span></div><div class="eyes"><div class="eye"></div><div class="eye"></div></div><div class="snout"><div class="nostril"></div><div class="nostril"></div></div><div class="mouth"></div></div><div class="pig-body shirt-red"></div><div class="pants"></div></div></div></div></body></html>"""
    b64_html = base64.b64encode(full_html.encode('utf-8')).decode('utf-8')
    st.components.v1.iframe(f"data:text/html;charset=utf-8;base64,{b64_html}", height=480, scrolling=False)


def render_image_by_filename(filename, fallback_msg):
    base_name = os.path.splitext(filename)[0]
    candidate_files = [
        filename,                           # three_pigs.png
        filename.lower(),                   # three_pigs.png
        f"{base_name.lower()}.jpg",
        f"{base_name.lower()}.PNG",
        f"{base_name.lower()}.jpeg"
    ]
    
    found = None
    for candidate in candidate_files:
        if os.path.exists(candidate):
            found = candidate
            break
            
    if found:
        try:
            # PIL 모듈로 이미지를 직접 열어 모바일 인지 안정성 확보
            img = Image.open(found)
            st.image(img, use_container_width=True)
        except Exception:
            st.image(found, use_container_width=True)
    else:
        # 이미지가 진짜로 없을 경우에만 대안 SVG 그래픽 출력
        if "three_pigs" in filename or "q1" in filename:
            render_three_pigs_crossroads_image()
        else:
            st.info(fallback_msg)

# ==========================================
# 5. 질문 트리 및 페르소나 정의
# ==========================================
QUESTION_TREE_PIGS = {
    "Q1": {
        "text": "📜 [EP1. 숲의 입구] 위험한 투자의 숲에 늑대(폭락)가 온다는 소문이 돕니다! 당신은 어떤 집을 지으시겠습니까?",
        "options": [
            {"label": "🌾 첫째 돼지: 스피드가 생명! 짚으로 뚝딱 지어 남들보다 먼저 대박 보물을 찾으러 갈래.", "next": "Q2_C"},
            {"label": "🪵 둘째 돼지: 적당히 튼튼하게! 나무로 근사하고 균형 있게 지어 정원을 가꿀래.", "next": "Q2_B"},
            {"label": "🧱 셋째 돼지: 안전이 최고! 어떤 늑대가 바람을 불어도 안 무너지는 벽돌 요새를 지을래.", "next": "Q2_A"}
        ]
    },
    "Q2_A": {
        "text": "🐺 [EP2. 늑대의 등장] 늑대가 찾아와 외벽을 부수며 경고합니다! '당장 나오지 않으면 자산을 -15% 떨어뜨리겠다!' 당신은?",
        "options": [
            {"label": "🏃‍♂️ 무서워! 주식 숲은 위험해... 안전한 자산 보존 구역으로 피신한다.", "next": "Q3_A1"},
            {"label": "🧱 벽돌집은 안 무너져! 문을 잠그고 꼬박꼬박 나오는 월세(배당금)를 챙기며 버틴다.", "next": "Q3_A2"}
        ]
    },
    "Q2_B": {
        "text": "🪴 [EP2. 정원 가꾸기] 나무집 앞 정원에 세월이 흘러도 번성할 나무를 심으려 합니다. 어떤 나무를 심어볼까요?",
        "options": [
            {"label": "☕ 한번 잘 심어두면 한 달에 한두 번만 느긋하게 관리해서 혼자 단단하게 자라는 거목 심기", "next": "Q3_B1"},
            {"label": "✂️ 지금 가장 핫한 신품종 트렌드 열매나무를 심어, 매일 정원에 들리면서 관리하기", "next": "Q3_B2"}
        ]
    },
    "Q2_C": {
        "text": "💎 [EP2. 보물상자] 짚집 마당에서 신비하게 빛나는 보물상자를 발견했습니다! 당신이 챙기고 싶은 보물은?",
        "options": [
            {"label": "🚀 숲의 유행을 타서 빠르게 값을 올리는 시세차익 보석", "next": "Q3_C1"},
            {"label": "⚡ 위험하지만 터지면 2배, 3배가 되는 잭팟 주문서", "next": "Q3_C2"}
        ]
    },
    "Q3_A1": {
        "text": "🛡️ [EP3. 안심 나만의 무기] 늑대의 바람을 완벽히 막아낼 방어 무기 2가지 중 어떤 것을 선택하시겠습니까?",
        "options": [
            {"label": "🛡️ 초단기 파킹통장(CD/KOFR): 원금 손실 위험 0%! 하루만 맡겨도 매일 이자가 복리로 쌓이는 파킹형 자산", "next": "Q4_1A"},
            {"label": "🏛️ 우량 국공채 및 채권: 만기까지 고정 이자를 확실하게 챙기고 금리 인하 시 시세차익까지 노리는 채권 자산", "next": "Q4_1B"}
        ]
    },
    "Q3_A2": {
        "text": "🎁 [EP2. 월세 상자] 월세 보너스로 두가지 상자를 샀다! 어떤 상자를 열어볼까?",
        "options": [
            {"label": "💵 지금 당장 통장에 수수료 없이 두둑하게 들어오는 고배당 상자", "next": "Q4_2A"},
            {"label": "🌱 지금은 적지만 해가 지날수록 금액이 점점 커지는 배당성장 상자", "next": "Q4_2B"}
        ]
    },
    "Q3_B1": {
        "text": "🌳 [EP3. 거목의 조건] 정원에 오래 키우고 싶은 거목은 어떤 특징을 가져야 안심되나요?",
        "options": [
            {"label": "🏢 남들의 관심이 적더라도 실적과 자산 대비 억울하게 저평가된 가치 거목", "next": "Q4_3A"},
            {"label": "👑 이미 세상의 중심이 되어 절대로 쓰러질 리 없는 1등 대표 거목", "next": "Q4_3B"}
        ]
    },
    "Q3_B2": {
        "text": "🔥 [EP3. 트렌드 열매] 꾸준한 관리를 통해 열리는 나만의 탐스럽고 비싼 열매는 무엇인가요?",
        "options": [
            {"label": "💻 세상을 지배하는 1위 빅테크 및 반도체 열매", "next": "Q4_4A"},
            {"label": "🔋 미래를 바꿀 친환경 2차전지 및 신기술 열매", "next": "Q4_4B"}
        ]
    },
    "Q3_C1": {
        "text": "🌪️ [EP3. 파도 타기] 하루에도 집이 ±15%씩 요동치는 폭풍이 칠 때, 당신의 태도는?",
        "options": [
            {"label": "🏄‍♂️ 오히려 좋아! 거센 파도를 타며 가파른 시세 차익을 노린다.", "next": "Q4_5A"},
            {"label": "🤖 세상을 바꿀 주도 산업(AI, 로봇)이라면 끝까지 올인한다.", "next": "Q4_5B"}
        ]
    },
    "Q3_C2": {
        "text": "⚡ [EP3. 마법 주문] 짚집에서 대박을 안겨줄 마법의 주문을 외워보세요!",
        "options": [
            {"label": "📈 주가가 오를 때 2배, 3배로 폭발하는 레버리지 주문", "next": "Q4_6A"},
            {"label": "🧪 급등락을 반복하는 초기 혁신 벤처/바이오 주문", "next": "Q4_6B"}
        ]
    },
    "Q4_1A": {
        "text": "🎯 [EP4. 최종 확정] '원금 손실 걱정 없이 하루만 맡겨도 매일 이자가 차곡차곡 쌓이는 안전 파킹형 투자'를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 원금을 100% 안전하게 지키면서 매일 이자를 받는 안심 파킹 투자를 확정하겠습니다.", "next": "END", "persona": "P1_A_PARKING_ETF", "tag": "PARKING_ETF"}
        ]
    },
    "Q4_1B": {
        "text": "🎯 [EP4. 최종 확정] '정부나 초우량 은행이 보증해 약속된 이자를 꼬박꼬박 챙겨주는 안심 채권 투자'를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 만기까지 이자가 확실히 보장되는 안심 우량 채권 투자를 확정하겠습니다.", "next": "END", "persona": "P1_B_BOND_INVESTMENT", "tag": "BOND_INVESTMENT"}
        ]
    },
    "Q4_2A": {
        "text": "🎯 [EP4. 최종 확정] 주가 변동성보다 당장 통장에 두둑한 현금이 정기적으로 들어오는 '고배당 현금창출' 전략을 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 당장 높은 시가배당률을 챙기는 고배당 인컴 포트폴리오를 확정하겠습니다.", "next": "END", "persona": "P3_A_HIGH_DIVIDEND", "tag": "HIGH_DIVIDEND"}
        ]
    },
    "Q4_2B": {
        "text": "🎯 [EP4. 최종 확정] 지금은 배당이 적더라도 기업 성장에 맞춰 매년 배당금이 커지는 '배당 복리(스노우볼)' 전략을 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 매년 배당금이 증액되는 배당성장 복리 포트폴리오를 확정하겠습니다.", "next": "END", "persona": "P3_B_DIVIDEND_GROWTH", "tag": "DIVIDEND_GROWTH"}
        ]
    },
    "Q4_3A": {
        "text": "🎯 [EP4. 최종 확정] 주가 하방 안전성이 탄탄하고 자산/실적 대비 억울하게 저평가된 밸류업 가치주 중심의 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 탄탄한 하방 안전성과 밸류업 정책 수혜를 노리는 가치주 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P5_VALUE_SAFETY", "tag": "VALUE_STOCK"}
        ]
    },
    "Q4_3B": {
        "text": "🎯 [EP4. 최종 확정] 대한민국을 대표하며 업계 1위 독점적 경쟁력을 가진 대표 대장주 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 쓰러지지 않는 대한민국 1등 대표 대장주 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P2_STABLE_GROWTH", "tag": "LARGE_CAP"}
        ]
    },
    "Q4_4A": {
        "text": "🎯 [EP4. 최종 확정] 글로벌 AI 생태계 및 반도체 산업을 주도하는 대표 빅테크 핵심주 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 높은 ROE와 반도체 주도권을 쥔 테크 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P4_A_SEMICON_TECH", "tag": "SEMICON_TECH"}
        ]
    },
    "Q4_4B": {
        "text": "🎯 [EP4. 최종 확정] 친환경 2차전지, ESS 및 로봇 등 차세대 신기술 산업의 강력한 모멘텀주 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 미래 패러다임을 바꿀 친환경·신기술 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P4_B_NEXT_GEN_TECH", "tag": "NEXT_GEN_TECH"}
        ]
    },
    "Q4_5A": {
        "text": "🎯 [EP4. 최종 확정] 수급 상승 폭풍을 타고 빠르게 시세차익을 확정짓는 스윙/모멘텀 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 빠른 주가 상승 탄력을 가진 수급 모멘텀 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P4_C_MOMENTUM_SWING", "tag": "MOMENTUM_SWING"}
        ]
    },
    "Q4_5B": {
        "text": "🎯 [EP4. 최종 확정] 단기 폭풍을 견디며 시대를 바꿀 AI·로봇 등 메가트렌드 주도주 장기 올인을 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 미래 주도권을 거머쥘 메가트렌드 대장주 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P4_D_MEGA_TREND", "tag": "MEGA_TREND"}
        ]
    },
    "Q4_6A": {
        "text": "🎯 [EP4. 최종 확정] 시장 지수 변동을 2배 추종하여 단기 압도적 고수익을 노리는 지수 레버리지/파생 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 변동성 위험을 무릅쓰고 2배 수익을 노리는 트레이딩 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P6_A_INDEX_LEVERAGE", "tag": "INDEX_LEVERAGE"}
        ]
    },
    "Q4_6B": {
        "text": "🎯 [EP4. 최종 확정] 신약 임상 모멘텀이나 초기 혁신 기술로 잭팟 수익을 노리는 벤처/바이오 고변동 투자를 선택하시겠습니까?",
        "options": [
            {"label": "✅ 네! 초고위험을 감수하고 대박을 지향하는 바이오·벤처 포트폴리오를 선택하겠습니다.", "next": "END", "persona": "P6_B_VENTURE_BIO", "tag": "VENTURE_BIO"}
        ]
    }
}

PERSONA_CARDS = {
    "P1_A_PARKING_ETF": {
        "title": "🛡️ ①-A 초단기 파킹·원금보존형 (안심 파수꾼)",
        "description": "원금 손실 위험을 0%에 가깝게 회피하며, 매일 복리 이자를 챙기고 필요할 때 언제든 현금화할 유동성을 최우선하는 투자자입니다.",
        "alloc_advice": "파킹형 CD금리 및 KOFR ETF에 80% 이상 배치하고, 나머지 비중을 수시 입출금 비상금 계좌로 관리하세요.",
        "portfolio_mix": [
            {"name": "CD금리/KOFR 파킹형 ETF", "ratio": 80, "desc": "매일 이자 복리 누적, 원금손실 위험 0%"},
            {"name": "초단기 MMF 및 예치금", "ratio": 15, "desc": "비상금 및 유동성 확보 계좌"},
            {"name": "수시 입출금 파킹통장", "ratio": 5, "desc": "즉시 출금 가능 현금 계좌"}
        ]
    },
    "P1_B_BOND_INVESTMENT": {
        "title": "🏛️ ①-B 우량 채권·고정수익형 (채권 밸런서)",
        "description": "원금 안전성을 기본으로 장기 고정 이자 수수와 금리 인하 시 채권 가격 상승에 따른 프리미엄 차익을 함께 추구하는 투자자입니다.",
        "alloc_advice": "대한민국 30년 국채 및 초우량 은행채 ETF에 80% 비중을 분산 편입하여 매월/매분기 안정적인 이자 채권을 굴리세요.",
        "portfolio_mix": [
            {"name": "장기 국고채 ETF", "ratio": 50, "desc": "정부 보증 안정성 + 금리 인하 시 시세차익"},
            {"name": "초우량 만기매칭 은행채 ETF", "ratio": 30, "desc": "AA+ 이상 등급 만기 확정 이자 수익"},
            {"name": "단기 채권 및 현금", "ratio": 20, "desc": "이체 및 현금성 예치 계좌"}
        ]
    },
    "P3_A_HIGH_DIVIDEND": {
        "title": "💵 ③-A 고배당·현금창출형 (월세 수급 파수꾼)",
        "description": "주가 상승에 따른 차익보다는 매년/매분기 꼬박꼬박 들어오는 고정 배당금 현금흐름을 최우선으로 여기는 투자자입니다.",
        "alloc_advice": "시가배당률 연 6~8%대의 고배당주 및 인프라 자산에 70% 이상 집중 배치하여 즉각적인 현금 유동성을 확보하세요.",
        "portfolio_mix": [
            {"name": "고배당 금융/인프라 개별주", "ratio": 70, "desc": "시가배당률이 높고 분기 배당을 지급하는 초우량주"},
            {"name": "월배당 커버드콜 ETF", "ratio": 20, "desc": "매달 고정적 월세 수입을 챙기는 인컴형 ETF"},
            {"name": "현금 자산", "ratio": 10, "desc": "배당금 예치 및 유동성 확보 계좌"}
        ]
    },
    "P3_B_DIVIDEND_GROWTH": {
        "title": "🌱 ③-B 배당성장·복리형 (스노우볼 캐처)",
        "description": "당장의 배당수익률은 다소 낮더라도 이익 성장에 따라 매년 배당금을 늘려주는 기업에 투자해 복리 효과를 노리는 투자자입니다.",
        "alloc_advice": "배당성장주 3종목에 70% 비중을 배분하고, 지급받은 배당금을 즉시 재투자하여 자산 스노우볼을 굴리세요.",
        "portfolio_mix": [
            {"name": "배당성장 대표 우량주", "ratio": 70, "desc": "매년 영업이익 증액 및 배당금 상향 기업"},
            {"name": "배당성장 ETF", "ratio": 20, "desc": "배당 증액 기업들에 분산 투자하는 성장형 ETF"},
            {"name": "배당 재투자 현금 계좌", "ratio": 10, "desc": "배당금 복리 재투자 전용 예약 계좌"}
        ]
    },
    "P2_STABLE_GROWTH": {
        "title": "🏢 ② 안정성장·대형주형 (스마트 항해사)",
        "description": "파산 위험이 없는 시가총액 1등 대장주 위주로 포트폴리오를 구성하여, 시장 평균 이상의 안정한 성장을 추구하는 투자자입니다.",
        "alloc_advice": "추천 대형주 3종목에 60%를 배분하고, 20%는 고배당주, 20%는 현금성 파킹 자산으로 리스크를 방어하세요.",
        "portfolio_mix": [
            {"name": "시가총액 상위 1등 대장주", "ratio": 60, "desc": "글로벌 경쟁력 보유 핵심 대표주"},
            {"name": "배당성장 금융/인프라주", "ratio": 20, "desc": "안정적인 캐시카우 현금흐름"},
            {"name": "파킹형 ETF 및 현금", "ratio": 20, "desc": "시장 조정 시 추가 매수용 실탄"}
        ]
    },
    "P4_A_SEMICON_TECH": {
        "title": "💻 ④-A AI·반도체 주도주형 (하이테크 항해사)",
        "description": "글로벌 AI 생태계의 중심인 반도체 및 핵심 빅테크 기업에 집중하여 강한 성장 모멘텀을 추구하는 투자자입니다.",
        "alloc_advice": "HBM 및 반도체 장비/부품 1위주에 60% 비중을 투자하고, 눌림목마다 분할 매집하세요.",
        "portfolio_mix": [
            {"name": "AI/메모리 반도체 주도주", "ratio": 60, "desc": "글로벌 점유율 1위 반도체 독점 우량주"},
            {"name": "반도체 소부장 테마 ETF", "ratio": 20, "desc": "반도체 밸류체인 전체 분산 투자"},
            {"name": "파킹형 현금 자산", "ratio": 20, "desc": "주가 조정 시 추매 실탄"}
        ]
    },
    "P4_B_NEXT_GEN_TECH": {
        "title": "🔋 ④-B 친환경·신기술 혁신형 (미래 개척자)",
        "description": "2차전지, ESS, 로봇 등 미래 패러다임을 대전환할 핵심 신기술 기업의 폭발적인 성장을 지향하는 투자자입니다.",
        "alloc_advice": "차세대 에너지 및 신기술 1위 기업에 60% 비중을 배분하고 손절선(-7~10%)을 설정해 위험을 관리하세요.",
        "portfolio_mix": [
            {"name": "2차전지 & 로봇 핵심주", "ratio": 60, "desc": "미래 패러다임을 바꿀 1위 신기술 주도 기업"},
            {"name": "친환경/로봇 테마 ETF", "ratio": 20, "desc": "신기술 산업 밸류체인 분산 투자"},
            {"name": "파킹형 현금 자산", "ratio": 20, "desc": "변동성 대비 리스크 관리 버퍼"}
        ]
    },
    "P4_C_MOMENTUM_SWING": {
        "title": "🏄‍♂️ ④-C 단기 모멘텀·시세차익형 (트렌드 서퍼)",
        "description": "가파르게 상승하는 수급 폭발주나 실적 모멘텀주를 타고 단기간에 뛰어난 시세차익을 확정하는 투자자입니다.",
        "alloc_advice": "상승 동력이 강한 수급 모멘텀주에 60% 비중을 실되, 익절 및 손절선(-5~7%) 기준을 철저히 지키며 호흡을 빠르게 가져가세요.",
        "portfolio_mix": [
            {"name": "수급/실적 모멘텀 스윙주", "ratio": 60, "desc": "강한 주가 상승 탄력을 지닌 시세차익주"},
            {"name": "모멘텀/주도주 ETF", "ratio": 20, "desc": "트렌드 상향 정배열 섹터 ETF"},
            {"name": "기회 포착 현금", "ratio": 20, "desc": "새로운 파도를 타기 위한 현금 실탄"}
        ]
    },
    "P4_D_MEGA_TREND": {
        "title": "🤖 ④-D 메가트렌드·산업집중형 (게임체인저)",
        "description": "단기 주가 파도보다는 AI, 로봇 등 시대를 바꿀 수밖에 없는 메가트렌드 산업 1등주에 올인하여 장기적 거대 수익을 노리는 투자자입니다.",
        "alloc_advice": "미래 패러다임을 지배할 거대 주도주에 70%를 편입하고, 시장 흔들림 시 저가 분할 매수로 수량을 모으세요.",
        "portfolio_mix": [
            {"name": "AI/로봇 메가트렌드 대장주", "ratio": 70, "desc": "시대를 관통하는 독점적 게임체인저"},
            {"name": "빅테크/AI 테마 ETF", "ratio": 20, "desc": "메가트렌드 생태계 전체 분산 ETF"},
            {"name": "적립식 예약 현금 계좌", "ratio": 10, "desc": "조정 시 추가 매수를 위한 실탄 계좌"}
        ]
    },
    "P5_VALUE_SAFETY": {
        "title": "🔍 ⑤ 가치·안전지대형 (딥밸류 탐험가)",
        "description": "회사 보유 자산과 실적 대비 현저히 저평가된 밸류업 주식을 찾아 하방 안전성을 챙기는 투자자입니다.",
        "alloc_advice": "저PBR/저PER 가치주에 70% 비중을 투자하고, 목표가 도달 시까지 장기 보유하세요.",
        "portfolio_mix": [
            {"name": "저PBR/저PER 밸류업 가치주", "ratio": 70, "desc": "자산 가치 대비 극심한 저평가 우량주"},
            {"name": "중장기 국채 / 단기채", "ratio": 20, "desc": "안정적 이자 수입과 하방 방어"},
            {"name": "기회 포착 현금", "ratio": 10, "desc": "저평가 종목 추가 발굴용 예비비"}
        ]
    },
    "P6_A_INDEX_LEVERAGE": {
        "title": "⚡ ⑥-A 지수 레버리지·트레이딩형 (파동 추종 파이터)",
        "description": "지수의 단기 변동성을 2배 추종하여 빠른 시세차익을 노리는 공격적 스윙/트레이딩 투자자입니다.",
        "alloc_advice": "횡보장 시 자산이 까먹히는 음의 복리 위험이 크므로 장기 투자를 금지하고, 20%의 현금 리스크 버퍼를 반드시 보유하세요.",
        "portfolio_mix": [
            {"name": "지수 2X 레버리지/인버스 ETF", "ratio": 50, "desc": "단기 방향성 추종 트레이딩 자산"},
            {"name": "시가총액 상위 대형주", "ratio": 30, "desc": "기초 체력을 잡아주는 하방 방어용 주식"},
            {"name": "손절매/리스크 관리 현금", "ratio": 20, "desc": "변동성 폭발 시 대응을 위한 안심 버퍼"}
        ]
    },
    "P6_B_VENTURE_BIO": {
        "title": "🧪 ⑥-B 초기 벤처·바이오 대박형 (잭팟 탐험가)",
        "description": "임상 성공 및 파괴적 신기술에 따른 잭팟 수익을 노리고, 높은 급등락 위험을 기꺼이 감수하는 과감한 모험 투자자입니다.",
        "alloc_advice": "단일 종목 부도 및 급락 위험을 고려해 포트폴리오의 15% 이내 소액으로 분산 투자하고 철저한 손절선을 설정하세요.",
        "portfolio_mix": [
            {"name": "초기 바이오 & AI 벤처 혁신주", "ratio": 50, "desc": "임상 및 신기술 모멘텀 보유 고변동주"},
            {"name": "바이오/헬스케어 테마 ETF", "ratio": 30, "desc": "단일 종목 위험을 낮춰주는 섹터 분산 ETF"},
            {"name": "손절매/비상용 현금", "ratio": 20, "desc": "급락 및 리밸런싱 대응용 예비 현금"}
        ]
    }
}

# ==========================================
# 6. 추천 알고리즘 및 포트폴리오 재계산 로직
# ==========================================
def recalculate_portfolio_mix(base_mix, safety_boost, dividend_boost, speed_boost):
    mix = [dict(item) for item in base_mix]
    
    if safety_boost == "유지" and dividend_boost == "유지" and speed_boost == "유지":
        return mix

    for item in mix:
        name = item["name"]
        
        if safety_boost == "안전 자산 비중 확대 (+30%)":
            if any(k in name for k in ["현금", "채권", "파킹", "MMF", "버퍼"]):
                item["ratio"] += 30
                item["desc"] += " (🛡️ 안전 비중 확대)"
            else:
                item["ratio"] = max(5, item["ratio"] - 15)
                
        if dividend_boost == "배당/월세수입 집중 (+20%)":
            if any(k in name for k in ["배당", "인컴", "월세", "커버드콜"]):
                item["ratio"] += 20
                item["desc"] += " (💵 배당 집중)"
            elif not any(k in name for k in ["현금", "채권", "파킹"]):
                item["ratio"] = max(5, item["ratio"] - 10)
                
        if speed_boost == "단기 시세차익 스윙":
            if any(k in name for k in ["현금", "실탄"]):
                item["ratio"] += 10
                item["desc"] += " (⚡ 빠른 스윙 현금)"
        elif speed_boost == "장기 적립식 모으기":
            if any(k in name for k in ["대표", "1등", "주도", "우량", "성장"]):
                item["ratio"] += 10
                item["desc"] += " (☕ 장기 적립 중심)"

    total_ratio = sum(item["ratio"] for item in mix)
    if total_ratio > 0:
        for item in mix:
            item["ratio"] = round((item["ratio"] / total_ratio) * 100)
            
        diff = 100 - sum(item["ratio"] for item in mix)
        if diff != 0:
            mix[0]["ratio"] += diff
            
    return mix


def recommend_products_by_persona(tag):
    if tag in ["PARKING_ETF", "BOND_INVESTMENT"]:
        reason_msg = "🛡️ 원금을 철저히 보존하면서 매일 복리 이자수익을 주는 파킹형 자산입니다." if tag == "PARKING_ETF" else "🏛️ 국가 보증 및 초우량 등급으로 안정적 만기 이자수입을 보장하는 우량 채권형 자산입니다."
        return {
            "category": "BOND",
            "items": TARGET_STOCKS_BY_PERSONA[tag],
            "reason": reason_msg
        }

    reason_messages = {
        "HIGH_DIVIDEND": "💵 [고배당형] 시가배당률이 매력적이며 안정적인 현금 인컴을 제공하는 고배당주 추천군입니다.",
        "DIVIDEND_GROWTH": "🌱 [배당성장형] 실적 성장과 배당금 증액으로 복리 스노우볼에 최적화된 우량주입니다.",
        "LARGE_CAP": "🏆 [안정성장형] 파산 위험이 없는 대한민국 시가총액 1등 대장주 추천군입니다.",
        "SEMICON_TECH": "💻 [AI·반도체형] 글로벌 AI 생태계 중심에 서 있는 초우량 반도체 주도주 추천군입니다.",
        "NEXT_GEN_TECH": "🔋 [2차전지·신기술형] 친환경 에너지 및 미래 기술 패러다임을 이끄는 모멘텀 추천군입니다.",
        "MOMENTUM_SWING": "🏄‍♂️ [단기시세차익형] 강한 주가 탄력과 수급 모멘텀을 기민하게 추종하는 추천군입니다.",
        "MEGA_TREND": "🤖 [메가트렌드올인형] AI·로봇 등 세상을 바꿀 미래 1등 주도주 집중 추천군입니다.",
        "INDEX_LEVERAGE": "⚡ [지수레버리지형] 지수 일간 변동률의 2배 수익을 노리는 고변동 파생 ETF 추천군입니다.",
        "VENTURE_BIO": "🧪 [벤처·바이오형] 임상 승인 및 차세대 기술 모멘텀으로 잭팟 수익을 지향하는 추천군입니다.",
        "VALUE_STOCK": "🔍 [가치안전형] PBR이 억울하게 저평가되어 하방 방어력이 뛰어난 밸류업 가치주입니다."
    }

    candidate_pool = TARGET_STOCKS_BY_PERSONA.get(tag, TARGET_STOCKS_BY_PERSONA["LARGE_CAP"])
    selected_base_items = random.sample(candidate_pool, min(3, len(candidate_pool)))

    realtime_items = []
    for item in selected_base_items:
        ticker = item.get("ticker", "")
        name = item.get("name", "")
        desc = item.get("desc", "")
        
        is_etf = ("ETF" in desc or "레버리지" in name or "인버스" in name)
        rt_data = fetch_realtime_metrics(ticker, default_data=item, is_etf=is_etf)
        
        merged_item = {
            "name": name,
            "ticker": ticker,
            "desc": desc,
            "price": rt_data["price"],
            "per": rt_data["per"],
            "pbr": rt_data["pbr"],
            "roe": rt_data["roe"],
            "eps": rt_data["eps"]
        }
        realtime_items.append(merged_item)

    return {
        "category": "STOCK",
        "items": realtime_items,
        "reason": reason_messages.get(tag, "📊 성향 맞춤 실시간 재무 검증 주식입니다.")
    }

# ==========================================
# 7. 메인 실행부
# ==========================================
if "current_node" not in st.session_state:
    st.session_state.current_node = "Q1"
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = None
if "final_tag" not in st.session_state:
    st.session_state.final_tag = None
if "history" not in st.session_state:
    st.session_state.history = []

if "adjust_mode" not in st.session_state:
    st.session_state.adjust_mode = False
if "safety_boost" not in st.session_state:
    st.session_state.safety_boost = "유지"
if "dividend_boost" not in st.session_state:
    st.session_state.dividend_boost = "유지"
if "speed_boost" not in st.session_state:
    st.session_state.speed_boost = "유지"

st.markdown("<div class='main-title'>🐷 아기돼지 삼형제의 뚝딱! 주식&채권 집짓기 🏡</div>", unsafe_allow_html=True)

if st.session_state.current_node != "END":
    node = st.session_state.current_node
    
    if st.session_state.current_node != "Q1":
        if st.button("⬅️ 이전 질문으로 돌아가기"):
            if st.session_state.history:
                st.session_state.current_node = st.session_state.history.pop()
                st.session_state.selected_persona = None
                st.session_state.final_tag = None
                st.rerun()

    # 질문별 이미지 렌더링 (Q1 세션 로딩 오류 방지 처리)
    if node == "Q1":
        render_image_by_filename("three_pigs.png", "📌 삼형제 첫 화면 이미지가 표시됩니다.")
    elif node == "Q2_A": 
        render_image_by_filename("wolf_attack.png", "📌 늑대의 등장 이미지가 표시됩니다.")
    elif node == "Q2_B": 
        render_image_by_filename("q2_b.png", "📌 정원 가꾸기 이미지가 표시됩니다.")
    elif node == "Q2_C": 
        render_image_by_filename("q2_c.png", "📌 보물상자 이미지가 표시됩니다.")
    elif node == "Q3_A1": 
        render_image_by_filename("q3_a1.png", "📌 동굴 속 돼지 이미지가 표시됩니다.")
    elif node == "Q3_A2": 
        render_image_by_filename("q3_a2.png", "📌 월세 상자 이미지가 표시됩니다.")
    elif node == "Q3_B1": 
        render_image_by_filename("q3_b1.png", "📌 거목의 조건 이미지가 표시됩니다.")
    elif node == "Q3_B2": 
        render_image_by_filename("q3_b2.png", "📌 트렌드 열매 이미지가 표시됩니다.")
    elif node == "Q3_C1": 
        render_image_by_filename("q3_c1.png", "📌 파도 타기 이미지가 표시됩니다.")
    elif node == "Q3_C2": 
        render_image_by_filename("q3_c2.png", "📌 마법 주문 이미지가 표시됩니다.")

    node_data = QUESTION_TREE_PIGS[st.session_state.current_node]
    
    st.markdown(
        f"<div class='question-box'>"
        f"<p class='question-text'>{node_data['text']}</p>"
        f"</div>", 
        unsafe_allow_html=True
    )
    
    st.write("👇 **마음에 드는 탐험 카드(선택지)를 클릭하세요:**")
    
    for option in node_data["options"]:
        if st.button(option["label"], key=option["label"], use_container_width=True):
            st.session_state.history.append(st.session_state.current_node)
            if "persona" in option:
                st.session_state.selected_persona = option["persona"]
            if "tag" in option:
                st.session_state.final_tag = option["tag"]
            st.session_state.current_node = option["next"]
            st.rerun()

else:
    # 최종 결과 화면
    if st.button("⬅️ 이전 질문으로 돌아가기"):
        if st.session_state.history:
            st.session_state.current_node = st.session_state.history.pop()
            st.session_state.selected_persona = None
            st.session_state.final_tag = None
            st.rerun()

    persona_key = st.session_state.selected_persona if st.session_state.selected_persona else "P2_STABLE_GROWTH"
    persona_info = PERSONA_CARDS[persona_key]
    
    persona_title_color = "#155724" if st.session_state.final_tag not in ["PARKING_ETF", "BOND_INVESTMENT"] else "#004085"
    persona_bg_color = "#d4edda" if st.session_state.final_tag not in ["PARKING_ETF", "BOND_INVESTMENT"] else "#cce5ff"

    st.markdown(
        f"<div class='persona-card'>"
        f"<h2 style='margin-top:0;'>{persona_info['title']}</h2>"
        f"<p style='font-size: 15px;'>{persona_info['description']}</p>"
        f"<div style='margin-top: 10px; font-weight: 500; color: {persona_title_color}; background-color: {persona_bg_color}; padding: 10px 14px; border-radius: 8px;'>"
        f"💡 가이드: {persona_info['alloc_advice']}"
        f"</div>"
        f"</div>", 
        unsafe_allow_html=True
    )

    adjusted_mix = recalculate_portfolio_mix(
        persona_info['portfolio_mix'],
        st.session_state.safety_boost,
        st.session_state.dividend_boost,
        st.session_state.speed_boost
    )

    mix_items_html = "".join([
        f"<li><b>{item['name']} ({item['ratio']}%):</b> {item['desc']}</li>"
        for item in adjusted_mix
    ])
    
    is_adjusted = (st.session_state.safety_boost != "유지" or st.session_state.dividend_boost != "유지" or st.session_state.speed_boost != "유지")
    sub_title_extra = " (🛠️ 세부 성향 맞춤 조율 완료)" if is_adjusted else ""
    
    st.markdown(
        f"<div class='portfolio-card'>"
        f"<h4 style='margin-top:0; color:#5f3dc4; font-size:16px;'>🛡️ 맞춤형 포트폴리오 구성 가이드{sub_title_extra}</h4>"
        f"<p style='font-size:14px; color:#495057;'>투자 위험을 줄이고 수익률을 극대화하기 위한 자산 배분 비중입니다:</p>"
        f"<ul style='font-size:14px; line-height:1.7; color:#2b8a3e; margin-bottom:0;'>"
        f"{mix_items_html}"
        f"</ul>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    result_data = recommend_products_by_persona(st.session_state.final_tag)
    st.info(f"{result_data['reason']} (현재 무위험 국채 10년물 금리: 연 {MARKET_GOV_BOND_RATE}%)")
    
    if result_data["category"] == "BOND":
        st.subheader("🛡️ 당신을 위한 맞춤 채권/파킹형 ETF")
        for item in result_data["items"]:
            bond_advice = generate_bond_advice(item['name'], item['type'])
            st.markdown(
                f"<div class='product-card'>"
                f"<h4 style='margin-top:0;'>{item['name']} ({item['ticker']})</h4>"
                f"<p style='font-size:14px;'><b>유형:</b> {item['type']}</p>"
                f"<p style='color: #666; font-size:14px;'>{item['desc']}</p>"
                f"<div class='advice-box'>"
                f"{bond_advice}"
                f"</div>"
                f"</div>", 
                unsafe_allow_html=True
            )
            
    elif result_data["category"] == "STOCK" and result_data["items"]:
        st.subheader("🏆 종목별 최신 재무 반영 추천 상품")
        
        for idx, item in enumerate(result_data["items"], start=1):
            per = item.get("per", 0.0)
            pbr = item.get("pbr", 0.0)
            roe = item.get("roe", 0.0)
            eps = item.get("eps", 0)
            name = item.get("name", "")
            desc = item.get("desc", "")
            ticker = item.get("ticker", "")
            price = item.get("price", 0)
            
            is_etf = (per == 0.0 and pbr == 0.0) or ("ETF" in desc or "레버리지" in name or "인버스" in name)
            
            dynamic_advice = generate_investment_advice(
                stock_tag=st.session_state.final_tag,
                name=name,
                per=per,
                pbr=pbr,
                roe=roe,
                market_rate=MARKET_GOV_BOND_RATE
            )
            
            if st.session_state.speed_boost == "단기 시세차익 스윙":
                dynamic_advice += "<br>⚡ <b>[조율 팁]</b> 단기 호흡 접근이 설정되었습니다. +5% 이상 수익 시 목표가를 조절하세요."
            elif st.session_state.speed_boost == "장기 적립식 모으기":
                dynamic_advice += "<br>☕ <b>[조율 팁]</b> 장기 적립 접근이 설정되었습니다. 단기 시세보다 수량을 모으는 데 집중하세요."

            if is_etf:
                html_etf = (
                    f"<div class='product-card'>"
                    f"<div style='display: flex; justify-content: space-between; align-items: center;'>"
                    f"<h3 style='margin:0; font-size:18px;'>{idx}. {name} <span style='font-size:15px; color:#666;'>({ticker})</span></h3>"
                    f"<span style='background:#fff0f6; color:#d6336c; font-weight:bold; padding:4px 8px; border-radius:6px; font-size:14px;'>현재가 {price:,}원</span>"
                    f"</div>"
                    f"<div class='etf-metric-box'>"
                    f"📊 <b>상품 분류 지표 (ETF):</b><br>"
                    f"• <b>상품 유형:</b> 지수 파생 / 파동 추종 ETF<br>"
                    f"• <b>기초 자산:</b> KOSPI 200 등 연동 지수"
                    f"</div>"
                    f"<div class='biz-desc'>"
                    f"🏢 <b>상품 특징 설명:</b> {desc}"
                    f"</div>"
                    f"<div class='etf-advice-box'>"
                    f"{dynamic_advice}"
                    f"</div>"
                    f"</div>"
                )
                st.markdown(html_etf, unsafe_allow_html=True)

            else:
                html_stock = (
                    f"<div class='product-card'>"
                    f"<div style='display: flex; justify-content: space-between; align-items: center;'>"
                    f"<h3 style='margin:0; font-size:18px;'>{idx}. {name} <span style='font-size:15px; color:#666;'>({ticker})</span></h3>"
                    f"<span style='background:#e7f5ff; color:#1c7ed6; font-weight:bold; padding:4px 8px; border-radius:6px; font-size:14px;'>현재가 {price:,}원</span>"
                    f"</div>"
                    f"<div class='metric-box'>"
                    f"📊 <b>실시간 반영 재무지표 (Valuation):</b><br>"
                    f"• <b>PER (주가수익비율):</b> {per}배 &nbsp;|&nbsp; "
                    f"• <b>PBR (주가순자산비율):</b> {pbr}배<br>"
                    f"• <b>ROE (자기자본이익률):</b> {roe}% &nbsp;|&nbsp; "
                    f"• <b>EPS (주당순이익):</b> {eps:,}원"
                    f"</div>"
                    f"<div class='biz-desc'>"
                    f"🏢 <b>기업 주요 사업:</b> {desc}"
                    f"</div>"
                    f"<div class='advice-box'>"
                    f"{dynamic_advice}"
                    f"</div>"
                    f"</div>"
                )
                st.markdown(html_stock, unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # 8. 미세 조정 질문 영역
    # ==========================================
    if not st.session_state.adjust_mode:
        if st.button("🛠️ 포트폴리오 조금 더 조정하기", use_container_width=True):
            st.session_state.adjust_mode = True
            st.rerun()
    else:
        st.markdown("<div class='adjust-box'>", unsafe_allow_html=True)
        st.markdown("### ⚙️ 세부 포트폴리오 미세 조율")
        st.write("결과가 맘에 쏙 들지 않으신가요? 아래 항목을 선택해 내 성향에 딱 맞게 포트폴리오를 바꿔보세요.")
        
        with st.form("fine_tune_form"):
            safety_choice = st.radio(
                "1. 원금 안전성을 더 높이고 싶으신가요?",
                ["유지", "안전 자산 비중 확대 (+30%)"],
                index=0 if st.session_state.safety_boost == "유지" else 1
            )
            
            dividend_choice = st.radio(
                "2. 정기적인 배당 수입을 더 원하시나요?",
                ["유지", "배당/월세수입 집중 (+20%)"],
                index=0 if st.session_state.dividend_boost == "유지" else 1
            )
            
            speed_choice = st.radio(
                "3. 선호하는 투자 호흡을 고르세요:",
                ["유지", "단기 시세차익 스윙", "장기 적립식 모으기"],
                index=0 if st.session_state.speed_boost == "유지" else (1 if st.session_state.speed_boost == "단기 시세차익 스윙" else 2)
            )
            
            submit_adjust = st.form_submit_button("✅ 조정된 포트폴리오 적용하기")
            
            if submit_adjust:
                st.session_state.safety_boost = safety_choice
                st.session_state.dividend_boost = dividend_choice
                st.session_state.speed_boost = speed_choice
                st.session_state.adjust_mode = False
                st.rerun()
                
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.adjust_mode = False
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    # '테스트 다시 하기' 버튼
    if st.button("🔄 테스트 다시 하기", use_container_width=True):
        st.session_state.current_node = "Q1"
        st.session_state.selected_persona = None
        st.session_state.final_tag = None
        st.session_state.history = []
        st.session_state.adjust_mode = False
        st.session_state.safety_boost = "유지"
        st.session_state.dividend_boost = "유지"
        st.session_state.speed_boost = "유지"
        st.rerun()

    # 투자 유의사항 및 법적 고지
    st.warning("""
        **⚠️ 투자 유의사항 및 법적 고지**  
        * 본 서비스에서 제공하는 재무지표 및 분석 결과는 참고용이며, 특정 종목에 대한 절대적인 투자 권유가 아닙니다.  
        * 주식 시장 변동에 따른 모든 투자 결정과 그 결과 책임은 **투자자 본인에게 귀속**됩니다.
    """)