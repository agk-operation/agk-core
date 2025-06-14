from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.db.models import Sum
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

        # 1) calcula o total já embarcado por OrderItem (todos os batches anteriores)
        shipped_qs = (
            BatchItem.objects
            .filter(batch__order=self.instance.order)
            .values('order_item_id')
            .annotate(shipped=Sum('quantity'))
        )
        shipped = {row['order_item_id']: row['shipped'] for row in shipped_qs}

        # 2) acumula novas quantidades + previous, e agrupa forms por OrderItem
        totals = {}
        forms_per_item = {}
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get('DELETE'):
                continue

            oi  = form.cleaned_data.get('order_item')
            qty = form.cleaned_data.get('quantity')
            if not oi or qty is None:
                continue

            prev = shipped.get(oi.pk, 0)
            totals.setdefault(oi, prev)
            totals[oi] += qty
            forms_per_item.setdefault(oi, []).append(form)

        # 3) valida e marca erros
        has_error = False
        for oi, total in totals.items():
            if total > oi.quantity:
                msg = (
                    f'O total acumulado ({total}) ultrapassa o pedido '
                    f'({oi.quantity}) para “{oi.item.name}”.'
                )
                # erro de campo em cada linha envolvida
                for form in forms_per_item[oi]:
                    form.add_error('quantity', msg)
                has_error = True

        # 4) erro global simplificado
        if has_error:
            raise forms.ValidationError(
                'Há itens com quantidade maior do que o disponível.'
            )

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