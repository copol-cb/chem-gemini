import pdfplumber
import pandas as pd

# ==========================================
# [설정] 파일 이름 설정
pdf_filename = "restrict_chem.pdf"  # 선생님이 넣어둔 파일명
excel_filename = "restrict_chem_result.xlsx" # 만들어질 엑셀 파일명
# ==========================================

print(f"🚀 '{pdf_filename}' 파일에서 표를 추출합니다...")

all_tables = []

try:
    with pdfplumber.open(pdf_filename) as pdf:
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            
            if table:
                # 데이터프레임으로 변환
                df = pd.DataFrame(table[1:], columns=table[0]) 
                all_tables.append(df)
                print(f"{i+1} 페이지 추출 완료")
            else:
                print(f"{i+1} 페이지: 표 없음 (Pass)")

    if all_tables:
        final_result = pd.concat(all_tables, ignore_index=True)
        final_result.to_excel(excel_filename, index=False)
        print("------------------------------------------")
        print(f"🎉 성공! '{excel_filename}' 파일이 생성되었습니다.")
    else:
        print("❌ 표를 하나도 못 찾았습니다. PDF가 이미지(스캔본)인지 확인해주세요.")

except FileNotFoundError:
    print(f"❌ 에러: '{pdf_filename}' 파일이 폴더에 없습니다.")
except Exception as e:
    print(f"❌ 에러 발생: {e}")