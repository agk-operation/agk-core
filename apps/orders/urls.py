from django.urls import path
from .views import (
    OrderListView, OrderCreateView, OrderUpdateView,
    OrderBatchListView, OrderBatchCreateView, NewOrderItemsImportView, OrderItemsImportView
)

app_name = 'orders'
urlpatterns = [
    # ORDERS
    path('', OrderListView.as_view(), name='order-list'),
    path('add/', OrderCreateView.as_view(), name='order-add'),
    path('<int:pk>/edit/', OrderUpdateView.as_view(), name='order-edit'),
    path('<int:pk>/items/import/', OrderItemsImportView.as_view(), name='order-item-import'),
    path('items/items/import/new/', NewOrderItemsImportView.as_view(), name='order-item-import-new'),
    # BATCHES
    path('<int:order_pk>/batches/', OrderBatchListView.as_view(), name='batch-list'),
    path('<int:order_pk>/batches/add/', OrderBatchCreateView.as_view(), name='batch-add'),
]
