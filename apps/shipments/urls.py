from django.urls import path
from . import views


app_name = 'shipments'
urlpatterns = [
    path('pre/', views.PreShipmentListView.as_view(), name='pre_shipment-list'),
    # criação / edição
    path('pre/add/', views.PreShipmentCreateView.as_view(), name='pre_shipment-add'),
    path('pre/<int:pk>/', views.PreShipmentUpdateView.as_view(), name='pre_shipment-edit'),
    path('pre/<int:pk>/delete/', views.PreShipmentDeleteView.as_view(), name='pre_shipment-delete'),
    # embarque final
    path('final/<int:pk>/', views.FinalShipmentDetailView.as_view(), name='shipment-detail'),
    path('final/<int:pk>/stages/', views.ShipmentUpdateView.as_view(), name='shipment-stages'),
]
