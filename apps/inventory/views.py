from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from . import models
from . import forms


class ItemListView(ListView):
    model = models.Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 25

CREATE_URLS = {
    'category':           'inventory:category-create',
    'subcategory':        'inventory:subcategory-create',
    'project':            'inventory:project-create',
    'supplier_chain':     'inventory:supplierchain-create',
    'chain':              'inventory:chain-create',
    'ncm':                'inventory:ncm-create',
    'brand_manufacturer': 'inventory:brandmanufacturer-create',
    'model_application':  'inventory:modelapplication-create',
    'currency':           'inventory:currency-create',
}
FORMSET_PREFIX = 'itemmodelapplication_set'
SUCCESS_URL = reverse_lazy('inventory:item-list')


class ItemCreateUpdateView(View):
    """
    Se pk fornecido, faz update; se não, create.
    """

    def get(self, request, pk=None):
        if pk is not None:
            item = get_object_or_404(models.Item, pk=pk)
            form = forms.ItemForm(instance=item)
            formset = forms.ItemModelApplicationFormSet(
                instance=item,
                prefix=FORMSET_PREFIX
            )
        else:
            item = None
            form = forms.ItemForm()
            formset = forms.ItemModelApplicationFormSet(
                prefix=FORMSET_PREFIX
            )

        return render(request, 'inventory/item_form.html', {
            'form': form,
            'formset': formset,
            'create_urls': CREATE_URLS,
        })


    def post(self, request, pk=None):
        if pk is not None:
            item = get_object_or_404(models.Item, pk=pk)
            form = forms.ItemForm(request.POST, instance=item)
            formset = forms.ItemModelApplicationFormSet(
                request.POST,
                instance=item,
                prefix=FORMSET_PREFIX
            )
        else:
            form = forms.ItemForm(request.POST)
            formset = forms.ItemModelApplicationFormSet(
                request.POST,
                prefix=FORMSET_PREFIX
            )
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.instance = obj
            formset.save()
            return redirect(SUCCESS_URL)

        return render(request, 'inventory/item_form.html', {
            'form': form,
            'formset': formset,
            'create_urls': CREATE_URLS,
        })


class ItemDeleteView(DeleteView):
    model = models.Item
    template_name = 'inventory/item_delete.html'
    success_url = reverse_lazy('inventory:item-list')
    context_object_name = 'item'


RELATED_MODELS = [
    'Category', 'Subcategory', 'Project', 
    'SupplierChain', 'Chain', 'Ncm',
    'BrandManufacturer', 'ModelApplication', 'Currency'
]

for model_name in RELATED_MODELS:
    model = getattr(models, model_name)
    form_class = getattr(forms, f'{model_name}Form')

    create_view = type(
        f'{model_name}CreateView',
        (CreateView,),
        {
            'model': model,
            'form_class': form_class,
            'template_name': f'_generic_form.html',
            'success_url': reverse_lazy('inventory:item-create'),
            'extra_context': {
                'model_name': model._meta.verbose_name.title()
            },
        }
    )

    update_view = type(
        f'{model_name}UpdateView',
        (UpdateView,),
        {
            'model': model,
            'form_class': form_class,
            'template_name': f'_generic_form.html',
            'success_url': reverse_lazy('inventory:item-create'),
            'extra_context': {
                'model_name': model._meta.verbose_name.title()
            },
        }
    )

    globals()[f'{model_name}CreateView'] = create_view
    globals()[f'{model_name}UpdateView'] = update_view