# apps/shipments/forms.py

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field
from django import forms
from django.forms.models import inlineformset_factory, BaseInlineFormSet

from .models import Shipment, ShipmentBatch, ShipmentStage, Stage

class ShipmentForm(forms.ModelForm):
    class Meta:
        model  = Shipment
        fields = [
            'pod','signer','leader','customer_reference',
            # não expomos status aqui, ele é sempre PRE
        ]
        widgets = {
            'pod': forms.TextInput(attrs={'class':'form-control'}),
            'signer': forms.TextInput(attrs={'class':'form-control'}),
            'leader': forms.TextInput(attrs={'class':'form-control'}),
            'customer_reference': forms.TextInput(attrs={'class':'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False  # importante pois o <form> está no template
        self.helper.layout = Layout(
            Row(
                Column('pod', css_class='col-md-6'),
                Column('customer_reference', css_class='col-md-6'),
            ),
            Row(
                Column('signer', css_class='col-md-6'),
                Column('leader', css_class='col-md-6'),
            ),
        )


    def clean(self):
        cleaned = super().clean()
        # garante que todos os campos principais estejam preenchidos
        missing = [f for f in ('pod','signer','leader','customer_reference') 
                   if not cleaned.get(f)]
        if missing:
            raise forms.ValidationError(
                "Fill all the Pre-Loading fields."
            )
        return cleaned


class ShipmentBatchForm(forms.ModelForm):
    class Meta:
        model = ShipmentBatch
        fields = ['order_batch']  # ou os campos necessários
        widgets = {
            'order_batch': forms.Select(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean_order_batch(self):
        order_batch = self.cleaned_data.get('order_batch')

        # só valida se order_batch foi preenchido
        if not order_batch:
            return order_batch

        # se está editando, ignore ele mesmo
        if self.instance.pk:
            existing = ShipmentBatch.objects.filter(order_batch=order_batch).exclude(pk=self.instance.pk)
        else:
            existing = ShipmentBatch.objects.filter(order_batch=order_batch)

        if existing.exists():
            raise forms.ValidationError("Este lote já está vinculado a outro pré-embarque.")

        return order_batch


class BaseShipmentBatchFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_batches = set()

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            order_batch = form.cleaned_data.get('order_batch')

            if not order_batch:
                continue

            if order_batch.pk in seen_batches:
                form.add_error('order_batch', "Este batch já foi adicionado.")
            else:
                seen_batches.add(order_batch.pk)


ShipmentBatchFormSet = inlineformset_factory(
    Shipment,
    ShipmentBatch,
    form=ShipmentBatchForm,
    formset=BaseShipmentBatchFormSet,
    extra=1,
    can_delete=True
)


class ShipmentStageForm(forms.ModelForm):
    class Meta:
        model = ShipmentStage
        fields = [
            'stage',
            'estimated_completion',
            'actual_completion',
            'notes',
            'attachment',
        ]
        widgets = {
            'stage':                forms.HiddenInput(),
            'estimated_completion': forms.DateInput(attrs={
                                        'type': 'date',
                                        'class': 'form-control form-control-sm'
                                    }),
            'actual_completion':    forms.DateInput(attrs={
                                        'type': 'date',
                                        'class': 'form-control form-control-sm'
                                    }),
            'notes':                forms.Textarea(attrs={
                                        'class': 'form-control form-control-sm',
                                        'rows': 2
                                    }),
            'attachment':           forms.FileInput(attrs={
                                        'class': 'form-control form-control-sm'
                                    }),
        }

    def __init__(self, *args, shipment=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Descobre o Stage
        self.stage = getattr(self.instance, 'stage', None)
        if not self.stage:
            stage_id = self.initial.get('stage')
            self.stage = Stage.objects.filter(pk=stage_id).first()
            if self.stage:
                self.instance.stage = self.stage

        if not self.stage:
            return

        # Regras para o campo anexo
        if not self.stage.allows_attachment:
            self.fields.pop('attachment', None)
        elif self.stage.requires_attachment:
            self.fields['attachment'].required = True

        # Garante que temos o Shipment
        if shipment is None:
            try:
                shipment = self.instance.shipment
            except (AttributeError, Shipment.DoesNotExist):
                shipment = None

        if not shipment:
            shipment = Shipment()  # fallback vazio

        # Injeção dos campos dinâmicos
        for cfg in self.stage.field_configs.all():
            fname = cfg.field_name

            if fname in self.fields:
                continue  # já está presente

            field_obj = Shipment._meta.get_field(fname)
            field = field_obj.formfield()
            field.required = False

            # ⚠️ Se estiver bindado (POST), tenta capturar o valor da submissão
            if self.is_bound:
                value = self.data.get(self.add_prefix(fname), None)
                field.initial = value
            else:
                field.initial = getattr(shipment, fname)

            field.widget.attrs.update({
                'class': 'form-control form-control-sm',
            })
            self.fields[fname] = field
         
    def clean(self):
        data = super().clean()
        stage = self.stage
        shp   = self.instance.shipment or None

        # 2) Se preencher actual_completion → exige o attachment
        if stage and stage.requires_attachment:
            if data.get('actual_completion') and not data.get('attachment'):
                self.add_error('attachment',
                    "Este anexo é obrigatório para concluir a etapa.")

        # 3) Se preencher actual_completion → exige todos os shipment_fields configurados
        if stage and data.get('actual_completion'):
            missing = []
            for cfg in stage.field_configs.all():
                fname = cfg.field_name
                val = self.cleaned_data.get(fname)

                # Se não achou, tenta no Shipment (ex: edição)
                if val in (None, '', []) and shp:
                    val = getattr(shp, fname, None)

                if val in (None, '', []):
                    missing.append(fname)
            if missing:     
                self.add_error(
                    None,
                    "Para concluir “%s”, preencha: %s" % (
                        stage.name,
                        ", ".join(missing)
                    )
                )

        return data


class ShipmentStageInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)

        shp   = form.instance.shipment
        stg   = form.instance.stage

        # para cada configuração criada no admin
        for cfg in stg.field_configs.all():
            fname = cfg.field_name
            try:
                field_obj = Shipment._meta.get_field(fname)
            except Exception:
                continue

            ff = field_obj.formfield()
            ff.initial = getattr(shp, fname)
            # opcional: readonly
            ff.widget.attrs.update({
                'class': 'form-control form-control-sm',
            })
            form.fields[fname] = ff



# finalmente, o inlineformset “oficial”
ShipmentStageFormSet = inlineformset_factory(
    Shipment,
    ShipmentStage,
    form=ShipmentStageForm,
    formset=ShipmentStageInlineFormSet,
    extra=0,
    can_delete=False,
)


class FinalShipmentForm(forms.ModelForm):
    class Meta:
        model  = Shipment
        fields = [
            'bl_number',
            'bl_date',
            'inspection_no',
            'eta_destination',
            'ata_destination',
        ]
        widgets = {
            'bl_number':      forms.TextInput(attrs={'class':'form-control'}),
            'bl_date':        forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'inspection_no':  forms.TextInput(attrs={'class':'form-control'}),
            'eta_destination':forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'ata_destination':forms.DateInput(attrs={'type':'date','class':'form-control'}),
        }

    def clean(self):
        cd = super().clean()
        # Exemplo de validação conjuta: se um dos campos for preenchido,
        # exija todos:
        any_filled = any(cd.get(f) for f in self.fields)
        missing = [f for f in self.fields if not cd.get(f)] if any_filled else []
        if missing:
            raise forms.ValidationError(
                f"Para completar o Final Shipment, preencha: {', '.join(missing)}"
            )
        return cd