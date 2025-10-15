from django.urls import path
from . import views


app_name = 'shipments'
urlpatterns = [
    path('pre/', views.PreShipmentListView.as_view(), name='pre_shipment-list'),
    # criação / edição
    path('pre/add/', views.PreShipmentCreateView.as_view(), name='pre_shipment-add'),
    path('pre/<int:pk>/', views.PreShipmentUpdateView.as_view(), name='pre_shipment-edit'),
    path('pre/<int:pk>/delete/', views.PreShipmentDeleteView.as_view(), name='pre_shipment-delete'),
    path('ready/<int:pk>/confirmation/', views.ShipmentReadyConfirmationView.as_view(), name='shipment-ready-confirmation'),
    # embarque final
    path('final/', views.ShipmentListView.as_view(), name='shipment-list'),
    path('final/<int:pk>/', views.ShipmentUpdateView.as_view(), name='shipment-stages'),
]
