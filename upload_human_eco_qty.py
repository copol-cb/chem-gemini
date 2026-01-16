import os
import django
import pandas as pd

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import ChemicalRegulation

# ==============================================================
# [설정] 파일 이름 (선생님이 만드신 파일명)
excel_filename = "human_eco_qty.xlsx" 

# [설정] 엑셀 컬럼 이름
COL_CAS = "CAS번호"
COL_NAME = "화학물질명"
COL_TYPE = "구분"       # 급성, 만성, 생태
COL_LIMIT = "함량기준"   # %
COL_LOWEST = "최하위(톤)"
COL_LOWER = "하위(톤)"
COL_UPPER = "상위(톤)"
# ==============================================================

def clean_float(value):
    """ 숫자만 깔끔하게 추출 """
    if pd.isna(value): return 0.0
    s_val = str(value).replace(",", "").replace("톤", "").replace("kg", "").replace("-", "").strip()
    if not s_val or s_val.lower() == "nan": return 0.0
    try:
        return float(s_val)
    except ValueError:
        return 0.0

def get_full_reg_type(short_type):
    """ '급성' -> '인체급성유해성물질' 로 변환 """
    key = str(short_type).strip()
    if "급성" in key: return "인체급성유해성물질"
    if "만성" in key: return "인체만성유해성물질"
    if "생태" in key: return "생태유해성물질"
    return None

def run_upload():
    print(f"🚀 '{excel_filename}' (인체/생태 규정수량) 업로드를 시작합니다...")
    
    try:
        df = pd.read_excel(excel_filename)
        # 컬럼 공백 제거
        df.columns = df.columns.str.replace('\n', '').str.strip()
        print(f"✅ 파일 읽기 성공! (총 {len(df)}행)")
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {excel_filename}")
        return

    # [초기화] 기존 인체/생태 데이터 삭제 (중복 방지)
    # 사고대비물질은 건드리지 않고, 인체/생태만 지우고 다시 넣습니다.
    print("🧹 기존 인체/생태 유해성 데이터를 초기화합니다...")
    target_types = ["인체급성유해성물질", "인체만성유해성물질", "생태유해성물질"]
    ChemicalRegulation.objects.filter(regulation_type__in=target_types).delete()

    count = 0
    
    for index, row in df.iterrows():
        try:
            raw_cas = row.get(COL_CAS)
            raw_name = row.get(COL_NAME)
            raw_type = row.get(COL_TYPE)

            if pd.isna(raw_cas) or pd.isna(raw_name) or pd.isna(raw_type):
                continue

            # 규제 유형 변환
            reg_type_full = get_full_reg_type(raw_type)
            if not reg_type_full:
                continue

            # 수치 데이터 정리
            limit_val = clean_float(row.get(COL_LIMIT))
            qty_lowest = clean_float(row.get(COL_LOWEST))
            qty_lower = clean_float(row.get(COL_LOWER))
            qty_upper = clean_float(row.get(COL_UPPER))

            # 이미 엑셀 변환 단계에서 CAS 분리를 했으므로, 바로 저장하면 됩니다.
            clean_cas = str(raw_cas).strip()

            ChemicalRegulation.objects.create(
                cas_no=clean_cas,
                name_korean=str(raw_name).strip(),
                limit_concentration=limit_val,
                regulation_type=reg_type_full, 
                
                # 3단계 규정수량 저장
                limit_qty_lowest=qty_lowest,
                limit_qty_lower=qty_lower,
                limit_qty_upper=qty_upper
            )
            count += 1

        except Exception as e:
            print(f"❌ {index+2}행 에러 발생: {e}")
            continue

    print("-" * 40)
    print(f"🎉 업로드 완료! 총 {count}개의 인체/생태 데이터가 저장되었습니다.")

if __name__ == "__main__":
    run_upload()