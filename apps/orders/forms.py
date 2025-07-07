from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.db.models import Sum
from .models import Order, OrderItem, OrderBatch, BatchItem, BatchStage
from apps.inventory.models import CustomerItemMargin


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'exporter', 'company']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'exporter': forms.Select(attrs={'class': 'form-select'}),
            'company':  forms.Select(attrs={'class': 'form-select'}),
        }


class OrderItemForm(forms.ModelForm):
    margin = forms.DecimalField(
        label="Margem (%)",
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,  # agora é opcional
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step':'0.01','min':0}),
        help_text="Deixe vazio para usar a margem padrão deste cliente/item."
    )

    class Meta:
        model = OrderItem
        fields = ('item', 'quantity', 'margin')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer

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


OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True
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

        order = None
        if hasattr(self.instance, 'order') and self.instance.order_id:
            order = self.instance.order
        else:
            order = kwargs.get('initial', {}).get('order')

        if order:
            allowed_qs = order.order_items.all()
        else:
            allowed_qs = OrderItem.objects.none()

        for form in self.forms:
            form.fields['order_item'].queryset = allowed_qs

        self.empty_form.fields['order_item'].queryset = allowed_qs


    def clean(self):
        super().clean()

        totals = {}
        forms_per_item = {}
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get('DELETE'):
                continue
            oi = form.cleaned_data.get('order_item')
            qty = form.cleaned_data.get('quantity')
            if not oi or qty is None:
                continue
            totals.setdefault(oi, 0)
            totals[oi] += qty
            forms_per_item.setdefault(oi, []).append(form)

        errors = []
        for oi, new_qty in totals.items():
            qs = BatchItem.objects.filter(order_item=oi)
            if self.instance.pk:
                qs = qs.exclude(batch=self.instance)
            already_shipped = qs.aggregate(total=Sum('quantity'))['total'] or 0

            if already_shipped + new_qty > oi.quantity:
                allowed = oi.quantity - already_shipped
                msg = (
                    f"Você está tentando embarcar {new_qty} unidades de “{oi.item.name}”, "
                    f"mas só restam {allowed}."
                )
                for f in forms_per_item[oi]:
                    f.add_error('quantity', msg)
                errors.append(msg)
                
        if errors:
            raise ValidationError("Existem itens com quantidade maior do que o disponível.")
        

# final inlineformset, referenciando o BaseBatchItemFormSet
BatchItemFormSet = inlineformset_factory(
    OrderBatch, BatchItem,
    form=BatchItemForm,
    formset=BaseBatchItemFormSet,
    extra=1,
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
    class Meta:
        model = BatchStage
        fields = ['name', 'estimated_completion', 'actual_completion']
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control'}),
            'estimated_completion': forms.DateInput(
                attrs={'type':'date','class':'form-control'}
            ),
            'actual_completion': forms.DateInput(
                attrs={'type':'date','class':'form-control'}
            ),
        }

BatchStageFormSet = inlineformset_factory(
    OrderBatch, BatchStage,
    form=BatchStageForm,
    extra=1,
    can_delete=True
)