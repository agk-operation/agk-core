from decimal import Decimal
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, Field, HTML, Submit
from crispy_forms.bootstrap import AppendedText
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.db.models import Sum
from .models import Order, OrderItem, OrderBatch, BatchItem, BatchStage
from apps.pricing.models import CustomerItemMargin


from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from crispy_forms.bootstrap import AppendedText
from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'customer', 'exporter', 'company',
            'validity', 'usd_rmb', 'usd_brl', 'required_schedule',
            'asap', 'down_payment', 'pol', 'pod',
            'sales_representative', 'business_unit', 'project', 'order_type',
        ]
        # centraliza classes comuns nos widgets
        base_select = {'class': 'form-select form-select-sm'}
        base_input = {'class': 'form-control form-control-sm'}

        widgets = {
            'customer': forms.Select(attrs=base_select),
            'exporter': forms.Select(attrs=base_select),
            'company': forms.Select(attrs=base_select),
            'down_payment': forms.Select(attrs=base_select),
            'down_payment': forms.NumberInput(
                attrs={**base_input, 
                       'type': 'number', 'step': '0.01', 
                       'min': '0', 'placeholder' : '0.00'
                       }
            ),
            'pol': forms.Select(attrs=base_select),
            'pod': forms.Select(attrs=base_select),
            'sales_representative': forms.Select(attrs=base_select),
            'business_unit': forms.Select(attrs=base_select),
            'project': forms.Select(attrs=base_select),
            'order_type': forms.Select(attrs=base_select),

            'validity': forms.DateInput(
                attrs={**base_input, 'type': 'date'}
            ),
            'required_schedule': forms.DateInput(
                attrs={**base_input, 'type': 'date'}
            ),
            'usd_rmb': forms.NumberInput(
                attrs={**base_input, 
                       'type': 'number', 'step': '0.0001', 
                       'min': '0', 'style': 'max-width:100px;',
                       'placeholder' : '0.0000'
                       }
            ),
            'usd_brl': forms.NumberInput(
                attrs={**base_input, 'type': 'number', 'step': '0.0001', 
                       'min': '0', 'style': 'max-width:100px;',
                       'placeholder' : '0.0000'}
            ),
            'asap': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'role': 'switch'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-4'),
                Column('exporter', css_class='col-md-4'),
                Column('company', css_class='col-md-4'),
            ),
            Row(
                Column(
                    Div(
                        Div(
                            Div(
                                Field('required_schedule', css_class='form-control form-control-sm'),
                                css_class='col'
                            ),
                            Div(
                                Div(
                                    Field('asap', css_class='form-check-input'),
                                    css_class='form-check form-switch d-flex align-items-center'
                                ),
                                css_class='col-auto'
                            ),
                            css_class='row g-2 align-items-center'
                        ),
                    ),
                    css_class='col-md-4'
                ),

                Column('pol', css_class='col-md-4'),
                Column('pod', css_class='col-md-4'),
            ),
            Row(
                Column('sales_representative', css_class='col-md-4'),
                Column('business_unit', css_class='col-md-4'),
                Column('project', css_class='col-md-4'),
            ),
            Row(
                Column('order_type', css_class='col-md-4'),
            ),
            Row(
                Column('validity', css_class='col-md-3'),
                Column(
                    AppendedText('usd_rmb', 'USD → CNY', wrapper_class='input-group input-group-sm'),
                    css_class='col-md-3 align-self-center'
                ),
                Column(
                    AppendedText('usd_brl', 'USD → BRL', wrapper_class='input-group input-group-sm'),
                    css_class='col-md-3 align-self-center'
                ),
                Column('down_payment', css_class='col-md-3'),
            ),
        )


class OrderItemForm(forms.ModelForm):
    margin = forms.DecimalField(
        label="Margem (%)",
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,  # agora é opcional
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 
                                        'step':'0.01','min':0,
                                        'style': 'width:100px;', 
        }),
        help_text="Deixe vazio para usar a margem padrão deste cliente/item."
    )

    class Meta:
        model = OrderItem
        fields = ('item', 'packaging_version', 'quantity', 'margin')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select form-select-sm', 
                                        'style': 'max-width:300px;',}
            ),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm',
                                                 'style': 'width:100px;', 
                                                 'min': 1,
            }),
        }

    def __init__(self, *args, customer=None, usd_rmb : Decimal=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        self.usd_rmb = usd_rmb or Decimal('0')

        # se for criação (sem pk) e tiver customer, tentar pré-preencher
        if not self.instance.pk and customer and 'item' in self.initial:
            try:
                cim = CustomerItemMargin.objects.get(
                    customer=customer,
                    item=self.initial['item']
                )
                self.fields['margin'].initial = cim.margin

            except CustomerItemMargin.DoesNotExist:
                pass
            
        if self.instance.pk and self.instance.order.is_locked:
            self.fields['packaging_version'].disabled = True
            self.fields['packaging_version'].widget.attrs['disabled'] = 'disabled'


OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True
)

class OrderItemPackagingForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['packaging_version']
        widgets = {
            'packaging_version': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # filtra só as versões desse item, em ordem decrescente de validade
        if self.instance and self.instance.item_id:
            qs = self.instance.item.packaging_versions.order_by('-valid_from')
            self.fields['packaging_version'].queryset = qs
            # opcional: personalizar a label de cada opção
            self.fields['packaging_version'].label_from_instance = (
                lambda obj: f"{obj.valid_from:%Y-%m-%d %H:%M}"
            )


class BatchItemForm(forms.ModelForm):
    class Meta:
        model = BatchItem
        fields = ('order_item', 'quantity')
        widgets = {
            'order_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class BaseBatchItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        order = getattr(self.instance, 'order', None)
        if not order and 'initial' in kwargs:
            order = kwargs['initial'].get('order')

        allowed_qs = order.order_items.all() if order else OrderItem.objects.none()
        for form in self.forms:
            form.fields['order_item'].queryset = allowed_qs

        self.empty_form.fields['order_item'].queryset = allowed_qs

    def clean(self):
        super().clean()
        errors = []

        # 1) Agrupa os forms não-deletados por OrderItem
        forms_per_item = {}
        for form in self.forms:
            # pula forms com erro de validação de campo (não têm cleaned_data)
            if not hasattr(form, 'cleaned_data'):
                continue

            data = form.cleaned_data
            oi   = data.get('order_item')
            qty  = data.get('quantity')
            delete = data.get('DELETE') if self.can_delete else False

            # só queremos os que têm order_item, quantidade e NÃO estão marcados p/ exclusão
            if oi and qty is not None and not delete:
                forms_per_item.setdefault(oi, []).append(form)

        # 2) Para cada OrderItem, calcula:
        #    shipped_other = soma de todas as quantidades já embarcadas
        #                     EM OUTRAS batches (batch != esta)
        #    max_shippable = quantidade total do pedido - shipped_other
        for oi, forms in forms_per_item.items():
            # soma o que já foi embarcado fora desta batch
            shipped_other = (
                oi.batchitem_set
                  .exclude(batch=self.instance)  # exclui os desta batch
                  .aggregate(total=Sum('quantity'))['total']
                or 0
            )

            max_shippable = oi.quantity - shipped_other
            new_total = sum(f.cleaned_data['quantity'] for f in forms)

            if new_total > max_shippable:
                msg = (
                    f"Você está tentando embarcar {new_total} unidades de “{oi.item.name}”, "
                    f"mas só podem ser enviados {max_shippable} no total (já foram "
                    f"{shipped_other} em outras batches)."
                )
                # anexa o erro a cada form envolvido
                for f in forms:
                    f.add_error('quantity', msg)
                errors.append(msg)


        if errors:
            # dispara um ValidationError geral para interromper o save
            raise ValidationError("Existem itens com quantidade maior do que o disponível.")
        
# final inlineformset, referenciando o BaseBatchItemFormSet
BatchItemFormSet = inlineformset_factory(
    OrderBatch, BatchItem,
    form=BatchItemForm,
    formset=BaseBatchItemFormSet,
    extra=0,
    can_delete=True
)


class OrderBatchForm(forms.ModelForm):
    class Meta:
        model = OrderBatch
        # “order” ficará oculto, “batch_code” e “status” apresentarão selects/text
        fields = ['order', 'batch_code', 'status']
        widgets = {
            'order': forms.HiddenInput(),        # já preenchemos na view
            'batch_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class OrderItemsImportForm(forms.Form):
    file = forms.FileField(
        label="Arquivo (.xlsx ou .csv)",
        help_text="Faça upload de um .xlsx ou .csv com colunas: product, quantity, unit_price"
    )


class BatchStageForm(forms.ModelForm):
    active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Ativo"
    )

    class Meta:
        model = BatchStage
        # note que 'stage' vem como HiddenInput, pois não deve ser alterado
        fields = ['stage', 'active', 'estimated_completion', 'actual_completion']
        widgets = {
            'stage': forms.HiddenInput(),
            'estimated_completion': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'actual_completion': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }


class BaseBatchStageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        errors = []
        for i, form in enumerate(self.forms):

            est = form.cleaned_data.get('estimated_completion')
            act = form.cleaned_data.get('actual_completion')

            # exemplo de regra: real só depois de previsto
            if est and act and act < est:
                msg = "Data real não pode ser anterior à data prevista."
                form.add_error('actual_completion', msg)
                errors.append(f"Linha {i+1}: {msg}")

        if errors:
            # isso vai aparecer em stages_fs.non_form_errors()
            raise forms.ValidationError(errors)


BatchStageFormSet = inlineformset_factory(
    OrderBatch, BatchStage,
    form=BatchStageForm,
    formset=BaseBatchStageFormSet,
    extra=0,
    can_delete=True
)