from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import ChemicalRegulation, MyInventory
import json # [NEW] 데이터를 JSON으로 변환하기 위해 필요

# ====================================================
# [설정] 사업장별 접속 코드 (비밀번호)
# ====================================================
SITE_ACCESS_CODES = {
    "ourhome001": "안산공장",
    "ourhome1": "용인1공장",
    "ourhome2": "용인2공장",
    "ourhome48": "제천공장",
    "rngf": "음성공장",
    "ourhome11": "계룡공장",
    "ourhome300": "구미공장",
    "aw9969": "양산공장",
    "ourhome1001": "동서울물류센터",
    "ys21002": "양산2물류센터",
    "yi31003": "용인3물류센터",
    "hn1004": "호남물류센터",
    "jj1005": "제주물류센터",
    "e002463": "MASTER", 
}

def inventory_access(request):
    if request.method == 'POST':
        input_code = request.POST.get('access_code', '').strip()
        if input_code in SITE_ACCESS_CODES:
            matched_site = SITE_ACCESS_CODES[input_code]
            request.session['allowed_site'] = matched_site
            return redirect('inventory_list') 
        else:
            return render(request, 'inventory/access.html', {'error': '코드가 올바르지 않습니다.'})
    return render(request, 'inventory/access.html')

def inventory_logout(request):
    request.session.flush() 
    return redirect('inventory_access') 


# ====================================================
# [헬퍼 함수] 사용시설 보유량(톤) 계산 로직 (핵심!)
# ====================================================
def calculate_usage_ton_process(item_or_val, percent_val=0.0):
    """
    사용시설의 최대보유량(톤)을 계산하는 로직
    - item_or_val: MyInventory 객체(조회 시) 또는 딕셔너리(등록 시)
    - percent_val: 등록 시에는 함량을 별도로 받음
    """
    # 1. 데이터 추출 (객체인지 딕셔너리인지 구분)
    if isinstance(item_or_val, MyInventory):
        u_max = item_or_val.usage_max        # 1회 최대 사용량(kg)
        u_water = item_or_val.water_input    # 물 투입량(kg)
        u_vol = item_or_val.usage_facility_vol # 수조 용량(m3)
        pct = item_or_val.percentage         # 함량(%)
        cas = item_or_val.cas_no             # CAS No.
    else:
        u_max = item_or_val.get('usage_max', 0.0)
        u_water = item_or_val.get('water_input', 0.0)
        u_vol = item_or_val.get('usage_facility_vol', 0.0)
        cas = item_or_val.get('cas_no', '')
        pct = percent_val

    # -----------------------------------------------------------
    # [Case 2] 희석 사용 (물 투입량 > 0 그리고 수조 용량 > 0)
    # -----------------------------------------------------------
    if u_water > 0 and u_vol > 0:
        # 1. 희석 후 농도 계산
        # 공식: (사용량 * 원액함량) / (사용량 + 물량)
        total_diluted_weight = u_max + u_water
        if total_diluted_weight == 0:
            return 0.0
            
        final_percent = (u_max * pct) / total_diluted_weight
        
        # 2. 규제 여부 확인 (DB 조회)
        reg_candidates = ChemicalRegulation.objects.filter(cas_no=cas)
        is_regulated_concentration = False
        
        for reg in reg_candidates:
            # 희석된 농도가 규제 기준 이상인지 확인
            if final_percent >= reg.limit_concentration:
                is_regulated_concentration = True
                break
        
        # 3. 판정 결과에 따른 보유량 산정
        if is_regulated_concentration:
            # 위험함 -> 수조 용량(m3)을 그대로 톤으로 적용 (A안)
            return u_vol 
        else:
            # 안전함 -> 보유량 0으로 간주
            return 0.0

    # -----------------------------------------------------------
    # [Case 1] 희석 아님 (일반 사용)
    # -----------------------------------------------------------
    else:
        # 1회 최대 사용량(kg)을 톤으로 변환
        return u_max / 1000.0


