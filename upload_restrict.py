import os
import django
import pandas as pd
import re # 정규표현식(탐지견) 라이브러리

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import ChemicalRegulation

# ==========================================
# [설정] 파일 이름
excel_filename = "restrict_chem_result.xlsx" 

# 선생님 엑셀 파일의 제목을 여기에 정확히 적어주세요!
col_text_blob = "화학물질의 명칭"   # CAS랑 함량이 섞여있는 그 열
col_details = "제한내용"           # 제한 내용이 적힌 열
# ==========================================

def extract_cas(text):
    """ 텍스트에서 000-00-0 형식의 CAS 번호를 찾아냅니다 """
    # 패턴: 숫자(2개이상)-숫자(2개)-숫자(1개)
    match = re.search(r'(\d{2,7}-\d{2}-\d)', str(text))
    if match:
        return match.group(1)
    return None

def extract_percentage(text):
    """ 텍스트에서 % 앞의 숫자를 찾아냅니다 """
    # 패턴: 숫자(점 포함 가능) 바로 뒤에 %가 오는 경우 (예: 0.1%, 25%)
    match = re.search(r'(\d+(\.\d+)?)%', str(text))
    if match:
        return float(match.group(1))
    return 0.0 # 못 찾으면 0%로 간주 (즉, 함량 상관없이 무조건 제한)

def run_upload():
    print(f"🚀 '{excel_filename}' 파일 분석을 시작합니다...")
    
    try:
        df = pd.read_excel(excel_filename)
        # 제목의 줄바꿈 제거
        df.columns = df.columns.str.replace('\n', '').str.strip()
    except FileNotFoundError:
        print("❌ 엑셀 파일을 찾을 수 없습니다.")
        return

    count = 0
    
    # 기존 '제한물질' 데이터만 싹 지우고 다시 넣기 (사고대비물질은 건드리지 않음!)
    print("🧹 기존 '제한물질' 데이터를 초기화합니다...")
    ChemicalRegulation.objects.filter(regulation_type="제한물질").delete()

    print("🔍 텍스트 마이닝(채굴) 시작...")

    for index, row in df.iterrows():
        try:
            # 1. 섞여있는 텍스트 가져오기
            raw_text = str(row[col_text_blob])
            details_text = str(row[col_details])
            
            # 2. 탐지견 투입! (CAS와 함량 추출)
            extracted_cas = extract_cas(raw_text)
            extracted_limit = extract_percentage(raw_text)

            # CAS 번호를 못 찾았으면 스킵 (가끔 제목 줄이거나 빈 줄일 수 있음)
            if not extracted_cas:
                continue

            # 3. DB에 저장
            ChemicalRegulation.objects.create(
                cas_no=extracted_cas,
                name_korean=raw_text[:100] + "...", # 이름이 너무 기니까 앞부분만 저장
                limit_concentration=extracted_limit,
                regulation_type='제한물질',
                regulation_details=details_text # 상세 내용 저장
            )
            count += 1
                
        except Exception as e:
            print(f"⚠️ {index+2}행 에러: {e}")
            continue

    print("------------------------------------------")
    print(f"🎉 제한물질 업로드 완료! 총 {count}건 저장됨.")
    print("이제 '말라카이트 그린'도 자동으로 탐지합니다.")

if __name__ == "__main__":
    run_upload()