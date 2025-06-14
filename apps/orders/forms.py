from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from .models import Order, OrderItem, OrderBatch, BatchItem


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
    class Meta:
        model = OrderItem
        fields = ('item', 'quantity')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1, can_delete=True
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
    def clean(self):
        super().clean()

        # 1) acumula totais por OrderItem e agrupa forms
        totals = {}
        forms_per_item = {}
        global_errors = []
        for form in self.forms:
            # pula formulários marcados para deleção ou vazios
            if self.can_delete and form.cleaned_data.get('DELETE'):
                continue

            oi = form.cleaned_data.get('order_item')
            qty = form.cleaned_data.get('quantity')
            if not oi or qty is None:
                continue

            totals.setdefault(oi, 0)
            totals[oi] += qty

            forms_per_item.setdefault(oi, []).append(form)

        # 2) para cada OrderItem que estourou, marca erro em cada form associado
        for oi, total in totals.items():
            if total > oi.quantity:
                msg = (
                    f'O total ({total}) para o item "{oi.item.name}" '
                    f'ultrapassa o disponível ({oi.quantity}).'
                )
                global_errors.append('Erro nos')
                for form in forms_per_item[oi]:
                    form.add_error('quantity', msg)
        if global_errors:
            raise forms.ValidationError(global_errors)


# agora use esse BaseFormSet na construção do seu inlineformset:
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