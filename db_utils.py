# --- db_utils.py ---
from supabase import create_client, Client
import streamlit as st

# (기존의 Supabase 연결 코드는 유지)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 1. 유저 확인 및 생성 (없으면 만들고 user_id 반환)
def get_or_create_user(api_key):
    # 유저가 있는지 검색
    response = supabase.table('users').select('user_id').eq('api_key', api_key).execute()
    if response.data:
        return response.data[0]['user_id']
    else:
        # 없으면 새로 삽입
        new_user = supabase.table('users').insert({'api_key': api_key}).execute()
        return new_user.data[0]['user_id']

# 2. 캐릭터 캐싱 데이터 저장 (Upsert)
def upsert_character_cache(user_id, character_name, stats_data, equip_data):
    data = {
        "user_id": user_id,
        "character_name": character_name,
        "stats_data": stats_data,
        "equip_data": equip_data,
        "updated_at": "now()"
    }
    # user_id와 character_name 쌍이 이미 있으면 덮어쓰고, 없으면 삽입
    response = supabase.table('characters').upsert(data, on_conflict='user_id, character_name').execute()
    return response.data[0] if response.data else None

# 3. [지연 업데이트] 주간 사냥 시간만 쏙 업데이트하는 함수
def update_hunting_hours(character_id, hours):
    response = supabase.table('characters').update({'weekly_hunting_hours': hours}).eq('character_id', character_id).execute()
    return response.data

# 4. 캐릭터별 즐겨찾기 저장 함수
def save_favorite_item(character_id, part, item_name, price, trades, stats_json):
    data = {
        "character_id": character_id,
        "part": part,
        "item_name": item_name,
        "price": price,
        "trade_count_left": trades,
        "stats_json": stats_json
    }
    response = supabase.table('favorite_items').insert(data).execute()
    return response.data

# 5. 캐릭터별 즐겨찾기 불러오기
def get_favorite_items(character_id):
    response = supabase.table('favorite_items').select('*').eq('character_id', character_id).execute()
    return response.data

# --- db_utils.py 맨 아래에 추가 ---

def get_character_cache(character_name):
    """
    새로운 구조에 맞게 characters 테이블에서 닉네임으로 데이터를 조회합니다.
    (필요시 부모 테이블인 users의 api_key도 함께 가져옵니다)
    """
    try:
        response = supabase.table('characters').select('*, users(api_key)').eq('character_name', character_name).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"캐릭터 조회 중 오류 발생: {e}")
        return None
    
# --- db_utils.py 맨 아래 추가 ---

# --- db_utils.py ---

def get_starforce_expected_cost(equip_level, start_star, end_star, safeguard, event_key, item_cost):
    """
    Supabase DB에서 2025년 최신 스타포스 기댓값을 조회합니다.
    (starcatch 파라미터 완전 삭제됨)
    """
    try:
        response = supabase.table('starforce_costs') \
            .select('expected_meso, expected_destructions') \
            .eq('equip_level', equip_level) \
            .gte('current_star', start_star) \
            .lt('current_star', end_star) \
            .eq('safeguard', safeguard) \
            .eq('event_type', event_key) \
            .execute()
            
        if not response.data or len(response.data) == 0:
            return 0
        
        # 순수 강화 비용 + (파괴 횟수 기댓값 * 노작 장비 가격)
        total_meso = sum(row['expected_meso'] + (item_cost * row['expected_destructions']) for row in response.data)
        return total_meso
        
    except Exception as e:
        print(f"스타포스 기댓값 DB 조회 오류: {e}")
        return 0