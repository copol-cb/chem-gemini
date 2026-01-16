import os
import django
import pandas as pd

# 1. Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory.models import ChemicalRegulation

# ==========================================
file_name = "normchem.xlsx"
BATCH_SIZE = 5000  
# ==========================================

def truncate_text(text, limit):
    if not text: return ""
    str_text = str(text).strip()
    if len(str_text) > limit:
        return str_text[:limit] + "..."
    return str_text

def run_upload():
    print(f"🚀 진단 모드: '{file_name}' 업로드를 시작합니다...")

    try:
        # 헤더가 있는 0번째 줄을 읽습니다.
        df = pd.read_excel(file_name, header=0)
        print(f"✅ 파일 읽기 성공 (총 {len(df)}행)")
        print(f"🔎 엑셀 헤더 확인: {df.columns.tolist()}") # 여기서 '일반화학물질' 열이 보여야 함
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_name}")
        return

    print("🧹 기존 '일반화학물질' 데이터를 삭제합니다...")
    ChemicalRegulation.objects.filter(regulation_type="일반화학물질").delete()

    print("📚 데이터 변환 중... (로그를 확인하세요!)")

    bulk_list = []
    total_count = 0
    
    # [진단] 처음 5개만 샘플로 로그를 찍어볼 것임
    sample_printed = 0

    for index, row in df.iterrows():
        try:
            # A열(0): CAS
            cas_raw = row.iloc[0]
            if pd.isna(cas_raw) or str(cas_raw).strip() == '': continue
            cas = str(cas_raw).strip()

            # B열(1): 영문, C열(2): 국문
            eng_raw = row.iloc[1] if len(row) > 1 else ""
            kor_raw = row.iloc[2] if len(row) > 2 else ""
            
            # --------------------------------------------------------
            # [중요] D열(3번째 칸) 읽기
            # --------------------------------------------------------
            # 만약 엑셀에 D열이 없다면 강제로 "일반화학물질"이라고 입력
            if len(row) > 3:
                type_raw = str(row.iloc[3]).strip()
            else:
                # D열이 없으면, 이 파일에 있는 건 무조건 일반화학물질로 간주
                type_raw = "일반화학물질"
            
            # 빈칸(nan)이어도 "일반화학물질"로 채움
            if type_raw == 'nan' or type_raw == '':
                type_raw = "일반화학물질"
            # --------------------------------------------------------

            # 이름 결정
            final_name = ""
            if not pd.isna(kor_raw) and str(kor_raw).strip() != 'nan':
                final_name = truncate_text(kor_raw, 30)
            elif not pd.isna(eng_raw) and str(eng_raw).strip() != 'nan':
                final_name = truncate_text(eng_raw, 50)
            else:
                continue

            # [진단 로그] 처음 3개 데이터가 어떻게 들어가는지 출력
            if sample_printed < 3:
                print(f"   👀 [확인] CAS: {cas} | 유형: {type_raw} (이게 '일반화학물질'이어야 함)")
                sample_printed += 1

            reg_obj = ChemicalRegulation(
                cas_no=cas,
                name_korean=final_name,
                limit_concentration=100, 
                regulation_type=type_raw, # 여기서 결정된 값을 저장
                regulation_details='관리대상 아님(Safe)'
            )
            bulk_list.append(reg_obj)
            total_count += 1

            if len(bulk_list) >= BATCH_SIZE:
                ChemicalRegulation.objects.bulk_create(bulk_list)
                print(f"   🚀 {total_count}개 저장 완료...")
                bulk_list = []

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            continue

    if bulk_list:
        ChemicalRegulation.objects.bulk_create(bulk_list)
        print(f"   🚀 나머지 {len(bulk_list)}개 저장 완료!")

    print(f"🎉 최종 완료! 총 {total_count}개 등록됨.")

if __name__ == "__main__":
    run_upload()