from django.urls import path
from . import views

app_name = 'orders'
urlpatterns = [
    # ORDERS
    path('', views.OrderListView.as_view(), name='order-list'),
    path('add/', views.OrderCreateView.as_view(), name='order-add'),
    path('<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order-edit'),
    path('<int:pk>/items/import/', views.OrderItemsImportView.as_view(), name='order-item-import'),
    path('items/import/new/', views.NewOrderItemsImportView.as_view(), name='order-item-import-new'),
    path('<int:pk>/update-margins/', views.UpdateOrderMarginsView.as_view(), name='order-update-margins'),
    # BATCHES
    path('batches/', views.AllBatchListView.as_view(), name='batch-list'),
    path('<int:order_pk>/batches/add/', views.OrderBatchCreateView.as_view(), name='batch-add'),
    path('<int:order_pk>/batches/', views.OrderBatchListView.as_view(), name='order-batch-list'),
    path('<int:order_pk>/batches/<int:pk>/', views.OrderBatchDetailView.as_view(), name='batch-detail'),
]
                                                                                                                                            