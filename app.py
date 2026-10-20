import streamlit as st
import google.generativeai as genai

# 페이지 설정
st.set_page_config(
    page_title="스마트플레이스 대표 키워드 추출기",
    page_icon="🎯",
    layout="wide"
)

# 헤더 섹션
st.title("🎯 스마트플레이스 SEO 대표 키워드 자동 추출기")
st.markdown("매장명, 지역명, 업종을 입력하면 네이버 스마트플레이스 알고리즘과 검색 트렌드에 맞춘 **맞춤형 키워드 6종(직접 2, 간접 2, 이벤트 1, 롱테일 1)**을 추출합니다.")

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

# 실행 버튼
if st.button("🚀 키워드 추출 및 분석 시작", type="primary"):
    if not api_key:
        st.error("⚠️ Gemini API Key가 설정되지 않았습니다. (사이드바 입력 또는 Streamlit Secrets 설정 필요)")
    elif not store_name or not region_name:
        st.warning("⚠️ 매장명과 지역명은 필수 입력 항목입니다.")
    else:
        with st.spinner("🔍 네이버 로컬 검색 패턴 및 연관어 분석 중..."):
            try:
                # Gemini API 설정 (최신 표준 모델인 gemini-1.5-flash 적용)
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')

                # 프롬프트 엔지니어링 (15년 경력의 SEO 전문가 페르소나 부여)
                prompt = f"""
                너는 15년 경력의 네이버 스마트플레이스 SEO 및 로컬 검색 마케팅 전문가야.
                아래 입력된 매장 정보를 바탕으로 스마트플레이스 상위 노출 및 트래픽 유입에 가장 효과적인 대표 키워드들을 추출해줘.

                [입력 정보]
                - 매장명: {store_name}
                - 지역명: {region_name}
                - 업종: {business_type}

                [필수 요구 조건]
                반드시 아래의 구조와 개수에 정확히 맞춰 총 6개의 키워드를 추출하고, 각 키워드마다 타당한 전략적 이유를 함께 작성해줘.
                1. 직접 키워드 (2개): 업종명과 지역명이 결합되어 소비자가 검색할 확률이 가장 높은 핵심 타겟 키워드
                2. 간접 키워드 (2개): 연관 카테고리, 목적성 검색어 (예: 회식장소, 데이트코스, 선물, 기념일 등)
                3. 이벤트/시즌별 키워드 (1개): 계절, 날씨, 기념일, 특정 시즌에 유입을 극대화할 수 있는 키워드
                4. 롱테일 키워드 (1개): 세부 니즈를 타겟팅하는 3~4어절 이상의 구체적인 복합 키워드

                [출력 형식]
                결과는 마크다운 테이블 형태로 깔끔하게 출력해줘.
                컬럼 구성: [구분 | 추천 키워드 | 타겟팅 전략 및 예상 검색 의도]
                """

                response = model.generate_content(prompt)

                st.success("✨ 키워드 추출이 완료되었습니다!")
                st.divider()
                
                # 결과 출력
                st.markdown(response.text)

            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")
