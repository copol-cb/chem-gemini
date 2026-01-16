import pdfplumber
import pandas as pd

# [설정] 파일 이름
pdf_filename = "restrict_gc_chem.pdf"   # 선생님이 준비한 상세 목록 PDF
excel_filename = "restrict_gc_chem.xlsx"

print(f"🚀 '{pdf_filename}' 파일 추출 시작...")
all_tables = []

try:
    with pdfplumber.open(pdf_filename) as pdf:
        for i, page in enumerate(pdf.pages):
            # extract_table 옵션을 써서 선이 있는 표를 잘 인식하게 함
            table = page.extract_table()
            
            if table:
                # 첫 번째 줄을 제목으로, 나머지를 데이터로
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)
                print(f"{i+1} 페이지 완료")

    if all_tables:
        final_result = pd.concat(all_tables, ignore_index=True)
        # 엑셀 저장
        final_result.to_excel(excel_filename, index=False)
        print(f"🎉 성공! '{excel_filename}' 생성 완료.")
        print("엑셀을 열어서 '고유번호'와 'CAS No.' 열 이름이 맞는지 확인해주세요.")
    else:
        print("❌ 표를 못 찾았습니다.")

except Exception as e:
    print(f"❌ 에러: {e}")