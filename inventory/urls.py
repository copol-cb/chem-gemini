from django.urls import path
from . import views


urlpatterns = [
    # 메인 주소 (접속 시 리스트 화면으로 이동 -> 권한 없으면 로그인창 뜸)
    path('', views.inventory_list, name='inventory_list'),
    
    # 작업자용 등록 페이지
    path('add/', views.inventory_add, name='inventory_add'),
    
    # 관리대장 조회 페이지
    path('list/', views.inventory_list, name='inventory_list'),

    # 접속 코드 입력 (문지기) 페이지
    path('access/', views.inventory_access, name='inventory_access'),

    # 로그아웃 기능
    path('logout/', views.inventory_logout, name='inventory_logout'),
    
    # [NEW] 삭제 기능 URL 추가
    path('delete/<int:pk>/', views.inventory_delete, name='inventory_delete'),
    
    path('delete/<int:pk>/', views.inventory_delete, name='inventory_delete'), # 기존 단건 삭제
    path('delete-bulk/', views.inventory_delete_bulk, name='inventory_delete_bulk'), # [NEW] 일괄 삭제
    path('delete-bulk/', views.inventory_delete_bulk, name='inventory_delete_bulk'),
    path('restore-bulk/', views.inventory_restore_bulk, name='inventory_restore_bulk'), # [NEW] 복구 URL
]