from django.urls import path
from . import views
import re


app_name = 'inventory'
urlpatterns = [
    path('item/list/', views.ItemListView.as_view(), name='item-list'),
    path('item/create/', views.ItemCreateUpdateView.as_view(), name='item-create'),
    path('item/<int:pk>/edit/', views.ItemCreateUpdateView.as_view(), name='item-edit'),
    path('item/<int:pk>/delete/', views.ItemDeleteView.as_view(), name='item-delete'),
    path('item/<int:pk>/packaging/', views.ItemPackagingUpdateView.as_view(), name='item-packaging'),
    path('api/populate-defaults/', views.PopulateDefaultsView.as_view(), name='populate-defaults'),
]

for name in [
    'Category', 'Subcategory', 'Project', 
    'SupplierChain', 'Chain', 'Ncm',
    'BrandManufacturer', 'ModelApplication', 'Currency',
    'Group', 'Version', 'Supplier',
]:
    slug = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    urlpatterns += [
        path(f'{slug}/create/', getattr(views, f'{name}CreateView').as_view(), name=f'{slug}-create'),
        path(f'{slug}/<int:pk>/edit/', getattr(views, f'{name}UpdateView').as_view(), name=f'{slug}-edit'),
    ]
