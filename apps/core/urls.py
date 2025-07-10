from django.urls import path
from . import views


app_name = 'core'
urlpatterns = []


for name in [
    'Company', 'Exporter', 
    'Customer', 'City', 'Port',
    'Province', 'Supplier', 'Currency',
    'SalesRepresentative', 'Project',
]:
    slug = name.lower()
    urlpatterns += [
        path(f'{slug}/create/', getattr(views, f'{name}CreateView').as_view(), name=f'{slug}-create'),
        path(f'{slug}/<int:pk>/edit/', getattr(views, f'{name}UpdateView').as_view(), name=f'{slug}-edit'),
    ]