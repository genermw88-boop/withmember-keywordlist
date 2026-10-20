import os
import io
import urllib.request
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from google import genai

# 페이지 설정
st.set_page_config(
    page_title="스마트플레이스 대표 키워드 추출기",
    page_icon="🎯",
    layout="wide"
)

# 📊 한글 폰트 강제 로드 및 등록 함수 (직접 TTF 다운로드 방식)
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/apache/nanumgothic/NanumGothic-Regular.ttf"
            urllib.request.urlretrieve(url, font_path)
        except Exception:
            pass
    
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        return prop
    return None

font_prop = get_korean_font()
if font_prop:
    plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

# 헤더 섹션
st.title("🎯 스마트플레이스 SEO 대표 키워드 자동 추출기")
st.markdown("매장명, 지역명, 업종, 그리고 선택적 이벤트 조건을 입력하면 네이버 스마트플레이스 알고리즘에 맞춘 **맞춤형 핵심 키워드**를 추출하고 이미지로 제공합니다.")

# API 키 설정 (Streamlit Secrets 우선 확인, 없으면 사이드바 입력창 활용)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    with st.sidebar:
        st.header("⚙️ 시스템 설정")
        api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studio에서 발급받은 API 키를 입력하세요.")
        st.divider()
        st.markdown("### 💡 개발자 팁")
        st.info("지역명은 '남양주시 별내동'처럼 세부 동 단위까지 입력할수록 정확도가 높아집니다.")

# 메인 입력 폼
col1, col2, col3 = st.columns(3)

with col1:
    store_name = st.text_input("매장명", placeholder="예: 온도네일스튜디오")
with col2:
    region_name = st.text_input("지역명", placeholder="예: 경기 남양주시 별내동")
with col3:
    business_type = st.text_input("업종 / 카테고리", placeholder="예: 네일아트")

# 이벤트/시즌별 키워드 입력 필드 (선택 사항)
event_input = st.text_input("🎯 이벤트 / 시즌별 키워드 조건 (선택 입력)", placeholder="예: 크리스마스, 여름휴가, 수험생 할인 등 (입력 시에만 반영됩니다)")

# 마크다운 테이블을 이미지(BytesIO)로 변환하는 함수 (셀 단위 폰트 강제 적용 포함)
def markdown_table_to_image(markdown_text, title="스마트플레이스 추천 키워드 분석"):
    lines = [line.strip() for line in markdown_text.split('\n') if '|' in line]
    table_data = []
    for line in lines:
        if '---' in line:
            continue
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if cols:
            table_data.append(cols)
    
    if len(table_data) < 2:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis('off')
        ax.text(0.05, 0.95, markdown_text, transform=ax.transAxes, fontsize=11, 
                verticalalignment='top', wrap=True, fontproperties=font_prop)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        plt.close(fig)
        buf.seek(0)
        return buf

    headers = table_data[0]
    rows = table_data[1:]

    fig, ax = plt.subplots(figsize=(12, len(rows) * 0.9 + 2.5))
    ax.axis('off')
    
    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)
    
    # 🔑 핵심: 테이블의 모든 셀(Cell)마다 한글 폰트 속성을 직접 강제 지정
    for (row, col), cell in table.get_celld().items():
        if font_prop:
            cell.get_text().set_fontproperties(font_prop)
        if row == 0:
            cell.set_facecolor('#2E7D32')
            cell.set_text_props(color='white', weight='bold')
            if font_prop:
                cell.get_text().set_fontproperties(font_prop)
        else:
            cell.set_facecolor('#F1F8E9' if row % 2 == 0 else '#FFFFFF')

    # 타이틀 폰트 적용
    if font_prop:
        plt.title(title, fontsize=15, weight='bold', pad=25, color='#1B5E20', fontproperties=font_prop)
    else:
        plt.title(title, fontsize=15, weight='bold', pad=25, color='#1B5E20')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    buf.seek(0)
    return buf

# 실행 버튼
if st.button("🚀 키워드 추출 및 이미지 생성 시작", type="primary"):
    if not api_key:
        st.error("⚠️ Gemini API Key가 설정되지 않았습니다. (사이드바 입력 또는 Streamlit Secrets 설정 필요)")
    elif not store_name or not region_name:
        st.warning("⚠️ 매장명과 지역명은 필수 입력 항목입니다.")
    else:
        with st.spinner("🔍 네이버 로컬 검색 패턴 분석 및 키워드 조합 생성 중..."):
            try:
                client = genai.Client(api_key=api_key)

                # 조건에 따른 프롬프트 구성
                if event_input.strip():
                    event_instruction = f"3. 이벤트/시즌별 키워드 (1개): 사용자가 입력한 조건인 '{event_input}'을 반영하여 트래픽을 극대화할 수 있는 시즈널 키워드"
                    total_desc = "총 6개의 키워드(직접 2개, 간접 2개, 이벤트/시즌 1개, 롱테일 1개)"
                else:
                    event_instruction = ""
                    total_desc = "총 5개의 키워드(직접 2개, 간접 2개, 롱테일 1개)"

                prompt = f"""
                너는 15년 경력의 네이버 스마트플레이스 SEO 및 로컬 검색 마케팅 전문가야.
                아래 입력된 매장 정보를 바탕으로 스마트플레이스 상위 노출 및 트래픽 유입에 가장 효과적인 대표 키워드들을 추출해줘.

                [입력 정보]
                - 매장명: {store_name}
                - 지역명: {region_name}
                - 업종: {business_type}
                {f"- 이벤트/시즌 조건: {event_input}" if event_input.strip() else ""}

                [필수 요구 조건]
                반드시 아래의 구조와 개수에 정확히 맞춰 {total_desc}를 추출하고, 각 키워드마다 타당한 전략적 이유를 함께 작성해줘.
                1. 직접 키워드 (2개): 업종명과 지역명이 결합되어 소비자가 검색할 확률이 가장 높은 핵심 타겟 키워드 (각각 다른 조합으로 2개)
                2. 간접 키워드 (2개): 연관 카테고리, 목적성 검색어 (예: 회식장소, 데이트코스, 선물 등)
                {f"3. 이벤트/시즌별 키워드 (1개): {event_instruction}" if event_input.strip() else ""}
                4. 롱테일 키워드 (1개): 세부 니즈를 타겟팅하는 3~4어절 이상의 구체적인 복합 키워드

                [출력 형식]
                결과는 마크다운 테이블 형태로 깔끔하게 출력해줘.
                컬럼 구성: [구분 | 추천 키워드 | 타겟팅 전략 및 예상 검색 의도]
                """

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )

                st.success("✨ 키워드 추출 및 이미지 변환이 완료되었습니다!")
                st.divider()
                
                # 1. 텍스트(마크다운) 결과 출력
                st.markdown("### 📋 텍스트 결과")
                st.markdown(response.text)
                
                st.divider()

                # 2. 이미지 변환 및 출력
                st.markdown("### 🖼️ 이미지 결과 및 다운로드")
                img_buffer = markdown_table_to_image(response.text, title=f"[{store_name}] 스마트플레이스 맞춤형 SEO 키워드 전략")
                
                # 화면에 이미지 표시
                st.image(img_buffer, caption="생성된 키워드 분석표 이미지", use_container_width=True)

                # 다운로드 버튼 제공
                st.download_button(
                    label="📥 분석표 이미지(PNG) 다운로드",
                    data=img_buffer,
                    file_name=f"{store_name}_키워드전략.png",
                    mime="image/png"
                )

            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")
