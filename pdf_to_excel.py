import pdfplumber
import pandas as pd

# ==========================================
# [중요] 여기에 선생님의 PDF 파일 이름을 정확히 적어주세요!
# 파일이 같은 폴더 안에 있어야 합니다.
pdf_filename = "accident_chem.pdf"  
excel_filename = "accident_chem_result.xlsx"
# ==========================================

print("작업을 시작합니다... (잠시만 기다려주세요)")

# 데이터를 담을 빈 바구니
all_tables = []

try:
    # PDF 파일 열기
    with pdfplumber.open(pdf_filename) as pdf:
        # 모든 페이지를 한 장씩 넘기면서 확인
        for i, page in enumerate(pdf.pages):
            # 페이지에서 표(Table) 추출하기
            table = page.extract_table()
            
            if table:
                # 표가 있으면 데이터프레임으로 변환해서 담기
                # 첫 줄(table[0])은 제목, 나머지(table[1:])는 내용
                df = pd.DataFrame(table[1:], columns=table[0]) 
                all_tables.append(df)
                print(f"{i+1} 페이지에서 표를 찾았습니다.")
            else:
                print(f"{i+1} 페이지: 표가 없어서 넘어갑니다.")

    # 바구니에 담긴 표가 있으면 하나로 합치기
    if all_tables:
        final_result = pd.concat(all_tables, ignore_index=True)
        final_result.to_excel(excel_filename, index=False)
        print("------------------------------------------")
        print(f"🎉 성공! '{excel_filename}' 파일이 만들어졌습니다.")
        print("왼쪽 파일 목록에서 엑셀 파일을 열어보세요.")
    else:
        print("PDF를 다 뒤졌는데 표를 못 찾았습니다. PDF가 이미지로 되어있나요?")

except FileNotFoundError:
    print(f"❌ 에러: '{pdf_filename}' 파일을 못 찾겠어요. 파일 이름이 맞는지 확인해주세요.")
except Exception as e:
    print(f"❌ 알 수 없는 에러 발생: {e}")