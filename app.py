import os
import io
import re
import urllib.request
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from google import genai

# 페이지 설정
st.set_page_config(
    page_title="스마트플레이스 대표 키워드 추출기",
    page_icon="🎯",
    layout="wide"
)

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

# 🔤 폰트 다운로드 및 적용 (검증된 CDN 링크 사용)
@st.cache_resource
def load_robust_font():
    font_path = "/tmp/NanumGothic.ttf"
    
    # 1. 시스템 설치 폰트 확인
    system_font_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    ]
    for sys_path in system_font_paths:
        if os.path.exists(sys_path):
            try:
                return (
                    ImageFont.truetype(sys_path, 22),
                    ImageFont.truetype(sys_path, 14),
                    ImageFont.truetype(sys_path, 13)
                )
            except Exception:
                pass

    # 2. 시스템 폰트가 없으면 안정적인 CDN 경로에서 직접 다운로드
    if not os.path.exists(font_path) or os.path.getsize(font_path) < 100000:
        urls = [
            "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nanumgothic/NanumGothic-Regular.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        ]
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                    out_file.write(response.read())
                if os.path.exists(font_path) and os.path.getsize(font_path) > 100000:
                    break
            except Exception:
                continue

    try:
        title_font = ImageFont.truetype(font_path, 22)
        header_font = ImageFont.truetype(font_path, 14)
        cell_font = ImageFont.truetype(font_path, 13)
        return title_font, header_font, cell_font
    except Exception:
        return ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()

title_font, header_font, cell_font = load_robust_font()

# 마크다운 특수문자(** 등) 제거 헬퍼 함수
def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    return text.strip()

# 텍스트 줄바꿈 함수
def wrap_text(text, font, max_width, draw):
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines if lines else [""]

# 마크다운 테이블을 깔끔한 PNG 이미지로 변환하는 함수
def markdown_table_to_image_pil(markdown_text, title="스마트플레이스 추천 키워드 분석"):
    lines = [line.strip() for line in markdown_text.split('\n') if '|' in line]
    table_data = []
    for line in lines:
        if '---' in line:
            continue
        cols = [clean_markdown(c.strip()) for c in line.split('|')[1:-1]]
        if cols:
            table_data.append(cols)
    
    if len(table_data) < 2:
        table_data = [["구분", "추천 키워드", "타겟팅 전략 및 예상 검색 의도"], ["결과", clean_markdown(markdown_text), "분석 결과"]]

    headers = table_data[0]
    rows = table_data[1:]

    col_widths = [160, 260, 700]
    total_width = sum(col_widths) + 60
    
    row_heights = []
    dummy_img = Image.new("RGB", (100, 100))
    dummy_draw = ImageDraw.Draw(dummy_img)

    header_max_lines = 1
    for i, h_text in enumerate(headers):
        wrapped = wrap_text(h_text, header_font, col_widths[i] - 20, dummy_draw)
        header_max_lines = max(header_max_lines, len(wrapped))
    header_height = header_max_lines * 22 + 20

    processed_rows = []
    for row in rows:
        row_wrapped_cells = []
        max_lines = 1
        for i, cell_text in enumerate(row):
            if i >= len(col_widths): 
                i = len(col_widths) - 1
            wrapped = wrap_text(cell_text, cell_font, col_widths[i] - 20, dummy_draw)
            row_wrapped_cells.append(wrapped)
            max_lines = max(max_lines, len(wrapped))
        r_height = max_lines * 22 + 20
        row_heights.append(r_height)
        processed_rows.append(row_wrapped_cells)

    total_height = 100 + header_height + sum(row_heights) + 50

    img = Image.new("RGB", (total_width, total_height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # 상단 타이틀
    draw.rectangle([30, 25, total_width - 30, 75], fill="#1B5E20")
    draw.text((50, 38), title, fill="#FFFFFF", font=title_font)

    y_current = 95
    x_start = 30

    # 테이블 헤더
    draw.rectangle([x_start, y_current, x_start + sum(col_widths), y_current + header_height], fill="#2E7D32")
    
    x_current = x_start
    for i, h_text in enumerate(headers):
        wrapped = wrap_text(h_text, header_font, col_widths[i] - 20, dummy_draw)
        text_y = y_current + 10
        for line in wrapped:
            bbox = dummy_draw.textbbox((0, 0), line, font=header_font)
            text_width = bbox[2] - bbox[0]
            line_x = x_current + (col_widths[i] - text_width) / 2
            draw.text((line_x, text_y), line, fill="#FFFFFF", font=header_font)
            text_y += 22
        
        if i < len(headers) - 1:
            draw.line([x_current + col_widths[i], y_current, x_current + col_widths[i], y_current + header_height], fill="#FFFFFF", width=1)
        x_current += col_widths[i]

    y_current += header_height

    # 테이블 데이터 행
    for r_idx, row_cells in enumerate(processed_rows):
        r_height = row_heights[r_idx]
        bg_color = "#F1F8E9" if r_idx % 2 == 0 else "#FFFFFF"
        
        draw.rectangle([x_start, y_current, x_start + sum(col_widths), y_current + r_height], fill=bg_color)
        
        x_current = x_start
        for c_idx, wrapped_lines in enumerate(row_cells):
            text_y = y_current + 10
            for line in wrapped_lines:
                if c_idx == 0:
                    bbox = dummy_draw.textbbox((0, 0), line, font=cell_font)
                    text_width = bbox[2] - bbox[0]
                    line_x = x_current + (col_widths[c_idx] - text_width) / 2
                else:
                    line_x = x_current + 10
                
                draw.text((line_x, text_y), line, fill="#333333", font=cell_font)
                text_y += 22
            
            draw.rectangle([x_current, y_current, x_current + col_widths[c_idx], y_current + r_height], outline="#CCCCCC", width=1)
            x_current += col_widths[c_idx]

        y_current += r_height

    draw.rectangle([x_start, 95, x_start + sum(col_widths), y_current], outline="#1B5E20", width=2)

    buf = io.BytesIO()
    img.save(buf, format='png', dpi=(300, 300))
    buf.seek(0)
    return buf

# 실행 버튼
if st.button("🚀 키워드 추출 및 이미지 생성 시작", type="primary"):
    if not api_key:
        st.error("⚠️ Gemini API Key가 설정되지 않았습니다.")
    elif not store_name or not region_name:
        st.warning("⚠️ 매장명과 지역명은 필수 입력 항목입니다.")
    else:
        with st.spinner("🔍 네이버 로컬 검색 패턴 분석 및 키워드 조합 생성 중..."):
            try:
                client = genai.Client(api_key=api_key)

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
                2. 간접 키워드 (2개): 연관 카테고리, 목적성 검색어 (예: 데이트코스, 선물 등)
                {f"3. 이벤트/시즌별 키워드 (1개): {event_instruction}" if event_input.strip() else ""}
                4. 롱테일 키워드 (1개): 세부 니즈를 타겟팅하는 3~4어절 이상의 구체적인 복합 키워드

                [엄격한 제약 사항 (Negative Constraint)]
                - 업종이 식음료/음식점이 아닐 경우, '맛집' 단어가 포함된 키워드는 절대 추출하지 마세요. (예: 네일아트, 뷰티, 펜션 등 매장 성격에 맞지 않는 '맛집' 키워드 원천 차단)

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
                
                # 1. 텍스트 결과 출력
                st.markdown("### 📋 텍스트 결과")
                st.markdown(response.text)
                
                st.divider()

                # 2. 이미지 변환 및 출력
                st.markdown("### 🖼️ 이미지 결과 및 다운로드")
                img_buffer = markdown_table_to_image_pil(response.text, title=f"[{store_name}] 스마트플레이스 맞춤형 SEO 키워드 전략")
                
                st.image(img_buffer, caption="생성된 키워드 분석표 이미지", use_container_width=True)

                st.download_button(
                    label="📥 분석표 이미지(PNG) 다운로드",
                    data=img_buffer,
                    file_name=f"{store_name}_키워드전략.png",
                    mime="image/png"
                )

            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {e}")
