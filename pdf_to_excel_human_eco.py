import pdfplumber
import pandas as pd
import re

# ==============================================================
# [설정] 파일 이름
pdf_file = "human_eco_chem(kg).pdf"
excel_file = "human_eco_qty.xlsx"
# ==============================================================

def clean_text(text):
    """ 줄바꿈, 불필요한 공백 제거 """
    if text is None: return ""
    return str(text).replace('\n', ' ').strip()

def run_conversion():
    print(f"🚀 '{pdf_file}' 변환을 시작합니다...")
    
    all_rows = []

    # 1. PDF 파일 열기
    try:
        with pdfplumber.open(pdf_file) as pdf:
            print(f"📄 총 {len(pdf.pages)}페이지를 발견했습니다.")
            
            for i, page in enumerate(pdf.pages):
                # 테이블 추출
                tables = page.extract_tables()
                
                for table in tables:
                    # 앞쪽의 병합된 셀(이름, CAS 등) 값을 기억할 변수들
                    last_name = ""
                    last_cas = ""
                    
                    for row in table:
                        # 엑셀 헤더(제목) 줄은 건너뛰기
                        if row[0] == "연번" or "규정수량" in str(row[6]):
                            continue
                        
                        # 데이터 정제 (각 열의 위치는 PDF 표 구조에 맞춤)
                        # 보통: 0:연번, 1:고유번호, 2:화학물질명, 3:CAS번호, 4:구분, 5:함량, 6:최하위, 7:하위, 8:상위
                        
                        # [핵심 로직 1] 병합된 셀 처리 (비어있으면 윗줄 값 사용)
                        # 이름(2번열)
                        current_name = clean_text(row[2])
                        if current_name:
                            last_name = current_name
                        else:
                            current_name = last_name # 윗줄 값 복사

                        # CAS번호(3번열)
                        current_cas_raw = clean_text(row[3])
                        if current_cas_raw:
                            last_cas = current_cas_raw
                        else:
                            current_cas_raw = last_cas # 윗줄 값 복사

                        # 구분(4번열) - 이게 비어있으면 데이터 행이 아님 (무시)
                        raw_type = clean_text(row[4])
                        if not raw_type:
                            continue

                        # 나머지 수치 데이터
                        limit_val = clean_text(row[5])
                        qty_lowest = clean_text(row[6])
                        qty_lower = clean_text(row[7])
                        qty_upper = clean_text(row[8])

                        # [핵심 로직 2] CAS 번호 쪼개기 (쉼표, 줄바꿈 등)
                        # 예: "51-75-2, 55-86-7" -> ["51-75-2", "55-86-7"]
                        # 정규식을 써서 숫자-숫자-숫자 패턴이 아니면 구분자로 봅니다.
                        cas_list = [c.strip() for c in re.split(r'[,\n\s]+', current_cas_raw) if c.strip()]
                        
                        if not cas_list:
                            cas_list = [""] # 없으면 빈칸으로라도

                        for single_cas in cas_list:
                            # 엑셀에 들어갈 한 줄 생성
                            new_row = {
                                "CAS번호": single_cas,
                                "화학물질명": current_name,
                                "구분": raw_type,
                                "함량기준": limit_val,
                                "최하위(톤)": qty_lowest,
                                "하위(톤)": qty_lower,
                                "상위(톤)": qty_upper
                            }
                            all_rows.append(new_row)
                
                if (i+1) % 10 == 0:
                    print(f"   ... {i+1} 페이지 처리 중")

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_file}")
        return

    # 2. 엑셀로 저장
    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_excel(excel_file, index=False)
        print("-" * 40)
        print(f"🎉 변환 완료! '{excel_file}' 파일이 생성되었습니다.")
        print(f"📊 총 {len(df)}개의 데이터 행이 추출되었습니다.")
    else:
        print("⚠️ 추출된 데이터가 없습니다. PDF 표 형식을 확인해주세요.")

if __name__ == "__main__":
    run_conversion()