def calculate_total_ton(item):
    """
    [관리대장용] 전체 최대보유량(톤) 합계 계산
    """
    total_ton = 0.0
    
    # 1. 저장시설 (용량m3 * 비중 * 1000 -> kg -> ton) = (용량 * 비중)
    if item.is_storage:
        total_ton += (item.storage_vol * item.specific_gravity)
        
    # 2. 보관시설 (kg -> ton)
    if item.is_keeping:
        total_ton += (item.keeping_max / 1000.0)
        
    # 3. 사용시설 (케이스별 로직 적용)
    if item.is_usage:
        total_ton += calculate_usage_ton_process(item)

    return total_ton


# ====================================================
# [NEW] 대시보드 통계 계산 함수 (새로 추가됨)
# ====================================================
def calculate_dashboard_stats(items):
    # 1. 등록 제품 수
    total_count = items.count()

    # 2. 용도별 구분 (번호로 매칭하여 인식률 높임)
    usage_map = {
        "1": "1. 원료 및 첨가제",
        "2": "2. 공정보조물질",
        "3": "3. 시설/설비 유지보수",
        "4": "4. 시험용 시약",
        "5": "5. 폐수처리약품",
        "6": "6. 보관/저장(운송업/창고업 해당)",
        "7": "7. 기타"
    }
    # 카운트 초기화 (7번은 별도로)
    usage_counts = {label: 0 for label in usage_map.values()}
    usage_counts["8. 기타(미지정)"] = 0

    # 3. 유해화학물질 통계 초기화
    danger_types = ["인체급성", "인체만성", "생태유해", "사고대비", "제한물질", "금지물질"]
    danger_stats = {
        dtype: {"lowest": 0, "report": 0, "permission": 0, "total": 0} 
        for dtype in danger_types
    }
    
    # [전체 아이템 순회하며 통계 집계]
    for item in items:
        # (1) 용도 카운팅 (앞글자 번호로 인식)
        u_pur = str(item.usage_purpose).strip()
        matched_code = u_pur[:1] # 첫 글자 ("1" 등) 추출
        
        if matched_code in usage_map:
            label = usage_map[matched_code]
            usage_counts[label] += 1
        else:
            # 번호가 없거나 7번이면 미지정 처리
            usage_counts["8. 기타(미지정)"] += 1

        # (2) 유해화학물질 카운팅
        result_text = str(item.is_danger_result)
        
        # 안전한 물질은 통계에서 제외
        if "안전" in result_text:
            continue

        for dtype in danger_types:
            # 해당 규제 타입(예: 인체급성)이 결과 텍스트에 포함되어 있으면
            if dtype in result_text:
                danger_stats[dtype]["total"] += 1
                
                # 금지/제한은 합계만 계산하고 상세 구분 생략
                if dtype in ["제한물질", "금지물질"]:
                    continue

                # 상세 구분: 해당 타입이 언급된 문맥에서 허가/신고 찾기
                if "영업허가" in result_text and dtype in result_text:
                    danger_stats[dtype]["permission"] += 1
                elif "영업신고" in result_text and dtype in result_text:
                    danger_stats[dtype]["report"] += 1
                else:
                    danger_stats[dtype]["lowest"] += 1

    return total_count, usage_counts, danger_stats


