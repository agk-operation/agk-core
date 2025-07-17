from django.urls import path
from .views import ProformaInvoiceCreateView, ProformaInvoiceDetailView, ProformaInvoiceDeleteView

app_name = 'finance'

urlpatterns = [
    path('order/<int:order_pk>/proforma/create/', ProformaInvoiceCreateView.as_view(), name='proforma-create'),
    path('proforma/<int:pk>/', ProformaInvoiceDetailView.as_view(), name='proforma-detail'),
    path('proforma/<int:pk>/delete/', ProformaInvoiceDeleteView.as_view(), name='proforma-delete'),
]
