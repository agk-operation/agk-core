from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import CustomerItemMargin

class MarginListView(ListView):
    model = CustomerItemMargin
    template_name = 'pricing/margin_list.html'
    paginate_by = 50

class MarginCreateView(CreateView):
    model = CustomerItemMargin
    fields = ['customer','item','margin']
    template_name = 'pricing/margin_form.html'
    success_url = reverse_lazy('pricing:margin-list')

class MarginUpdateView(UpdateView):
    model = CustomerItemMargin
    fields = ['customer','item','margin']
    template_name = 'pricing/margin_form.html'
    success_url = reverse_lazy('pricing:margin-list')

class MarginDeleteView(DeleteView):
    model = CustomerItemMargin
    template_name = 'pricing/margin_delete.html'
    success_url = reverse_lazy('pricing:margin-list')