# ====================================================
# [관리 대장 조회] (페이지네이션 적용됨)
# ====================================================
def inventory_list(request):
    user_site = request.session.get('allowed_site')
    if not user_site:
        return redirect('inventory_access')

    current_mode = request.GET.get('mode', 'active') 

    # 1. 데이터 가져오기
    items = MyInventory.objects.all().order_by('-created_at', 'product_name', 'id')

    if current_mode == 'trash':
        items = items.filter(is_deleted=True)
    else:
        items = items.filter(is_deleted=False)

    # 2. 필터링 (MASTER)
    div_filter = None
    site_filter = None
    if user_site == 'MASTER':
        div_filter = request.GET.get('division')
        site_filter = request.GET.get('site_name')
        if div_filter: items = items.filter(division=div_filter)
        if site_filter: items = items.filter(site_name=site_filter)
        
        context_vars = {
            'is_master': True, 'selected_division': div_filter, 'selected_site': site_filter,
            'current_user_site': user_site, 'current_mode': current_mode
        }
    else:
        items = items.filter(site_name=user_site)
        context_vars = {
            'is_master': False, 'current_user_site': user_site, 'current_mode': current_mode
        }

    # 3. 대시보드 통계 (기존 로직 유지)
    d_total, d_usage, d_danger = calculate_dashboard_stats(items)
    context_vars['dashboard_data'] = {
        'total_count': d_total, 'usage_stats': json.dumps(d_usage), 'danger_stats': d_danger,
    }

    # 4. 데이터 그룹화
    grouped_items = []
    if items.exists():
        first_ton = calculate_total_ton(items[0])
        current_group = {
            'common': items[0], 'components': [items[0]], 'row_span': 1, 'total_ton': first_ton
        }
        for item in items[1:]:
            is_same_info = (
                item.product_name == current_group['common'].product_name and
                item.registrant == current_group['common'].registrant and
                item.site_name == current_group['common'].site_name and
                item.division == current_group['common'].division
            )
            time_diff = abs((item.created_at - current_group['common'].created_at).total_seconds())
            if is_same_info and time_diff < 2.0:
                current_group['components'].append(item)
                current_group['row_span'] += 1
            else:
                grouped_items.append(current_group)
                new_ton = calculate_total_ton(item)
                current_group = {
                    'common': item, 'components': [item], 'row_span': 1, 'total_ton': new_ton 
                }
        grouped_items.append(current_group)

    # ==========================================================
    # [NEW] 페이지네이션 (20개씩 자르기)
    # ==========================================================
    page = request.GET.get('page', '1')  # 페이지 번호 가져오기
    paginator = Paginator(grouped_items, 20) # 20개씩 자르기
    page_obj = paginator.get_page(page)      # 해당 페이지 데이터 가져오기

    context_vars['grouped_items'] = page_obj # 템플릿에는 잘린 데이터만 전달
    # ==========================================================

    return render(request, 'inventory/inventory_list.html', context_vars)


