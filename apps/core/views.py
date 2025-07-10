from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from . import models
from . import forms


RELATED_MODELS = [
    'Company', 'Exporter', 
    'Customer', 'City', 'Port',
    'Province', 'Supplier', 'Currency',
    'SalesRepresentative', 'Project',
]

for model_name in RELATED_MODELS:
    model = getattr(models, model_name)
    form_class = getattr(forms, f'{model_name}Form')
    list_url_name = f'core:{model_name.lower()}-list'

    create_view = type(
        f'{model_name}CreateView',
        (CreateView,),
        {
            'model': model,
            'form_class': form_class,
            'template_name': f'_generic_form.html',
            'success_url': reverse_lazy(list_url_name),
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
            'success_url': reverse_lazy(list_url_name),
            'extra_context': {
                'model_name': model._meta.verbose_name.title()
            },
        }
    )

    globals()[f'{model_name}CreateView'] = create_view
    globals()[f'{model_name}UpdateView'] = update_view