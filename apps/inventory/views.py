from django.views import View
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db import transaction
from django.utils import timezone
from . import models
from . import forms


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 25
    permission_required = 'inventory.view_item'

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


class ItemCreateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    model = models.Item
    def get_object(self):
        pk = self.kwargs.get('pk')
        if pk:
            return get_object_or_404(self.model, pk=pk)
        return self.model()  # instância nova
    '''
    ajustar, não fucnionou...
    def handle_no_permission(self):
        raise PermissionDenied("Você não tem permissão para realizar essa ação.")
    '''
    def has_permission(self):
        obj = self.get_object()
        if obj.pk:
            perm = f'{self.model._meta.app_label}.change_{self.model._meta.model_name}'
        else:
            perm = f'{self.model._meta.app_label}.add_{self.model._meta.model_name}'
        return self.request.user.has_perm(perm)


    def get(self, request, pk=None):
        item = get_object_or_404(models.Item, pk=pk) if pk else models.Item()
        form = forms.ItemForm(instance=item)
        fs_app  = forms.ItemModelApplicationFormSet(instance=item, prefix=APP_FS_PREFIX)
        fs_pack = forms.ItemPackagingVersionFormSet(instance=item, prefix=PACK_FS_PREFIX)

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


class ItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Item
    template_name = 'inventory/item_delete.html'
    success_url = reverse_lazy('inventory:item-list')
    context_object_name = 'item'
    permission_required = 'inventory.delete_item'


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
        (LoginRequiredMixin, PermissionRequiredMixin, CreateView,),
        {
            'model': model,
            'permission_required': f'inventory.add_{model._meta.model_name}',
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
        (LoginRequiredMixin, PermissionRequiredMixin, UpdateView,),
        {
            'model': model,
            'form_class': form_class,
            'permission_required': f'inventory.change_{model._meta.model_name}',
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

    def get(self, request, *args, **kwargs):
        formset = forms.ItemPackagingVersionFormSet(instance=self.item)
        # Forms separados:
        current_forms = []
        historic_forms = []
        new_forms = []

        for form in formset.forms:
            if form.instance.pk:
                if form.instance.valid_to:
                    historic_forms.append(form)
                else:
                    current_forms.append(form)
            else:
                new_forms.append(form)

        # Form vazio manual
        empty_form = forms.ItemPackagingVersionFormSet(instance=self.item).empty_form

        context = {
            'item': self.item,
            'formset': formset,
            'current_forms': current_forms,
            'historic_forms': historic_forms,
            'new_forms': new_forms,
            'empty_form': empty_form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        formset = forms.ItemPackagingVersionFormSet(request.POST, instance=self.item)
        if formset.is_valid():
            now = timezone.now()
            current = self.item.current_packaging_version
            if current:
                current.valid_to = now
                current.save()

            instances = formset.save(commit=False)
            for inst in instances:
                inst.item = self.item
                if not inst.valid_from:
                    inst.valid_from = now
                inst.save()

            formset.save_m2m()

            for f in models.ItemPackagingVersion.PACKAGING_FIELDS:
                setattr(self.item, f, getattr(instances[-1], f))
            self.item.save()

            return redirect('inventory:item-edit', pk=self.item.pk)

        return render(request, self.template_name, {
            'formset': formset,
            'item': self.item
        })