# ====================================================
# [신규 등록]
# ====================================================
def inventory_add(request):
    if request.method == 'POST':
        input_division = request.POST.get('division')
        input_site = request.POST.get('site_name')
        input_registrant = request.POST.get('registrant')
        current_time = timezone.now() 

        index = 0
        while True:
            p_name_key = f'product_name_{index}'
            if p_name_key not in request.POST: break
            
            product_name = request.POST.get(p_name_key)
            state = request.POST.get(f'state_{index}')
            purpose = request.POST.get(f'usage_purpose_{index}')
            detail_input = request.POST.get(f'usage_detail_{index}')
            
            # 시설 정보
            is_storage_chk = request.POST.get(f'is_storage_{index}') == 'on'
            s_loc = request.POST.get(f'storage_loc_{index}')
            try: s_vol = float(request.POST.get(f'storage_vol_{index}'))
            except: s_vol = 0.0
            try: s_sg = float(request.POST.get(f'specific_gravity_{index}'))
            except: s_sg = 0.0

            is_keeping_chk = request.POST.get(f'is_keeping_{index}') == 'on'
            k_loc = request.POST.get(f'keeping_loc_{index}')
            try: k_max = float(request.POST.get(f'keeping_max_{index}'))
            except: k_max = 0.0

            is_usage_chk = request.POST.get(f'is_usage_{index}') == 'on'
            u_loc = request.POST.get(f'usage_loc_{index}')
            try: u_max = float(request.POST.get(f'usage_max_{index}'))
            except: u_max = 0.0
            try: u_water = float(request.POST.get(f'water_input_{index}'))
            except: u_water = 0.0
            try: u_vol = float(request.POST.get(f'usage_facility_vol_{index}'))
            except: u_vol = 0.0

            cas_list = request.POST.getlist(f'cas_no_{index}[]')
            percent_list = request.POST.getlist(f'percentage_{index}[]')

            for i in range(len(cas_list)):
                current_cas = cas_list[i].strip()
                current_percent_str = percent_list[i]
                if not current_cas: continue 

                try: percent_val = float(current_percent_str)
                except: percent_val = 0.0

                # [톤수 계산]
                current_total_ton = 0.0
                if is_storage_chk: current_total_ton += (s_vol * s_sg)
                if is_keeping_chk: current_total_ton += (k_max / 1000.0)
                if is_usage_chk:
                    temp_data = {'usage_max': u_max, 'water_input': u_water, 'usage_facility_vol': u_vol, 'cas_no': current_cas}
                    usage_ton = calculate_usage_ton_process(temp_data, percent_val)
                    current_total_ton += usage_ton
                
                daily_usage_ton = current_total_ton

                # [규제 판정]
                reg_candidates = ChemicalRegulation.objects.filter(cas_no=current_cas)
                msgs_concentration = set()
                msgs_quantity = set()
                is_general_chem = False 
                has_record = reg_candidates.exists()
                
                for reg in reg_candidates:
                    reg_type = str(reg.regulation_type).strip()
                    limit_conc = reg.limit_concentration
                    
                    if '일반화학물질' in reg_type:
                        is_general_chem = True
                        continue

                    # 희석 농도 재계산
                    compare_percent = percent_val
                    if is_usage_chk and u_water > 0 and u_vol > 0:
                         if (u_max + u_water) > 0:
                             compare_percent = (u_max * percent_val) / (u_max + u_water)
                    
                    if compare_percent >= limit_conc:
                        if '금지' in reg_type: 
                             raw = reg.regulation_details if reg.regulation_details else "내용 없음"
                             msgs_concentration.add(f"🚫 금지물질({limit_conc}% 이상)__DETAIL__{raw}")
                        if '제한' in reg_type:
                            raw = reg.regulation_details if reg.regulation_details else "내용 없음"
                            msgs_concentration.add(f"🚫 제한물질({limit_conc}% 이상)__DETAIL__{raw}")
                        if '사고' in reg_type: msgs_concentration.add(f"⚠️ 사고대비({limit_conc}% 이상)")
                        if '급성' in reg_type: msgs_concentration.add(f"☣️ 인체급성({limit_conc}% 이상)")
                        if '만성' in reg_type: msgs_concentration.add(f"☣️ 인체만성({limit_conc}% 이상)")
                        if '생태' in reg_type: msgs_concentration.add(f"☣️ 생태유해({limit_conc}% 이상)")
                        # [추가] 금지/제한 물질은 수량과 상관없이 메시지 추가
                        if '금지' in reg_type:
                            msgs_quantity.add("🚫 취급 금지 대상 (수량 무관)")
                        if '제한' in reg_type:
                            msgs_quantity.add("🚫 용도 제한 대상 (수량 무관)")
                        if not any(k in reg_type for k in ['금지','제한','사고','급성','만성','생태']):
                             msgs_concentration.add(f"⚠️ {reg_type}({limit_conc}% 이상)")

                        # [메시지 2] 취급량 규제 판정
                        if any(k in reg_type for k in ['사고', '급성', '만성', '생태']):
                            qty_lowest = reg.limit_qty_lowest if reg.limit_qty_lowest else 0.0
                            qty_lower = reg.limit_qty_lower if reg.limit_qty_lower else 0.0
                            
                            # 기준 정보가 아예 없으면 넘어감
                            if qty_lowest == 0 and qty_lower == 0:
                                pass 
                            else:
                                short_type_name = reg_type
                                if '사고' in reg_type: short_type_name = "사고대비"
                                elif '급성' in reg_type: short_type_name = "인체급성"
                                elif '만성' in reg_type: short_type_name = "인체만성"
                                elif '생태' in reg_type: short_type_name = "생태유해"

                                if daily_usage_ton >= qty_lower:
                                    msgs_quantity.add(f"⚠️ {short_type_name}(영업허가 대상)")
                                elif daily_usage_ton >= qty_lowest:
                                    msgs_quantity.add(f"⚠️ {short_type_name}(영업신고 대상)")
                                else:
                                    # [NEW] 여기가 핵심입니다! (기준 미만일 때 명확한 메시지 추가)
                                    msgs_quantity.add(f"✅ {short_type_name}(규정수량 미만)")

                final_parts = []
                if msgs_concentration:
                    reasons = " /// ".join(sorted(list(msgs_concentration)))
                    final_parts.append(f"규제 기준농도 [{reasons}]")
                if msgs_quantity:
                    reasons = " /// ".join(sorted(list(msgs_quantity)))
                    final_parts.append(f"규제 판정: [{reasons}]")

                if final_parts: is_danger_result = "__BcSplit__".join(final_parts)
                elif is_general_chem: is_danger_result = "✅ 안전 (해당없음)"
                elif has_record: is_danger_result = "✅ 안전 (규제미만)"
                else: is_danger_result = "✅ 안전 (정보없음)"

                official_name = ""
                found_chems = ChemicalRegulation.objects.filter(cas_no=current_cas)
                candidate_names = [c.name_korean.split('[')[0].strip() for c in found_chems if c.name_korean]
                if candidate_names: official_name = min(candidate_names, key=len)

                MyInventory.objects.create(
                    division=input_division, site_name=input_site, registrant=input_registrant,
                    product_name=product_name, cas_no=current_cas, chemical_name=official_name,
                    percentage=percent_val, state=state, usage_purpose=purpose, usage_detail=detail_input,
                    is_storage=is_storage_chk, storage_loc=s_loc, storage_vol=s_vol, specific_gravity=s_sg,
                    is_keeping=is_keeping_chk, keeping_loc=k_loc, keeping_max=k_max, 
                    is_usage=is_usage_chk, usage_loc=u_loc, usage_max=u_max, water_input=u_water, usage_facility_vol=u_vol,
                    is_danger_result=is_danger_result, created_at=current_time  
                )
            index += 1
        return redirect('inventory_list')
    return render(request, 'inventory/inventory_add.html')

