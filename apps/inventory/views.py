from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db import transaction
from django.utils import timezone
from . import models
from . import forms
from . import default_data

CHOICE_FIELD_DEFAULTS = {
    'category':    (models.Category,    default_data.DEFAULT_CATEGORIES),
    'supplier':    (models.Supplier,    default_data.DEFAULT_SUPPLIERS),
    'subcategory': (models.Subcategory, default_data.DEFAULT_SUBCATEGORIES),
    'project':     (models.Project,     default_data.DEFAULT_PROJECTS),
    'supplier_chain': (models.SupplierChain, default_data.DEFAULT_SUPPLIER_CHAINS),
    'chain':       (models.Chain,      default_data.DEFAULT_CHAINS),
    'brand_manufacturer': (models.BrandManufacturer, default_data.DEFAULT_BRAND_MANUFACTURERS),
    'ncm':         (models.Ncm,        default_data.DEFAULT_NCMS),
    }

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
APP_FS_PREFIX   = 'itemmodelapplication_set'
PACK_FS_PREFIX  = 'pack'


class ItemCreateUpdateView(View):
    def get(self, request, pk=None):
        item = get_object_or_404(models.Item, pk=pk) if pk else models.Item()
        form = forms.ItemForm(instance=item)
        fs_app  = forms.ItemModelApplicationFormSet(instance=item, prefix=APP_FS_PREFIX)
        fs_pack = forms.ItemPackagingVersionFormSet(instance=item, prefix=PACK_FS_PREFIX)

        for field_name, (model, defaults) in CHOICE_FIELD_DEFAULTS.items():
            if not model.objects.exists():
                choices = [(value, value) for value in defaults]
                form.fields[field_name].choices = choices

        # Desabilita ONLY os campos dos forms históricos (pk existente)
        if item.pk:
            for sub in fs_pack.forms:
                if sub.instance.pk:
                    for fld in sub.fields.values():
                        fld.disabled = True
                        fld.widget.attrs['disabled'] = True

        return render(request, 'inventory/item_form.html', {
            'form': form,
            'formset': fs_app,
            'packaging_fs': fs_pack,
            'packaging_fields': models.ItemPackagingVersion.PACKAGING_FIELDS,
            'create_urls': CREATE_URLS,
            'object': item,
        })

    def post(self, request, pk=None):
        item = get_object_or_404(models.Item, pk=pk) if pk else models.Item()
        form = forms.ItemForm(request.POST, request.FILES or None, instance=item)
        fs_app  = forms.ItemModelApplicationFormSet(
                      request.POST, instance=item, prefix=APP_FS_PREFIX)
        fs_pack = forms.ItemPackagingVersionFormSet(
                      request.POST, instance=item, prefix=PACK_FS_PREFIX)

        # Pule validação do blank form NÃO alterado
        for sub in fs_pack.forms:
            if not sub.instance.pk and not sub.has_changed():
                sub.empty_permitted = True

        form_valid    = form.is_valid()
        fs_app_valid  = fs_app.is_valid()
        fs_pack_valid = fs_pack.is_valid()

        print(">>> POST keys:", request.POST.keys())
        print(">>> fs_pack.prefix:", fs_pack.prefix)

        if not (form_valid and fs_app_valid and fs_pack_valid):
            return render(request, 'inventory/item_form.html', {
                'form': form,
                'formset': fs_app,
                'packaging_fs': fs_pack,
                'packaging_fields': models.ItemPackagingVersion.PACKAGING_FIELDS,
                'create_urls': CREATE_URLS,
                'object': item,
            })

        with transaction.atomic():
            item = form.save()
            fs_app.instance = item
            fs_app.save()

            # Seta default valid_from onde for novo e sem data
            for sub in fs_pack.forms:
                if not sub.instance.pk and sub.has_changed():
                    if not sub.cleaned_data.get('valid_from'):
                        sub.cleaned_data['valid_from'] = timezone.now()

            fs_pack.instance = item
            fs_pack.save()

        return redirect('inventory:item-list')


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


class ItemPackagingUpdateView(View):
    template_name = 'inventory/item_packaging.html'

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(models.Item, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        current = self.item.current_packaging_version()
        initial = {}
        if current:
            for f in models.ItemPackagingVersion.PACKAGING_FIELDS:
                initial[f] = getattr(current, f)
        else:
            for f in models.ItemPackagingVersion.PACKAGING_FIELDS:
                initial[f] = getattr(self.item, f)
        return initial

    def get(self, request, *args, **kwargs):
        form = forms.ItemPackagingVersionForm(initial=self.get_initial())
        return render(request, self.template_name, {'form': form, 'item': self.item})

    def post(self, request, *args, **kwargs):
        form = forms.ItemPackagingVersionForm(request.POST)
        if form.is_valid():
            now = timezone.now()
            current = self.item.current_packaging_version()
            if current:
                current.valid_to = now
                current.save()
            pkg = form.save(commit=False)
            pkg.item = self.item
            pkg.valid_from = now
            pkg.save()

            for f in models.ItemPackagingVersion.PACKAGING_FIELDS:
                setattr(self.item, f, getattr(pkg, f))
            self.item.save()

            return redirect('inventory:item-edit', pk=self.item.pk)

        return render(request, self.template_name, {'form': form, 'item': self.item})