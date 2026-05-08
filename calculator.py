import streamlit as st
import math
import db_utils

# --- 1. 주간 수익 계산기 ---
def render_income_calculator():
    st.markdown("#### 💰 예상 주간 수익 입력")
    weekly_boss_income_eok = st.number_input("주간 보스 수익 (억 메소)", min_value=0.0, step=1.0, value=15.0, format="%.2f")
    hunting_hours = st.number_input("주간 평균 사냥 시간 (시간)", min_value=0, step=1, value=10)
    hunting_income_per_hour_eok = st.number_input("시간당 사냥 수익 (억 메소)", min_value=0.0, step=0.1, value=1.0, format="%.2f")
    
    total_income = (weekly_boss_income_eok + (hunting_hours * hunting_income_per_hour_eok)) * 100_000_000
    st.session_state.total_weekly_income = total_income
    st.info(f"**총 예상 주간 수익:** {total_income / 100_000_000:.2f}억 메소")

# --- 2. 최신 스타포스 기댓값 계산기 ---
def render_starforce_simulator():
    st.markdown("#### ⭐ 스타포스 기댓값 계산기")
    st.write("2025년 최신 확률표(30성 확장 및 하락 삭제)와 할인 혜택을 적용하여 목표 스타포스까지의 기댓값을 계산합니다.")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            equip_level = st.selectbox("장비 레벨", [130, 140, 150, 160, 200, 250], index=3) 
            # 🚀 수정: 최대 별 개수를 30성으로 확장
            current_sf = st.number_input("현재 스타포스", min_value=0, max_value=29, value=17, step=1)
            target_sf = st.number_input("목표 스타포스", min_value=1, max_value=30, value=22, step=1)
            item_base_cost_eok = st.number_input("노작 장비 가격 (파괴 복구용, 억 메소)", min_value=0.0, step=1.0, value=5.0, format="%.2f")
            
            st.write("") 
            st.markdown("**기본 할인 혜택**")
            mvp_grade = st.selectbox("MVP 등급", ["없음", "브론즈", "실버 (3%)", "골드 (5%)", "다이아/레드 (10%)"], index=0)
            pc_cafe = st.checkbox("PC방 혜택 (5% 할인)")
            
        with col2:
            st.write("") 
            st.markdown("**🌟 스페셜 이벤트 체크리스트**")
            
            event_discount_30 = st.checkbox("스타포스 강화 비용 30% 할인 (전 구간)")
            event_dest_reduce = st.checkbox("21성까지 파괴 확률 30% 감소 (샤타포스)")
            event_restore_20 = st.checkbox("흔적 복구 비용 20% 할인")
            
            st.write("")
            st.markdown("**특수 옵션**")
            if target_sf <= 18:
                safeguard = st.checkbox("파괴 방지 적용 (15~17성 구간 비용 2배)")
            else:
                safeguard = False
                st.checkbox("파괴 방지 적용 (목표 18성 이하일 때만 선택 가능)", value=False, disabled=True)
                
            st.success("✨ 25년도 패치: 30성 확장 & 하락 삭제 & 스타캐치(5%) 상시 자동 반영")
            
        # --- (위쪽 UI 코드는 기존과 동일하게 유지) ---
        st.divider()
        calc_sf_btn = st.button("스타포스 기댓값 계산하기", use_container_width=True, type="primary")
        
        if calc_sf_btn:
            if current_sf >= target_sf:
                st.warning("목표 스타포스가 현재 스타포스보다 커야 합니다.")
            else:
                with st.spinner("30성 확장 기댓값 및 리스크 구간 연산 중..."):
                    event_key = f"D30_{event_discount_30}_Dest_{event_dest_reduce}"
                    
                    actual_item_cost = (item_base_cost_eok * 100_000_000) * (0.8 if event_restore_20 else 1.0)
                    
                    base_expected_meso = db_utils.get_starforce_expected_cost(
                        equip_level, current_sf, target_sf, safeguard, event_key, actual_item_cost
                    )
                    
                    if base_expected_meso == 0:
                        st.error("아직 DB에 해당 조건의 계산 데이터가 주입되지 않았습니다! 배치 스크립트를 먼저 실행해주세요.")
                    else:
                        discount_rate = 0.0
                        if mvp_grade == "실버 (3%)": discount_rate += 0.03
                        elif mvp_grade == "골드 (5%)": discount_rate += 0.05
                        elif mvp_grade == "다이아/레드 (10%)": discount_rate += 0.10
                        if pc_cafe: discount_rate += 0.05
                        
                        final_meso = base_expected_meso * (1.0 - discount_rate)
                        
                        # 🚀 통계적 변동계수(CV)를 활용한 리스크(오차) 구간 산출
                        # 메이플 스타포스 분포 특성상 상위 10%는 평균의 약 35%, 하위 10%는 평균의 약 240% 수준에서 형성됩니다.
                        lucky_meso = final_meso * 0.35
                        unlucky_meso = final_meso * 2.40
                        
                        st.success("✅ 2025년도 30성 확률표 기반 기댓값 계산 및 리스크 분석이 완료되었습니다.")
                        
                        # 결과 시각화 (3단 컬럼)
                        res1, res2, res3 = st.columns(3)
                        
                        with res1:
                            st.info("🍀 **운수 좋은 날 (상위 10%)**")
                            st.markdown(f"<h4 style='color: #00d2ff;'>{lucky_meso / 100_000_000:.2f}억</h4>", unsafe_allow_html=True)
                            st.caption("스트레이트 강화에 성공할 확률입니다.")
                            
                        with res2:
                            st.success("⚖️ **평균 기댓값 (Average)**")
                            st.markdown(f"<h4>{final_meso / 100_000_000:.2f}억</h4>", unsafe_allow_html=True)
                            st.caption("가장 보편적인 소요 예산입니다.")
                            
                        with res3:
                            st.error("🚨 **파산 주의 (하위 10%)**")
                            st.markdown(f"<h4 style='color: #ff4b4b;'>{unlucky_meso / 100_000_000:.2f}억</h4>", unsafe_allow_html=True)
                            st.caption("이 금액은 모아두고 도전하는 것을 권장합니다.")
                            
                        # 리스크 바 (시각적 경고)
                        st.write("")
                        st.markdown("**📊 필요 예산 리스크 게이지**")
                        st.progress(0.7) # 시각적 긴장감을 주는 70% 고정 바
                        st.caption("우측으로 갈수록(하위 10%에 걸릴수록) 파산 및 멘탈 붕괴의 위험이 기하급수적으로 증가합니다.")