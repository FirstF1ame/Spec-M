import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
import re
import altair as alt

import db_utils
import api_utils
import calculator 

# ---------------------------------------------------------------------
# --- 1. 페이지 기본 설정
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Spec-M | 최적의 스펙업 로드맵", 
    page_icon="🗡️", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)


# ---------------------------------------------------------------------
# --- 2. CSS 스타일 정의 ---
# ---------------------------------------------------------------------
st.markdown("""
<style>
    /* 메이플 UI 특유의 짙은 네이비/차콜 톤 그라데이션 */
    .stApp {
        background: linear-gradient(135deg, #13151A 0%, #1A1D24 50%, #0D1117 100%);
    }

    /* 모든 컨테이너(박스)를 메이플 장비창처럼 반투명하게 만들기 */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"],
    .stForm, .stTabs [data-baseweb="tab-panel"] {
        background-color: rgba(30, 34, 42, 0.7) !important;
        border: 1px solid rgba(85, 95, 110, 0.5) !important;
        border-radius: 8px !important;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
        padding: 1.5rem !important;
        margin-bottom: 1rem;
    }

    /* 버튼 스타일링 (메이플스타일 골드/옐로우 포인트) */
    .stButton>button[kind="primary"] {
        background: linear-gradient(180deg, #FFD700 0%, #FFA500 100%);
        color: #333333 !important;
        font-weight: 900 !important;
        border: 2px solid #B8860B !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(180deg, #FFF8DC 0%, #FFD700 100%);
        border-color: #DAA520 !important;
    }

    /* 장비 그리드 스타일 정의 */
    .eq-grid {
        display: grid;
        grid-template-columns: repeat(7, 55px);
        grid-template-rows: repeat(6, 55px);
        gap: 5px;
        width: max-content;
        padding: 15px;
        background: rgba(10, 10, 10, 0.5);
        border: 1px solid #444;
        border-radius: 5px;
        margin: 0 auto;
    }
    .eq-slot {
        width: 100%; height: 100%;
        background-color: #333;
        border: 1px solid #555;
        border-radius: 3px;
        position: relative;
        display: flex; align-items: center; justify-content: center;
    }
    .eq-slot img {
        width: 40px; height: 40px;
        object-fit: contain;
    }
    .part-label { font-size: 9px; color: #aaa; position: absolute; bottom: 2px; line-height: 1; text-align: center; width: 100%; }
    .star-label {
        font-size: 10px; color: #ffeb3b; position: absolute; top: 1px; right: 2px; z-index: 3; font-weight: bold;
        text-shadow: 1px 1px 2px #000;
    }
    
    /* 잠재능력 등급별 테두리 */
    .border-legendary { border: 2px solid #51ff00 !important; }
    .border-unique { border: 2px solid #ffcc00 !important; border-radius: 3px; }
    .border-epic { border: 2px solid #c800ff !important; border-radius: 3px; }
    .border-rare { border: 2px solid #00d9ff !important; border-radius: 3px; }
    
    /* 가독성을 위한 텍스트 스타일 */
    .stMarkdown, .stMetric, label, p {
        color: #EEE !important;
    }
    h1, h2, h3 {
        color: #FFF !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# --- 🚀 [수정] 우측 상단 로고 이미지 배치
# ---------------------------------------------------------------------
header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.title("🗡️ Spec-M")

with header_col2:
    st.markdown(
        f'<div style="text-align: right; padding-top: 15px;">'
        f'<img src="https://imgur.com/QKsqdvp.jpg" width="120">'
        f'</div>', 
        unsafe_allow_html=True
    )

st.markdown("**당신의 시간과 재화를 아껴주는 최적의 스펙업 로드맵**")
st.divider()

# --- 2. 세션 상태 초기화 ---
if 'char_data' not in st.session_state:
    st.session_state.char_data = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'dashboard'
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# --- 🚀 핵심 분석 알고리즘 (주스탯 % 환산 및 플가 필터링 적용) ---
def calculate_custom_score(item):
    total_score = 0.0
    
    all_options = []
    for i in range(1, 4):
        all_options.append(item.get(f"potential_option_{i}", ""))
        all_options.append(item.get(f"additional_potential_option_{i}", ""))

    for opt in all_options:
        if not opt: continue
        if "9레벨당" in opt:
            total_score += 6.0
        elif "%" in opt:
            match = re.search(r'\+(\d+)%', opt)
            if match: 
                total_score += float(match.group(1))
        elif "공격력" in opt or "마력" in opt:
            match = re.search(r'\+(\d+)', opt)
            if match:
                atk_val = float(match.group(1))
                total_score += (atk_val * 3.5) / 10.0

    starforce = int(item.get("starforce", 0))
    total_score += starforce * 1.5
    
    part = item.get("item_equipment_part", "")
    if part in ["무기", "보조무기", "엠블렘"]:
        total_score *= 1.5
        
    non_plat_parts = ["엠블렘", "보조무기", "기계 심장"]
    event_rings = ["테네브리스", "글로리온", "어웨이크", "결속", "카오스 링", "어드벤처", "SS급", "오닉스", "코스모스", "벤젼스", "이터널 플레임", "어비스 헌터스"]
    
    if part in non_plat_parts or any(ring in item.get("item_name", "") for ring in event_rings):
        total_score += 1000.0
        
    return total_score

# --- 3. 중앙 폼 영역 (로그인 및 검색) ---
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("<h3 style='text-align: center;'>나의 스펙 진단하기</h3>", unsafe_allow_html=True)
    with st.form("login_form"):
        api_key = st.text_input("넥슨 개발자 센터 API Key", type="password", value=st.session_state.api_key)
        character_name = st.text_input("캐릭터 닉네임", placeholder="조회할 캐릭터의 정확한 닉네임을 입력해 주세요.")
        submit_btn = st.form_submit_button("내 스펙 진단하기", width="stretch")

    if submit_btn:
        if not character_name:
            st.warning("조회할 캐릭터 닉네임을 입력해 주세요.")
        else:
            with st.spinner(f"'{character_name}'님의 정보를 찾는 중..."):
                cached_data = db_utils.get_character_cache(character_name)
                use_cache = False
                
                if cached_data:
                    updated_time = pd.to_datetime(cached_data['updated_at'])
                    current_time = datetime.now(updated_time.tzinfo)
                    if current_time - updated_time < timedelta(days=7):
                        use_cache = True
                        st.success(f"✨ '{character_name}'님의 최근 기록을 DB에서 찾았습니다!")
                        
                        basic_data = cached_data.get('stats_data', {}).get('basic', {})
                        equip_data = cached_data.get('equip_data', {}) 
                        
                        if cached_data.get('users') and cached_data['users'].get('api_key'):
                            st.session_state.api_key = cached_data['users']['api_key']
                        
                        st.session_state.user_id = cached_data['user_id']
                        st.session_state.character_id = cached_data['character_id']
                
                if not use_cache:
                    if not api_key:
                        st.error("❌ 신규 검색입니다. API Key를 입력해 주세요.")
                        st.stop()
                    
                    st.info("🔄 넥슨 서버와 통신합니다...")
                    ocid = api_utils.get_ocid(api_key, character_name)
                    if ocid:
                        basic_data = api_utils.get_character_basic(api_key, ocid)
                        stat_data = api_utils.get_character_stat(api_key, ocid)
                        equip_data = api_utils.get_character_equipment(api_key, ocid)
                        
                        if basic_data and stat_data and equip_data:
                            user_id = db_utils.get_or_create_user(api_key)
                            combined_stats = {"basic": basic_data, "stat": stat_data}
                            
                            char_record = db_utils.upsert_character_cache(user_id, character_name, combined_stats, equip_data)
                            
                            st.session_state.api_key = api_key 
                            st.session_state.user_id = user_id
                            st.session_state.character_id = char_record['character_id']
                        else:
                            st.error("데이터 로드 실패.") ; st.stop()
                    else:
                        st.error("캐릭터를 찾을 수 없습니다.") ; st.stop()

                equipment_list = equip_data.get("item_equipment", [])
                all_ui_items = []    
                analyzed_items = []  

                for item in equipment_list:
                    slot_name = item.get("item_equipment_slot", "") 
                    part_name = item.get("item_equipment_part", "알 수 없음")
                    part = slot_name if slot_name else part_name 
                    
                    item_name = item.get("item_name", "알 수 없음")
                    icon = item.get("item_icon", item.get("item_shape_icon", "")) 
                    starforce = int(item.get("starforce", 0))
                    potential = item.get("potential_option_grade", "없음")
                    
                    ui_item = {"part": part, "part_name": part_name, "name": item_name, "starforce": starforce, "potential": potential, "icon": icon}
                    all_ui_items.append(ui_item)
                    
                    seed_rings = ["리스트레인트", "컨티뉴어스", "웨폰퍼프", "리스크테이커", "크라이시스", "레벨퍼프", "링 오브 썸", "듀라빌리티"]
                    is_seed_ring = any(ring in item_name for ring in seed_rings)
                    
                    if part in ["훈장", "포켓 아이템", "뱃지"] or is_seed_ring:
                        continue

                    final_score = calculate_custom_score(item)
                    analyzed_items.append({**ui_item, "score": final_score})

                analyzed_items.sort(key=lambda x: x["score"], reverse=True)

                st.session_state.char_data = {
                    "level": basic_data.get("character_level", 0),
                    "class": basic_data.get("character_class", "알 수 없음"),
                    "image": basic_data.get("character_image", ""), 
                    "all_ui_items": all_ui_items, 
                    "analyzed_items": analyzed_items
                }
                st.session_state.current_view = 'dashboard'
                st.rerun() 

# ---------------------------------------------------------------------
# --- 🖥️ 4. 결과 렌더링 영역 ---
# ---------------------------------------------------------------------
if st.session_state.char_data:
    st.write("")
    st.divider()
    
    head_col, nav1, nav2, nav3 = st.columns([2.5, 1, 1, 1])
    with head_col:
        st.markdown(f"### 🎉 스펙 진단 완료! **Lv.{st.session_state.char_data['level']} {st.session_state.char_data['class']}**")
    
    with nav1:
        if st.button("📊 대시보드", width="stretch", type="primary" if st.session_state.current_view == 'dashboard' else "secondary"):
            st.session_state.current_view = 'dashboard' ; st.rerun()
    with nav2:
        if st.button("🔄 시뮬레이터", width="stretch", type="primary" if st.session_state.current_view == 'simulator' else "secondary"):
            st.session_state.current_view = 'simulator' ; st.rerun()
    with nav3:
        if st.button("⭐ 보관함", width="stretch", type="primary" if st.session_state.current_view == 'favorites' else "secondary"):
            st.session_state.current_view = 'favorites' ; st.rerun()

    # =========================================================
    # [뷰 1] 대시보드 화면
    # =========================================================
    if st.session_state.current_view == 'dashboard':
        st.subheader("📊 나의 장비 세팅 및 분석")

        st.markdown("""
        <style>
            .eq-grid {
                display: grid;
                grid-template-columns: repeat(7, 55px);
                grid-template-rows: repeat(6, 55px);
                gap: 5px;
                width: max-content;
                background-color: #1e1e1e;
                padding: 15px;
                border: 2px solid #555;
                border-radius: 8px;
                margin: 0 auto;
            }
            .eq-slot {
                width: 100%; height: 100%;
                background-color: #333;
                border: 1px solid #666;
                border-radius: 4px;
                position: relative;
                display: flex; align-items: center; justify-content: center;
            }
            .eq-slot img {
                width: 40px; height: 40px;
                object-fit: contain;
                z-index: 2;
            }
            .char-image-box {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 6px;
                display: flex; align-items: center; justify-content: center;
                overflow: hidden;
            }
            .char-image-box img {
                max-width: 100%; max-height: 100%; object-fit: contain;
            }
            .part-label { font-size: 10px; color: #888; position: absolute; bottom: 2px; line-height: 1; text-align: center; width: 100%; }
            .star-label {
                font-size: 11px; color: #ffeb3b; position: absolute; top: 2px; right: 4px; z-index: 3; font-weight: bold;
                text-shadow: 1px 1px 2px #000;
            }
            .border-legendary { border: 2px solid #51ff00 !important; }
            .border-unique { border: 2px solid #ffcc00 !important; }
            .border-epic { border: 2px solid #c800ff !important; }
            .border-rare { border: 2px solid #00d9ff !important; }
            
            .aura-strong { box-shadow: 0 0 12px #00bcff, inset 0 0 10px #00bcff; animation: pulse-b 1.5s infinite; }
            .aura-weak { box-shadow: 0 0 12px #ff4b4b, inset 0 0 10px #ff4b4b; animation: pulse-r 1.5s infinite; }
            @keyframes pulse-b { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            @keyframes pulse-r { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            
            .empty-slot { background-color: #1a1a1a; border: 1px dashed #555; }
        </style>
        """, unsafe_allow_html=True)

        strong_names = [item['name'] for item in st.session_state.char_data['analyzed_items'][:3]]
        weak_names = [item['name'] for item in st.session_state.char_data['analyzed_items'][-3:]]

        def render_slot(part_keywords, label, row, col):
            if isinstance(part_keywords, str): 
                part_keywords = [part_keywords]
            
            item = None
            for k in part_keywords:
                for i in st.session_state.char_data['all_ui_items']:
                    if i['part'] == k:
                        item = i
                        break
                if item: break
            
            if not item:
                for k in part_keywords:
                    for i in st.session_state.char_data['all_ui_items']:
                        if k in i['part'] or k in i.get('part_name', ''):
                            if k == '무기' and '보조' in i['part']: continue 
                            if k == '펜던트' and '2' in i['part']: continue 
                            item = i
                            break
                    if item: break

            grid_style = f"grid-row: {row}; grid-column: {col};"
            
            if not item or not item.get("icon"):
                return f'<div class="eq-slot empty-slot" style="{grid_style}"><div class="part-label">{label}</div></div>'
            
            classes = ["eq-slot"]
            if item['potential'] == "레전드리": classes.append("border-legendary")
            elif item['potential'] == "유니크": classes.append("border-unique")
            elif item['potential'] == "에픽": classes.append("border-epic")
            elif item['potential'] == "레어": classes.append("border-rare")
            
            if item['name'] in strong_names: classes.append("aura-strong")
            elif item['name'] in weak_names: classes.append("aura-weak")
            
            star_html = f'<div class="star-label">★{item["starforce"]}</div>' if item["starforce"] > 0 else ""
            img_html = f'<img src="{item["icon"]}">'
            
            return f'<div class="{" ".join(classes)}" style="{grid_style}" title="{item["name"]} ({item["potential"]})">{star_html}{img_html}</div>'

        dashboard_col1, dashboard_col2 = st.columns([1.2, 1])

        with dashboard_col1:
            char_img_url = st.session_state.char_data.get('image', '')
            char_html = f'<img src="{char_img_url}">' if char_img_url else '<div class="part-label">캐릭터</div>'

            html_parts = []
            html_parts.append('<div class="eq-grid">')
            
            html_parts.append(render_slot(['반지1'], '반지1', 1, 1))
            html_parts.append(render_slot(['얼굴장식'], '얼굴장식', 1, 2))
            html_parts.append(f'<div class="char-image-box" style="grid-row: 1 / 5; grid-column: 3 / 6;">{char_html}</div>')
            html_parts.append(render_slot(['모자'], '모자', 1, 6))
            html_parts.append(render_slot(['망토'], '망토', 1, 7))
            
            html_parts.append(render_slot(['반지2'], '반지2', 2, 1))
            html_parts.append(render_slot(['눈장식'], '눈장식', 2, 2))
            html_parts.append(render_slot(['상의', '한벌옷'], '상의', 2, 6))
            html_parts.append(render_slot(['장갑'], '장갑', 2, 7))
            
            html_parts.append(render_slot(['반지3'], '반지3', 3, 1))
            html_parts.append(render_slot(['귀고리', '귀걸이'], '귀걸이', 3, 2))
            html_parts.append(render_slot(['하의'], '하의', 3, 6))
            html_parts.append(render_slot(['신발'], '신발', 3, 7))
            
            html_parts.append(render_slot(['반지4'], '반지4', 4, 1))
            html_parts.append(render_slot(['펜던트', '펜던트1'], '펜던트1', 4, 2))
            html_parts.append(render_slot(['어깨장식'], '어깨장식', 4, 6))
            html_parts.append(render_slot(['훈장'], '훈장', 4, 7))
            
            html_parts.append(render_slot(['벨트'], '벨트', 5, 1))
            html_parts.append(render_slot(['펜던트2'], '펜던트2', 5, 2))
            html_parts.append(render_slot(['무기'], '무기', 5, 3))
            html_parts.append(render_slot(['보조무기', '보조 무기'], '보조무기', 5, 4))
            html_parts.append(render_slot(['엠블렘'], '엠블렘', 5, 5))
            html_parts.append('<div class="eq-slot empty-slot" style="grid-row: 5; grid-column: 6;"><div class="part-label">안드로이드</div></div>')
            html_parts.append(render_slot(['기계 심장', '심장'], '하트', 5, 7))
            
            html_parts.append(render_slot(['포켓 아이템'], '포켓', 6, 1))
            html_parts.append('<div class="empty-span-box" style="grid-row: 6; grid-column: 2 / 7; border: 1px dashed #444; border-radius: 4px;"></div>')
            html_parts.append(render_slot(['뱃지'], '뱃지', 6, 7))
            
            html_parts.append('</div>')
            
            st.markdown("".join(html_parts), unsafe_allow_html=True)

        with dashboard_col2:
            st.markdown("### 🔍 정밀 스펙 분석 리포트")
            st.write("잠재능력 수치(%)와 공/마를 실제 효율로 환산하여 분석한 결과입니다.")
            st.info(f"**💪 가장 강력한 부위 TOP 3:**\n\n{', '.join(strong_names)}")
            st.warning(f"**🚨 최우선 교체 권장 TOP 3:**\n\n{', '.join(weak_names)}")
            st.write("마우스를 아이템 아이콘 위에 올리면 상세 정보가 표시됩니다.")

        # --- 🚀 [수정] 대시보드 하단: 일요일 강조 메소 시세 트렌드 그래프 ---
        st.write("")
        st.divider()
        st.subheader("📈 최근 4주간 메소 시세 동향")
        st.write("안전한 스펙업의 첫걸음은 시세의 흐름을 읽는 것입니다. (1억 메소 당 거래가)")

        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(27, -1, -1)]
        is_sunday = [(today - timedelta(days=i)).weekday() == 6 for i in range(27, -1, -1)]

        np.random.seed(42)
        price_changes = np.random.normal(loc=0, scale=30, size=28) 
        prices = [2750]
        for change in price_changes[1:]:
            prices.append(int(prices[-1] + change))

        df_meso = pd.DataFrame({
            "날짜": pd.to_datetime(dates),
            "1억 메소 당 가격(원)": prices,
            "일요일": is_sunday
        })

        min_price = min(prices)
        max_price = max(prices)
        current_price = prices[-1]
        week_ago_price = prices[-8]
        price_diff = current_price - week_ago_price

        y_min = min_price - 50 
        
        base = alt.Chart(df_meso).encode(
            x=alt.X('날짜:T', title='', axis=alt.Axis(format='%m-%d', grid=False)),
            y=alt.Y('1억 메소 당 가격(원):Q', title='1억 메소 (원)', scale=alt.Scale(domain=[y_min, max_price + 50]))
        )

        line = base.mark_line(color='#FFD700', strokeWidth=3)

        points = base.mark_circle(size=60).encode(
            color=alt.condition(alt.datum.일요일, alt.value('#FF4B4B'), alt.value('#FFD700')),
            tooltip=[alt.Tooltip('날짜:T', format='%Y-%m-%d'), alt.Tooltip('1억 메소 당 가격(원):Q', format=',')]
        )

        rules = base.mark_rule(color='#FF4B4B', strokeDash=[4, 4], opacity=0.6).encode(
            x='날짜:T'
        ).transform_filter(alt.datum.일요일)

        chart = (rules + line + points).properties(height=350).interactive()
        st.altair_chart(chart, width="stretch")
        
        st.write("")
        col1, col2, col3 = st.columns(3)
        col1.metric("현재 시세", f"{current_price:,}원", f"{price_diff:+,}원 (전주 대비)")
        col2.metric("최근 4주 최고가", f"{max_price:,}원")
        col3.metric("최근 4주 최저가", f"{min_price:,}원")

    # =========================================================
    # [뷰 2] 시뮬레이터 화면 
    # =========================================================
    elif st.session_state.current_view == 'simulator':
        st.subheader("🔄 스펙업 가성비 시뮬레이터")
        st.markdown("경매장에서 본 아이템의 정보와 나의 플레이 타임을 입력하여 **정확한 소요 주차와 회수율**을 진단해 보세요.")
        
        sim_col1, sim_col2 = st.columns(2)
        
        with sim_col1:
            st.markdown("#### 🛍️ 구매 희망 아이템 정보")
            with st.form("item_sim_form"):
                target_part = st.selectbox("장착 부위", ["무기", "보조무기", "엠블렘", "모자", "상의", "하의", "신발", "장갑", "망토", "어깨장식", "반지", "펜던트", "얼굴장식", "눈장식", "귀고리", "벨트", "심장"])
                target_item_name = st.text_input("아이템 이름", placeholder="예: 17성 레전드리 앱솔랩스 무기")
                target_price_eok = st.number_input("경매장 가격 (억 메소)", min_value=0.0, step=1.0, value=15.0, format="%.2f")
                trades_left = st.slider("남은 가위 횟수 (거래 가능 횟수)", min_value=0, max_value=10, value=10)
                calc_btn = st.form_submit_button("가성비 및 회수율 계산", width="stretch")

        with sim_col2:
            calculator.render_income_calculator()

        if calc_btn:
            target_price = target_price_eok * 100_000_000
            
            if target_price > 0 and target_item_name:
                weekly_income = st.session_state.get('total_weekly_income', 0)
                weeks_needed = math.ceil(target_price / weekly_income) if weekly_income > 0 else 0

                after_equip_trades = trades_left - 1
                if after_equip_trades <= 0:
                    recoverable_meso, return_rate = 0, 0.0
                else:
                    log_multiplier = math.log10(after_equip_trades + 1) / math.log10(10)
                    recoverable_meso = target_price * 0.95 * log_multiplier
                    return_rate = (recoverable_meso / target_price) * 100

                st.write("---")
                st.subheader("💡 AI 스펙업 진단 결과")
                
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("⏳ 예상 소요 기간", f"약 {weeks_needed}주" if weeks_needed > 0 else "측정 불가")
                res_col2.metric("📉 예상 회수율", f"{return_rate:.1f}%")
                res_col3.metric("💰 나중에 되팔 때 금액", f"{recoverable_meso / 100_000_000:.2f}억 메소")

                st.session_state.last_sim_result = {
                    "part": target_part, "name": target_item_name, "price": target_price,
                    "trades": trades_left, "weeks": weeks_needed, "rate": return_rate, "meso": recoverable_meso
                }
            else:
                st.warning("아이템 이름과 가격을 올바르게 입력해 주세요.")
        
        if st.session_state.get('last_sim_result'):
            if st.button("⭐ 이 시뮬레이션 결과 즐겨찾기에 저장하기", width="stretch"):
                res = st.session_state.last_sim_result
                stats_json = {"expected_weeks": res['weeks'], "return_rate": res['rate'], "recoverable_meso": res['meso']}
                
                char_id = st.session_state.get('character_id')
                if char_id:
                    db_utils.save_favorite_item(char_id, res['part'], res['name'], res['price'], res['trades'], stats_json)
                    st.success(f"✅ '{res['name']}'이(가) 즐겨찾기에 안전하게 저장되었습니다!")
                    st.session_state.last_sim_result = None 
                else:
                    st.error("캐릭터 정보가 만료되었습니다. 다시 조회해 주세요.")
                    
        st.write("")
        st.divider()
        calculator.render_starforce_simulator()

    # =========================================================
    # [뷰 3] 즐겨찾기 보관함 화면
    # =========================================================
    elif st.session_state.current_view == 'favorites':
        st.subheader("⭐ 스펙업 가성비 보관함")
        st.markdown("저장해둔 시뮬레이션 결과를 모아보고, 어떤 아이템을 먼저 구매하는 것이 **가장 이득(가성비)**인지 비교해 보세요.")
        
        char_id = st.session_state.get('character_id')
        
        if char_id:
            favorites = db_utils.get_favorite_items(char_id)
            
            if not favorites:
                st.info("💡 아직 저장된 즐겨찾기가 없습니다. 시뮬레이터에서 찜하고 싶은 아이템을 먼저 저장해 보세요!")
            else:
                df_fav = pd.DataFrame(favorites)
                df_fav['expected_weeks'] = df_fav['stats_json'].apply(lambda x: x.get('expected_weeks', 0))
                df_fav['return_rate'] = df_fav['stats_json'].apply(lambda x: x.get('return_rate', 0.0))
                
                sort_option = st.radio("어떤 기준으로 아이템을 비교할까요?", 
                    ["📉 회수율이 높은 순서 (되팔 때 이득)", "⏳ 소요 주차가 짧은 순서 (빠른 스펙업)", "💰 가격이 저렴한 순서"], horizontal=True)
                st.write("")
                
                if sort_option == "📉 회수율이 높은 순서 (되팔 때 이득)":
                    df_fav = df_fav.sort_values(by='return_rate', ascending=False)
                elif sort_option == "⏳ 소요 주차가 짧은 순서 (빠른 스펙업)":
                    df_fav = df_fav.sort_values(by='expected_weeks', ascending=True)
                else:
                    df_fav = df_fav.sort_values(by='price', ascending=True)
                
                for idx, row in df_fav.iterrows():
                    with st.container():
                        st.markdown(f"#### [{row['part']}] {row['item_name']}")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("경매장 가격", f"{row['price'] / 100_000_000:.2f}억 메소")
                        col2.metric("남은 가위 횟수", f"{row['trade_count_left']}회")
                        col3.metric("예상 소요 기간", f"약 {row['expected_weeks']}주")
                        col4.metric("로그스케일 예상 회수율", f"{row['return_rate']:.1f}%", delta="가성비 지표", delta_color="off")
                        st.divider()
        else:
            st.error("캐릭터 정보가 만료되었습니다. 다시 조회해 주세요.")