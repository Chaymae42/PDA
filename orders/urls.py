from django.urls import path
from orders import views


urlpatterns = [
    # Commun
    path('<int:pk>/', views.order_detail, name='order-detail'),
    path('<int:pk>/history/', views.order_history_view, name='order-history'),
    path('<int:pk>/status/', views.check_order_status, name='check-order-status'),

    # Vendeur
    path('create/', views.create_order, name='create-order'),
    path('<int:pk>/modify/', views.modify_order, name='modify-order'),
    path('<int:pk>/cancel/', views.cancel_order, name='cancel-order'),
    path('vendeur/history/', views.vendeur_history, name='vendeur-history'),

    # Magasinier
    path('magasinier/list/', views.magasinier_orders, name='magasinier-orders'),
    path('<int:pk>/prepare/', views.start_preparing, name='start-preparing'),
    path('<int:pk>/ready/', views.mark_ready, name='mark-ready'),
    path('deliverers/', views.available_deliverers, name='available-deliverers'),
    path('<int:pk>/assign/', views.assign_deliverer, name='assign-deliverer'),
    path('magasinier/history/', views.magasinier_history, name='magasinier-history'),

    # Livreur
    path('livreur/deliveries/', views.livreur_deliveries, name='livreur-deliveries'),
    path('<int:pk>/deliver/', views.mark_delivered, name='mark-delivered'),
    path('<int:pk>/cancel-delivery/', views.cancel_delivery, name='cancel-delivery'),
    path('livreur/history/', views.livreur_history, name='livreur-history'),
]