def inventory_delete(request, pk):
    if request.session.get('allowed_site') != 'MASTER':
        return redirect('inventory_list')
    try:
        target = MyInventory.objects.get(pk=pk)
        MyInventory.objects.filter(
            division=target.division, site_name=target.site_name,
            product_name=target.product_name, registrant=target.registrant,
            created_at=target.created_at
        ).delete()
    except MyInventory.DoesNotExist:
        pass
    return redirect('inventory_list')

# ====================================================
# [일괄 삭제 (Soft Delete)] -> 휴지통 보내기
# ====================================================
def inventory_delete_bulk(request):
    if request.session.get('allowed_site') != 'MASTER':
        return redirect('inventory_list')
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        for pk in selected_ids:
            try:
                target = MyInventory.objects.get(pk=pk)
                MyInventory.objects.filter(
                    division=target.division, site_name=target.site_name,
                    product_name=target.product_name, registrant=target.registrant,
                    created_at=target.created_at
                ).update(is_deleted=True) 
            except MyInventory.DoesNotExist:
                continue
    return redirect('inventory_list')

# ====================================================
# [일괄 복구 (Restore)] -> 휴지통에서 꺼내기
# ====================================================
def inventory_restore_bulk(request):
    if request.session.get('allowed_site') != 'MASTER':
        return redirect('inventory_list')
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        for pk in selected_ids:
            try:
                target = MyInventory.objects.get(pk=pk)
                MyInventory.objects.filter(
                    division=target.division, site_name=target.site_name,
                    product_name=target.product_name, registrant=target.registrant,
                    created_at=target.created_at
                ).update(is_deleted=False)
            except MyInventory.DoesNotExist:
                continue
    return redirect('/list/?mode=trash')