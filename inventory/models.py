from django.db import models

# ==========================================================
# [1] 규제 정보 모델 (기존 유지)
# ==========================================================
class ChemicalRegulation(models.Model):
    cas_no = models.CharField(max_length=50, verbose_name="CAS No.")
    name_korean = models.CharField(max_length=500, verbose_name="화학물질명") 
    limit_concentration = models.FloatField(default=0.0, verbose_name="규제 기준 농도(%)")
    regulation_type = models.CharField(max_length=100, default="유해화학물질", verbose_name="규제 유형")
    
    # 제한 내용 (예: 페인트 용도 금지 등)
    regulation_details = models.TextField(blank=True, verbose_name="상세 규제 내용") 
    
    # 3단계 규정수량 필드 (단위: 톤)
    limit_qty_lowest = models.FloatField(default=0.0, null=True, blank=True, verbose_name="최하위 규정수량(톤)")
    limit_qty_lower = models.FloatField(default=0.0, null=True, blank=True, verbose_name="하위 규정수량(톤)")
    limit_qty_upper = models.FloatField(default=0.0, null=True, blank=True, verbose_name="상위 규정수량(톤)")

    def __str__(self):
        return f"[{self.regulation_type}] {self.name_korean} ({self.cas_no})"


# ==========================================================
# [2] 사용자 인벤토리 모델 (전면 개편)
# ==========================================================
class MyInventory(models.Model):
    # --- [1. 사업장 및 등록 정보] ---
    DIV_CHOICES = [('제조본부', '제조본부'), ('물류본부', '물류본부')]
    division = models.CharField(max_length=20, choices=DIV_CHOICES, default='제조본부', verbose_name="사업부")
    site_name = models.CharField(max_length=50, blank=True, verbose_name="사업장")
    registrant = models.CharField(max_length=50, blank=True, verbose_name="등록자")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일")

    # --- [2. 제품 및 성분 기본 정보] ---
    product_name = models.CharField(max_length=200, verbose_name="제품명")
    cas_no = models.CharField(max_length=50, verbose_name="제품 내 CAS No.")
    chemical_name = models.CharField(max_length=200, blank=True, verbose_name="화학물질명") 
    percentage = models.FloatField(verbose_name="제품 내 함량(%)")
    
    # 성상
    STATE_CHOICES = [
        ('액체', '액체'), 
        ('고체', '고체'), 
        ('기체', '기체'), 
        ('반고체', '반고체')
    ]
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default='액체', verbose_name="성상")
    
    # 용도
    usage_purpose = models.CharField(max_length=200, blank=True, verbose_name="사용용도")
    usage_detail = models.CharField(max_length=200, null=True, blank=True, verbose_name="용도상세(기타)")

    # --- [3. 시설 상세 정보 (NEW Structure)] ---
    
    # (1) 저장시설
    is_storage = models.BooleanField(default=False, verbose_name="저장시설_체크")
    storage_loc = models.CharField(max_length=100, null=True, blank=True, verbose_name="저장시설_위치")
    storage_vol = models.FloatField(default=0.0, verbose_name="저장시설_용량(m3)")
    specific_gravity = models.FloatField(default=0.0, verbose_name="비중")

    # (2) 보관시설
    is_keeping = models.BooleanField(default=False, verbose_name="보관시설_체크")
    keeping_loc = models.CharField(max_length=100, null=True, blank=True, verbose_name="보관시설_위치")
    keeping_max = models.FloatField(default=0.0, verbose_name="최대_보관량(kg)")

    # (3) 사용시설
    is_usage = models.BooleanField(default=False, verbose_name="사용시설_체크")
    usage_loc = models.CharField(max_length=100, null=True, blank=True, verbose_name="사용시설_위치")
    usage_max = models.FloatField(default=0.0, verbose_name="1회_최대_사용량(kg)")
    water_input = models.FloatField(default=0.0, verbose_name="물_투입량(kg)")
    usage_facility_vol = models.FloatField(default=0.0, verbose_name="사용시설_용량(m3)")

    # --- [4. 결과 판정] ---
    is_danger_result = models.CharField(max_length=500, default="판정대기", verbose_name="규제판정결과")
    
    # [NEW] 삭제 여부 (True면 휴지통에 있는 상태)
    is_deleted = models.BooleanField(default=False, verbose_name="삭제여부")

    def __str__(self):
        return f"[{self.division}/{self.site_name}] {self.product_name}"