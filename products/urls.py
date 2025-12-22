from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_products, name='list-products'),
    path('search/', views.search_products, name='search-products'),
    path('add-name/', views.add_product_name, name='add-product-name'),
    path('<int:pk>/validate/', views.validate_product, name='validate-product'),
    path('<int:pk>/update/', views.update_product, name='update-product'),
    path('<int:pk>/delete/', views.delete_product, name='delete-product'),
    path('import/', views.import_products_excel, name='import-products'),
]