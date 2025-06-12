from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Item
from django.urls import reverse_lazy


class ItemListView(ListView):
    model = Item
    paginate_by = 20

class ItemCreateView(CreateView):
    model = Item
    fields = ['sku','name','category','total_stock']
    success_url = reverse_lazy('inventory:item-list')

class ItemUpdateView(UpdateView):
    model = Item
    fields = ['sku','name','category','total_stock']
    success_url = reverse_lazy('inventory:item-list')