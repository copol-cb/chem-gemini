import os
import django
import pandas as pd

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import ChemicalRegulation

# ==============================================================
# [설정] 엑셀 파일 및 컬럼명 설정
excel_filename = "accident_chem_result.xlsx" 

col_name = "사고대비물질명"
col_cas = "CAS번호"
col_limit = "함량기준(% 이상)"

# [NEW] 3단계 규정수량 컬럼명 (엑셀 파일과 똑같아야 합니다!)
col_qty_lowest = "최하위규정수량(톤)"
col_qty_lower = "하위 규정수량(톤)"
col_qty_upper = "상위 규정수량(톤)"
# ==============================================================

def clean_float(value):
    """ 엑셀에서 읽은 지저분한 숫자(문자 섞임)를 깨끗한 실수(float)로 변환 """
    if pd.isna(value): return 0.0
    s_val = str(value).replace(",", "").replace("톤", "").replace("kg", "").replace(">", "").replace("=", "").strip()
    if not s_val or s_val == "nan": return 0.0
    try:
        return float(s_val)
    except ValueError:
        return 0.0

def run_upload():
    print(f"🚀 '{excel_filename}' (3단계 규정수량) 업로드를 시작합니다...")
    
    try:
        df = pd.read_excel(excel_filename)
        # 컬럼 제목 청소 (줄바꿈 제거)
        df.columns = df.columns.str.replace('\n', '').str.strip() 
        print(f"✅ 파일 읽기 성공 (총 {len(df)}행)")
        print(f"🔎 컬럼 확인: {df.columns.tolist()}")

        # [필수 체크] 컬럼이 진짜 있는지 확인
        required_cols = [col_qty_lowest, col_qty_lower, col_qty_upper]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"⚠️ 경고: 엑셀에 다음 컬럼이 없습니다 -> {missing}")
            print("   (엑셀 파일의 첫 줄 제목을 확인해주세요!)")
            # 강제 중단하지 않고 진행하되, 없는 컬럼은 0으로 처리됨
            
    except FileNotFoundError:
        print("❌ 파일을 못 찾았어요.")
        return

    count = 0
    
    # [중요] '사고대비물질' 데이터만 초기화
    print("🧹 기존 '사고대비물질' 데이터를 비웁니다...")
    ChemicalRegulation.objects.filter(regulation_type='사고대비물질').delete()

    print("📚 데이터 변환 및 저장 중...")

    for index, row in df.iterrows():
        try:
            if pd.isna(row[col_cas]) or pd.isna(row[col_name]):
                continue

            cas = str(row[col_cas]).strip()
            name = str(row[col_name]).strip()
            
            # 1. 함량 기준
            limit_val = clean_float(row.get(col_limit))

            # 2. [NEW] 3단계 규정수량 읽기
            val_lowest = clean_float(row.get(col_qty_lowest)) # 최하위
            val_lower = clean_float(row.get(col_qty_lower))   # 하위
            val_upper = clean_float(row.get(col_qty_upper))   # 상위

            # DB 저장
            ChemicalRegulation.objects.create(
                cas_no=cas,
                name_korean=name,
                limit_concentration=limit_val,
                regulation_type='사고대비물질',
                
                # 새로 만든 3개 칸에 저장
                limit_qty_lowest=val_lowest,
                limit_qty_lower=val_lower,
                limit_qty_upper=val_upper
            )
            count += 1
                
        except Exception as e:
            print(f"⚠️ {index+2}행 에러: {e}")
            continue

    print("-" * 40)
    print(f"🎉 사고대비물질 {count}개 업로드 완료!")
    print("이제 DB에 '최하위/하위/상위' 기준값이 모두 들어갔습니다.")

if __name__ == "__main__":
    run_upload()