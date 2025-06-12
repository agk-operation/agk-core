from django.urls import path
from .views import ItemListView, ItemCreateView, ItemUpdateView


app_name = 'inventory'
urlpatterns = [
    path('', ItemListView.as_view(), name='item-list'),
    path('add/', ItemCreateView.as_view(), name='item-add'),
    path('<int:pk>/edit/', ItemUpdateView.as_view(), name='item-edit'),
]