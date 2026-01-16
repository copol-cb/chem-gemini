import os
import django
import pandas as pd
import re

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import ChemicalRegulation

# ==========================================
# [설정] 파일 이름
file_main = "ban_chem.xlsx"       
file_detail = "ban_gc_chem.xlsx"  

# [설정] 엑셀 컬럼 이름
col_main_code = "고유번호"
col_main_text = "화학물질의 명칭"  
col_main_detail = "금지내용"       

col_detail_code = "고유번호"
col_detail_cas = "CAS No."         
# ==========================================

def extract_percentage(text):
    if pd.isna(text): return 0.0
    match = re.search(r'(\d+(\.\d+)?)%', str(text))
    if match:
        return float(match.group(1))
    return 0.0 

def clean_code(code):
    return str(code).replace(' ', '').replace('\n', '').strip()

def extract_cas_from_text(text):
    """ 텍스트 안에 숨어있는 CAS 번호(숫자-숫자-숫자)를 찾아냅니다. """
    if pd.isna(text): return None
    match = re.search(r'(\d{2,7}-\d{2}-\d)', str(text))
    if match:
        return match.group(1)
    return None

def run_upload():
    print("🚀 금지물질 통합(Merge) 업로드를 시작합니다...")
    
    try:
        df_main = pd.read_excel(file_main)
        df_detail = pd.read_excel(file_detail)
        
        df_main.columns = df_main.columns.str.replace('\n', '').str.strip()
        df_detail.columns = df_detail.columns.str.replace('\n', '').str.strip()
        
        if col_detail_code in df_detail.columns:
            df_detail[col_detail_code] = df_detail[col_detail_code].ffill()
            
        print(f"✅ 엑셀 파일 읽기 성공")

    except FileNotFoundError as e:
        print(f"❌ 엑셀 파일을 찾을 수 없습니다.\n{e}")
        return

    # 1. 기존 금지물질 데이터 초기화
    print("🧹 기존 금지물질 데이터를 비웁니다...")
    ChemicalRegulation.objects.filter(regulation_type="금지물질").delete()

    # [핵심] 중복 방지를 위한 '등록된 CAS 목록' (집합)
    registered_cas_set = set()

    # 2. 메인 파일 분석
    print("📚 규제 정보를 정리하는 중...")
    rule_dict = {}
    count_main_cas = 0
    
    for index, row in df_main.iterrows():
        if pd.isna(row.get(col_main_code)): continue
        
        code = clean_code(row[col_main_code])
        raw_text = str(row.get(col_main_text, ""))
        detail_text = str(row.get(col_main_detail, ""))
        limit_val = extract_percentage(raw_text)
        
        if not detail_text or detail_text == 'nan':
            detail_text = "제조, 수입, 판매, 보관, 저장, 운반, 사용을 금지"

        rule_dict[code] = {
            'limit': limit_val,
            'detail': detail_text,
            'name_hint': raw_text[:100]
        }

        # [NEW] 메인 파일에서 CAS 추출 및 중복 체크
        found_cas = extract_cas_from_text(raw_text)
        if found_cas:
            # 이미 등록된 CAS면 건너뜀
            if found_cas not in registered_cas_set:
                ChemicalRegulation.objects.create(
                    cas_no=found_cas, 
                    name_korean=raw_text[:100], 
                    limit_concentration=limit_val, 
                    regulation_type='금지물질',
                    regulation_details=detail_text
                )
                registered_cas_set.add(found_cas) # 명단에 추가
                count_main_cas += 1

    print(f"   ℹ️ 메인 파일에서 직접 추출한 CAS: {count_main_cas}개")

    # 3. 상세 목록 연결하기
    print("🔗 연결 작업(Mapping) 시작...")
    count_linked = 0
    
    for index, row in df_detail.iterrows():
        try:
            code_raw = row.get(col_detail_code)
            cas_raw = row.get(col_detail_cas)
            
            code = clean_code(code_raw)
            cas = str(cas_raw).strip()

            if pd.isna(cas_raw) or not cas or cas == 'nan' or '***' in cas or cas == '-':
                continue
            
            # [핵심] 이미 등록된 CAS면 건너뜀 (부모에서 이미 등록했거나, 자식 내 중복인 경우)
            if cas in registered_cas_set:
                continue

            if code in rule_dict:
                rule_info = rule_dict[code]
                
                ChemicalRegulation.objects.create(
                    cas_no=cas, 
                    name_korean=rule_info['name_hint'], 
                    limit_concentration=rule_info['limit'], 
                    regulation_type='금지물질',
                    regulation_details=rule_info['detail']
                )
                registered_cas_set.add(cas) # 명단에 추가
                count_linked += 1

        except Exception:
            continue

    total = count_main_cas + count_linked
    print(f"🎉 통합 업로드 완료! 총 {total}개의 금지물질 데이터가 등록되었습니다.")

if __name__ == "__main__":
    run_upload()