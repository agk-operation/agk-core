from django.urls import path
from . import views


app_name = 'pricing'
urlpatterns = [
    path('margins/', views.MarginListView.as_view(), name='margin-list'),
    path('margins/add/',views.MarginCreateView.as_view(), name='margin-add'),
    path('margins/<int:pk>/edit/',views.MarginUpdateView.as_view(), name='margin-edit'),
    path('margins/<int:pk>/delete/', views.MarginDeleteView.as_view(), name='margin-delete'),
]
