import requests
import urllib.parse

# 넥슨 API 기본 주소
BASE_URL = "https://open.api.nexon.com/maplestory/v1"

def get_ocid(api_key, character_name):
    """
    캐릭터 닉네임을 통해 고유 식별자(OCID)를 조회합니다.
    """
    url = f"{BASE_URL}/id?character_name={urllib.parse.quote(character_name)}"
    headers = {"x-nxopen-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("ocid")
    else:
        print(f"OCID 조회 실패: {response.status_code}")
        return None

def get_character_stat(api_key, ocid, date=None):
    """
    OCID를 사용하여 캐릭터의 종합 스탯을 조회합니다.
    (date 파라미터를 안 넣으면 어제 기준 최신 데이터를 가져옵니다)
    """
    url = f"{BASE_URL}/character/stat?ocid={ocid}"
    if date:
        url += f"&date={date}"
        
    headers = {"x-nxopen-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"스탯 조회 실패: {response.status_code}")
        return None

def get_character_equipment(api_key, ocid, date=None):
    """
    OCID를 사용하여 캐릭터가 현재 장착 중인 장비 정보를 조회합니다.
    """
    url = f"{BASE_URL}/character/item-equipment?ocid={ocid}"
    if date:
        url += f"&date={date}"
        
    headers = {"x-nxopen-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"장비 조회 실패: {response.status_code}")
        return None
    
# --- api_utils.py 파일의 기존 코드 아래에 추가 ---

def get_character_basic(api_key, ocid, date=None):
    """
    OCID를 사용하여 캐릭터의 기본 정보(레벨, 전직, 경험치 등)를 조회합니다.
    """
    url = f"{BASE_URL}/character/basic?ocid={ocid}"
    if date:
        url += f"&date={date}"
        
    headers = {"x-nxopen-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"기본 정보 조회 실패: {response.status_code}")
        return None