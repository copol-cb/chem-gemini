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
file_name = "human_eco_chem.xlsx"
HEADER_ROW = 2 
# ==========================================

def clean_val(text):
    """ 함량 수치 정제 """
    if pd.isna(text) or str(text).strip() == '-' or str(text).strip() == '':
        return None
    try:
        return float(str(text).replace('%', '').strip())
    except:
        return None

def split_cas_numbers(cas_text):
    """ CAS 번호 분리 (쉼표, 줄바꿈, 공백 기준) """
    if pd.isna(cas_text): return []
    text = str(cas_text).strip()
    if not text or text == 'nan' or '***' in text: return []
    parts = re.split(r'[,\n\s]+', text)
    valid_cas = [p.strip() for p in parts if p.strip() and p.strip() != '-']
    return valid_cas

def run_upload():
    print(f"🚀 '{file_name}' 업로드를 시작합니다 (유해성 유형별 개별 분리 버전)...")

    try:
        df = pd.read_excel(file_name, header=HEADER_ROW)
        
        # [1] 병합된 셀 채우기 (ffill)
        cols_to_fill = [5, 6, 7, 8] 
        df.iloc[:, cols_to_fill] = df.iloc[:, cols_to_fill].ffill()
        
        print(f"✅ 파일 읽기 성공")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_name}")
        return

    # 초기화
    print("🧹 기존 '인체등유해성물질' 데이터를 비웁니다...")
    # 주의: 기존에 뭉뚱그려 저장했던 데이터들을 삭제
    ChemicalRegulation.objects.filter(regulation_type__in=["인체등유해성물질", "인체급성유해성물질", "인체만성유해성물질", "생태유해성물질"]).delete()

    count = 0
    print("📚 데이터 분석 및 저장 중...")
    
    for index, row in df.iterrows():
        try:
            name_kr = str(row.iloc[2]).strip()  # C열: 국문명
            cas_raw = row.iloc[4]               # E열: CAS No.
            type_info = str(row.iloc[8]).strip() # I열: 참고용 유형

            # 삭제된 물질 필터링
            if "삭제" in type_info or "삭제" in name_kr:
                continue
            
            # 함량 정보 읽기
            limit_acute = clean_val(row.iloc[5])   
            limit_chronic = clean_val(row.iloc[6]) 
            limit_eco = clean_val(row.iloc[7])     
            
            # CAS 번호 쪼개기
            cas_list = split_cas_numbers(cas_raw)
            if not cas_list: continue

            # [핵심 변경] 각 기준이 존재하면 별도의 데이터로 저장합니다.
            
            # 1. 인체급성 저장
            if limit_acute is not None:
                for cas in cas_list:
                    ChemicalRegulation.objects.create(
                        cas_no=cas,
                        name_korean=name_kr,
                        limit_concentration=limit_acute,
                        regulation_type='인체급성유해성물질', # 구체적 타입 명시
                        regulation_details=f"인체급성({limit_acute}% 이상)"
                    )
                    count += 1
            
            # 2. 인체만성 저장
            if limit_chronic is not None:
                for cas in cas_list:
                    ChemicalRegulation.objects.create(
                        cas_no=cas,
                        name_korean=name_kr,
                        limit_concentration=limit_chronic,
                        regulation_type='인체만성유해성물질', # 구체적 타입 명시
                        regulation_details=f"인체만성({limit_chronic}% 이상)"
                    )
                    count += 1

            # 3. 생태유해성 저장
            if limit_eco is not None:
                for cas in cas_list:
                    ChemicalRegulation.objects.create(
                        cas_no=cas,
                        name_korean=name_kr,
                        limit_concentration=limit_eco,
                        regulation_type='생태유해성물질', # 구체적 타입 명시
                        regulation_details=f"생태유해성({limit_eco}% 이상)"
                    )
                    count += 1

        except Exception as e:
            continue

    print("-" * 30)
    print(f"🎉 업로드 완료! 총 {count}개의 세부 유해성 데이터가 생성되었습니다.")

if __name__ == "__main__":
    run_upload()