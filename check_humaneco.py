import pandas as pd
import re

# 파일 설정
file_name = "human_eco_chem.xlsx"
HEADER_ROW = 2 

def clean_val(text):
    if pd.isna(text) or str(text).strip() == '-' or str(text).strip() == '':
        return None
    try:
        return float(str(text).replace('%', '').strip())
    except:
        return None

def check_skipped_rows():
    print(f"🔎 '{file_name}' 누락 데이터 검증 시작...\n")
    try:
        df = pd.read_excel(file_name, header=HEADER_ROW)
    except Exception as e:
        print("파일 읽기 실패:", e)
        return

    skipped_count = 0
    
    for index, row in df.iterrows():
        # 엑셀 행 번호 (헤더 고려하여 +4 정도 보정)
        excel_row_num = index + 4 
        
        cas_raw = row.iloc[4]
        limit_acute = clean_val(row.iloc[5])
        limit_chronic = clean_val(row.iloc[6])
        limit_eco = clean_val(row.iloc[7])
        
        cas = str(cas_raw).strip()

        # [이유 1] CAS 번호 문제
        if pd.isna(cas_raw) or not cas or cas == 'nan':
            print(f"❌ [행 {excel_row_num}] 제외됨: CAS 번호가 비어있음")
            skipped_count += 1
            continue
            
        if '***' in cas:
            print(f"❌ [행 {excel_row_num}] 제외됨: CAS 번호가 불명확함 ('***') -> {row.iloc[2]}")
            skipped_count += 1
            continue

        # [이유 2] 함량 기준 없음
        valid_limits = []
        if limit_acute is not None: valid_limits.append(limit_acute)
        if limit_chronic is not None: valid_limits.append(limit_chronic)
        if limit_eco is not None: valid_limits.append(limit_eco)

        if not valid_limits:
            print(f"❌ [행 {excel_row_num}] 제외됨: 규제 함량(%) 정보가 모두 없음 ('-') -> {row.iloc[2]} (CAS: {cas})")
            skipped_count += 1
            continue

    print("-" * 30)
    print(f"🧐 검증 결과: 총 {skipped_count}개의 행이 위 사유로 제외되었습니다.")

if __name__ == "__main__":
    check_skipped_rows()