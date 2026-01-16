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
file_main = "restrict_chem_result.xlsx"   
file_detail = "restrict_gc_chem.xlsx"  

# [설정] 엑셀 컬럼 이름
col_main_code = "고유번호"
col_main_text = "화학물질의명칭" 
col_main_detail = "제한내용"

col_detail_code = "고유번호"
# [수정] 엑셀이 인식한 대로 띄어쓰기를 없앴습니다!
col_detail_cas = "CASNo." 
# ==========================================

def extract_percentage(text):
    if pd.isna(text): return 0.0
    match = re.search(r'(\d+(\.\d+)?)%', str(text))
    if match:
        return float(match.group(1))
    return 0.0 

def clean_code(code):
    return str(code).replace(' ', '').replace('\n', '').strip()

def run_upload():
    print("🚀 제한물질 통합(Merge) 업로드를 시작합니다...")
    
    try:
        df_main = pd.read_excel(file_main)
        df_detail = pd.read_excel(file_detail)
        
        # 제목줄 공백 청소
        df_main.columns = df_main.columns.str.replace(' ', '').str.replace('\n', '').str.strip()
        df_detail.columns = df_detail.columns.str.replace(' ', '').str.replace('\n', '').str.strip()
        
        # [확인] 상세 파일 컬럼
        print(f"🔎 상세 파일 컬럼 인식 결과: {list(df_detail.columns)}")
        
        # 에러 방지: 컬럼이 있는지 확인
        if col_detail_code not in df_detail.columns:
            print(f"❌ 에러: 상세 파일에서 '{col_detail_code}' 컬럼을 못 찾았습니다!")
            return
        if col_detail_cas not in df_detail.columns:
            print(f"❌ 에러: 상세 파일에서 '{col_detail_cas}' 컬럼을 못 찾았습니다! (현재 인식된 컬럼: {list(df_detail.columns)})")
            return

        # [안전장치] 빈칸 자동 채우기
        df_detail[col_detail_code] = df_detail[col_detail_code].ffill()
        
        print(f"✅ 파일 읽기 성공 (메인: {len(df_main)}행, 상세: {len(df_detail)}행)")

    except FileNotFoundError as e:
        print(f"❌ 엑셀 파일을 찾을 수 없습니다.\n{e}")
        return

    # 기존 데이터 초기화
    print("🧹 기존 제한물질 데이터를 비웁니다...")
    ChemicalRegulation.objects.filter(regulation_type="제한물질").delete()

    # 1. 규제 정보 사전 만들기
    print("📚 규제 정보를 정리하는 중...")
    rule_dict = {}
    for index, row in df_main.iterrows():
        if pd.isna(row[col_main_code]): continue
        code = clean_code(row[col_main_code])
        
        rule_dict[code] = {
            'limit': extract_percentage(row[col_main_text]),
            'detail': str(row[col_main_detail]),
            'name_hint': str(row[col_main_text])[:50]
        }
    
    print(f"   ℹ️ 메인 파일 코드 {len(rule_dict)}개 확보")

    # 2. 상세 목록 연결하기
    print("🔗 연결 작업(Mapping) 시작...")
    count = 0
    
    for index, row in df_detail.iterrows():
        try:
            code_raw = row[col_detail_code]
            cas_raw = row[col_detail_cas] # 여기서 이제 에러 안 날 겁니다!
            
            code = clean_code(code_raw)
            cas = str(cas_raw).strip()

            # 유효성 검사
            if pd.isna(cas_raw) or not cas or cas == 'nan' or '***' in cas or cas == '-':
                continue
            
            if pd.isna(code_raw) or not code or code == 'nan':
                continue

            # 매칭 시도
            if code in rule_dict:
                rule_info = rule_dict[code]
                ChemicalRegulation.objects.create(
                    cas_no=cas, 
                    name_korean=rule_info['name_hint'], 
                    limit_concentration=rule_info['limit'], 
                    regulation_type='제한물질',
                    regulation_details=rule_info['detail']
                )
                count += 1
            else:
                # 매칭 실패 (처음 3개만 출력)
                if count < 3: 
                    print(f"⚠️ 매칭 실패: 코드 '{code}'가 메인파일에 없습니다.")

        except Exception as e:
            print(f"⚠️ {index}행 처리 중 에러: {e}")
            continue

    print("------------------------------------------")
    if count == 0:
        print("❌ 0건 등록됨. 위 로그를 확인해주세요.")
    else:
        print(f"🎉 통합 업로드 완료! 총 {count}개의 제한물질이 등록되었습니다.")

if __name__ == "__main__":
    run_upload()