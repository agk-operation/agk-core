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
from django.http import JsonResponse
from . import default_data
from django.db.models import ForeignKey, CharField, IntegerField, DecimalField, TextField 

class PopulateDefaultsView(View):
    """
    View INTELIGENTE para popular os dados padrão dos modelos via AJAX.
    Ela inspeciona os modelos para descobrir campos obrigatórios.
    """
    MODEL_CONFIG = {
        # A configuração agora só precisa do modelo e da lista de nomes
        'Category':    (models.Category,    default_data.DEFAULT_CATEGORIES),
        'Supplier':    (models.Supplier,    default_data.DEFAULT_SUPPLIERS),
        'Subcategory': (models.Subcategory, default_data.DEFAULT_SUBCATEGORIES),
        'Project':     (models.Project,     default_data.DEFAULT_PROJECTS),
        'SupplierChain': (models.SupplierChain, default_data.DEFAULT_SUPPLIER_CHAINS),
        'Chain':       (models.Chain,       default_data.DEFAULT_CHAINS),
        'BrandManufacturer': (models.BrandManufacturer, default_data.DEFAULT_BRAND_MANUFACTURERS),
        'Ncm':         (models.Ncm,         default_data.DEFAULT_NCMS),
        'Group':       (models.Group,       default_data.DEFAULT_GROUPS),
        'Version':     (models.Version,     default_data.DEFAULT_VERSIONS),
    }

    def get_placeholder_for_fk(self, related_model):
        """
        Cria ou obtém um objeto placeholder para um modelo de chave estrangeira.
        Esta função é uma fábrica de objetos padrão.
        """
        # Tenta encontrar um campo 'name' para usar
        if hasattr(related_model, 'name'):
            placeholder, _ = related_model.objects.get_or_create(name=f'Default {related_model.__name__}')
            return placeholder
        # Adicione outras lógicas aqui se algum modelo não tiver o campo 'name'
        raise Exception(f"Não sei como criar um placeholder para o modelo {related_model.__name__}")

    def post(self, request, *args, **kwargs):
        created_items = {}
        
        for model_name, (Model, data_list) in self.MODEL_CONFIG.items():
            if not Model.objects.exists():
                print(f"Populando o modelo {model_name} com dados iniciais...")
                for value in data_list:
                    
                    # --- INÍCIO DA LÓGICA INTELIGENTE ---
                    defaults = {}
                    # Itera sobre todos os campos do modelo
                    for field in Model._meta.get_fields():
                        
                        if not field.concrete:
                            continue

                        is_auto_field = (
                            field.name == 'name' or
                            field.primary_key or
                            getattr(field, 'auto_now', False) or
                            getattr(field, 'auto_now_add', False)
                        )
                        if is_auto_field:
                            continue
                        
                        # Verifica se o campo é obrigatório (não nulo e sem valor padrão)
                        if not getattr(field, 'null', True) and not field.has_default():
                            
                            # Se for uma Chave Estrangeira (ForeignKey)
                            if isinstance(field, ForeignKey):
                                defaults[field.name] = self.get_placeholder_for_fk(field.related_model)
                            
                            # Se for um campo de texto (CharField OU TextField)
                            elif isinstance(field, (CharField, TextField)): # 👈 CORREÇÃO AQUI
                                defaults[field.name] = 'Default'
                            
                            # Adicione outros tipos de campo conforme necessário
                            elif isinstance(field, (IntegerField, DecimalField)):
                                defaults[field.name] = 0
                            
                            # Se encontrarmos um campo obrigatório que não sabemos como preencher, é melhor falhar
                            else:
                                raise TypeError(f"Campo obrigatório '{field.name}' do tipo '{type(field).__name__}' não tem um valor padrão definido.")
                    # --- FIM DA LÓGICA INTELIGENTE ---
                    
                    Model.objects.get_or_create(name=value, defaults=defaults)
            
            created_items[model_name.lower()] = list(Model.objects.values('id', 'name'))

        return JsonResponse({
            'status': 'success',
            'message': 'Dados padrão verificados e populados com sucesso!',
            'data': created_items
        })
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
    'chain':              'inventory:chain-create',
    'ncm':                'inventory:ncm-create',
    'supplier_chain':     'inventory:supplier_chain-create',  
    'brand_manufacturer': 'inventory:brand_manufacturer-create',
    'model_application':  'inventory:model_application-create', 
    'currency':           'inventory:currency-create',
    'group':              'inventory:group-create',
    'version':            'inventory:version-create',
    'supplier':           'inventory:supplier-create',
    
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
    'BrandManufacturer', 'ModelApplication', 'Currency',
    'Group', 'Version', 'Supplier',
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
