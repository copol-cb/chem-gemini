import pdfplumber
import pandas as pd
import os

# [설정] 변환할 파일 목록
files_to_convert = [
    ("ban_chem.pdf", "ban_chem.xlsx"),      
    ("ban_gc_chem.pdf", "ban_gc_chem.xlsx") 
]

def convert_pdf_to_excel(pdf_file, excel_file):
    print(f"🚀 '{pdf_file}' 변환 시작 (안전 모드)...")
    all_tables = []
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                # 표 추출
                table = page.extract_table()
                
                if table:
                    # [수정 핵심] 헤더(columns=table[0])를 강제로 지정하지 않음!
                    # 그냥 0, 1, 2... 번호로 매겨서 데이터 통째로 가져옴.
                    # 에러 원인(중복 컬럼명)을 원천 차단함.
                    df = pd.DataFrame(table)
                    all_tables.append(df)
                
                if (i+1) % 10 == 0: print(f"   ... {i+1}/{total_pages} 페이지 완료")

        if all_tables:
            final_result = pd.concat(all_tables, ignore_index=True)
            final_result.to_excel(excel_file, index=False, header=False) # 엑셀 저장할 때도 헤더 없이 저장
            print(f"🎉 성공! -> '{excel_file}' 생성됨 ({len(final_result)}행)")
            print("   (참고: 엑셀을 열어서 첫 번째 줄을 정리해주세요!)")
        else:
            print(f"⚠️ 경고: '{pdf_file}'에서 표를 찾지 못했습니다.")

    except FileNotFoundError:
        print(f"❌ 에러: '{pdf_file}' 파일이 폴더에 없습니다.")
    except Exception as e:
        print(f"❌ 에러: {e}")

# 실행 루프
print("=== 금지물질 PDF 변환 작업 시작 ===")
for pdf, xlsx in files_to_convert:
    convert_pdf_to_excel(pdf, xlsx)
    print("-" * 30)