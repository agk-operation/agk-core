from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View, generic
from django.db import transaction
from django.http import Http404
from agk_core import metrics
from .models import Shipment, Stage, ShipmentStage
from .forms  import ShipmentForm, ShipmentBatchFormSet, ShipmentStageFormSet, ShipmentStageForm, FinalShipmentForm

# ───────────────────────────────────────────────────────────
#  Views para a fase de PRE-LOADING (status = PRE)
# ───────────────────────────────────────────────────────────

class PreShipmentListView(generic.ListView):
    model = Shipment
    template_name = 'shipments/shipment_list.html'

    def get_queryset(self):
        return Shipment.objects.filter(status=Shipment.STATUS_PRELOADING)
    
    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['pre_loading'] = True
            return context


class PreShipmentCreateView(View):
    template_name = 'shipments/shipment_form.html'  # unificado

    def get(self, request):
        # Form principal (pré)
        form = ShipmentForm()
        batch_fs = ShipmentBatchFormSet(prefix='sb')

        # Stages de PRE em ordem
        pre_stages = list(
            Stage.objects
                 .filter(workflow=Stage.WORKFLOW_PRELOADING)
                 .order_by('sort_order')
        )

        # Construção dos forms de stage "soltos" (não formset)
        fake_shipment = Shipment()
        stage_forms = []
        for stage in pre_stages:
            instance = ShipmentStage(stage=stage, shipment=fake_shipment)
            form_stage = ShipmentStageForm(
                prefix=f"st-{stage.pk}",
                initial={'stage': stage.pk},
                instance=instance
            )
            stage_forms.append({'stage': stage, 'form': form_stage})

        ctx = {
            'phase': 'pre',
            'object': fake_shipment,           # para header/cards
            'main_form': form,                 # <- unificado
            'batch_fs': batch_fs,
            'stages_fs': None,                 # não usamos formset no pré
            'stages_forms': stage_forms,       # <- unificado (antes: stages_data)
            'read_only': False,
            'is_create': True,
            'show_batches': True,
            'delete_url': None,
            'cancel_url': reverse('shipments:pre_shipment-list'),
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = ShipmentForm(request.POST)
        batch_fs = ShipmentBatchFormSet(request.POST, request.FILES, prefix='sb')

        pre_stages = list(
            Stage.objects
                .filter(workflow=Stage.WORKFLOW_PRELOADING)
                .order_by('sort_order')
        )

        fake_shipment = Shipment()

        stage_forms = []
        stage_form_objects = []
        forms_valid = True

        for stage in pre_stages:
            prefix = f"st-{stage.pk}"
            instance = ShipmentStage(stage=stage, shipment=fake_shipment)
            form_stage = ShipmentStageForm(
                request.POST, request.FILES,
                prefix=prefix,
                instance=instance,
                shipment=fake_shipment
            )
            if not form_stage.is_valid():
                forms_valid = False
            stage_forms.append({'stage': stage, 'form': form_stage})
            stage_form_objects.append(form_stage)

        if form.is_valid() and batch_fs.is_valid() and forms_valid:
            with transaction.atomic():
                shipment = form.save(commit=False)

                # Persiste campos dinâmicos mapeados dos stages para o shipment
                for form_stage in stage_form_objects:
                    stage = form_stage.instance.stage
                    for cfg in stage.field_configs.all():
                        fname = cfg.field_name
                        if fname in form_stage.cleaned_data:
                            setattr(shipment, fname, form_stage.cleaned_data[fname])

                shipment.status = Shipment.STATUS_PRELOADING
                shipment.save()

                # Batches
                batch_fs.instance = shipment
                batch_fs.save()

                # Cria as ShipmentStage
                for form_stage in stage_form_objects:
                    new_stage = form_stage.save(commit=False)
                    new_stage.shipment = shipment
                    new_stage.save()

            return redirect('shipments:pre_shipment-edit', pk=shipment.pk)

        # Re-render com o template unificado
        ctx = {
            'phase': 'pre',
            'object': fake_shipment,
            'main_form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_forms': stage_forms,
            'read_only': False,
            'is_create': True,
            'show_batches': True,
            'delete_url': None,
            'cancel_url': reverse('shipments:pre_shipment-list'),
        }
        return render(request, self.template_name, ctx)


class PreShipmentUpdateView(View):
    template_name = 'shipments/shipment_form.html'  # unificado

    def dispatch(self, request, *args, **kwargs):
        self.shipment = get_object_or_404(Shipment, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def ensure_pre_stages(self, shipment):
        existing = { ss.stage_id for ss in shipment.stages.all() }
        qs = Stage.objects.filter(workflow=Stage.WORKFLOW_PRELOADING).order_by('sort_order')
        for st in qs:
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)
        self.ensure_pre_stages(shipment)

        form = ShipmentForm(instance=shipment)
        batch_fs = ShipmentBatchFormSet(instance=shipment, prefix='sb')

        pre_stages = Stage.objects.filter(
            workflow=Stage.WORKFLOW_PRELOADING
        ).order_by('sort_order')

        stage_forms = []
        for stage in pre_stages:
            shipment_stage = ShipmentStage.objects.get(shipment=shipment, stage=stage)
            form_stage = ShipmentStageForm(
                prefix=f"st-{stage.pk}",
                instance=shipment_stage,
                shipment=shipment
            )
            stage_forms.append({'stage': stage, 'form': form_stage})

        ctx = {
            'phase': 'pre',
            'object': shipment,
            'main_form': form,                  # <- unificado
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_forms': stage_forms,        # <- unificado
            'read_only': False,
            'is_create': False,
            'show_batches': True,
            'delete_url': reverse('shipments:pre_shipment-delete', args=[shipment.pk]),
            'cancel_url': reverse('shipments:pre_shipment-list'),
            'shipment_metrics': metrics.get_shipment_metrics(self.shipment.pk),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)
        self.ensure_pre_stages(shipment)

        form = ShipmentForm(request.POST, instance=shipment)
        batch_fs = ShipmentBatchFormSet(request.POST, prefix='sb', instance=shipment)

        pre_stages = Stage.objects.filter(
            workflow=Stage.WORKFLOW_PRELOADING
        ).order_by('sort_order')

        stage_forms = []
        stage_form_objects = []
        forms_valid = True

        for stage in pre_stages:
            prefix = f"st-{stage.pk}"
            shipment_stage = ShipmentStage.objects.get(shipment=shipment, stage=stage)
            form_stage = ShipmentStageForm(
                request.POST, request.FILES,
                prefix=prefix,
                instance=shipment_stage,
                shipment=shipment
            )
            if not form_stage.is_valid():
                forms_valid = False
            stage_forms.append({'stage': stage, 'form': form_stage})
            stage_form_objects.append(form_stage)

        if form.is_valid() and batch_fs.is_valid() and forms_valid:
            with transaction.atomic():
                shp = form.save(commit=False)
                for form_stage in stage_form_objects:
                    stage = form_stage.instance.stage
                    for cfg in stage.field_configs.all():
                        fname = cfg.field_name
                        if fname in form_stage.cleaned_data:
                            setattr(shp, fname, form_stage.cleaned_data[fname])
                batch_fs.save()
                for form_stage in stage_form_objects:
                    form_stage.save()
                if all(
                    ss.actual_completion
                    for ss in shp.stages.filter(stage__workflow=Stage.WORKFLOW_PRELOADING)
                ):
                    shp.status = Shipment.STATUS_READY
                shp.save()

            return redirect('shipments:pre_shipment-edit', pk=shipment.pk)

        ctx = {
            'phase': 'pre',
            'object': shipment,
            'main_form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_forms': stage_forms,
            'read_only': False,
            'is_create': False,
            'show_batches': True,
            'delete_url': reverse('shipments:pre_shipment-delete', args=[shipment.pk]),
            'cancel_url': reverse('shipments:pre_shipment-list'),
            'shipment_metrics': metrics.get_shipment_metrics(self.shipment.pk),
        }
        return render(request, self.template_name, ctx)



class PreShipmentDeleteView(View):
    """Excluir um Shipment em PRE-LOADING."""
    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)
        shipment.delete()
        return redirect('shipments:pre_shipment-list')


# ───────────────────────────────────────────────────────────
#  Views para a fase de SHIPMENT FINAL (status = RDY ou SHP)
# ───────────────────────────────────────────────────────────

class ShipmentListView(generic.ListView):
    model = Shipment
    template_name = 'shipments/shipment_list.html'

    def get_queryset(self):
        return Shipment.objects.exclude(status=Shipment.STATUS_PRELOADING)
    
    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['pre_loading'] = False
            return context


class FinalShipmentDetailView(generic.DetailView):
    model = Shipment
    template_name = 'shipments/shipment_detail.html'
    context_object_name = 'shipment'

    def get_object(self):
        obj = super().get_object()
        if obj.status not in [Shipment.STATUS_READY, Shipment.STATUS_SHIPPED]:
            raise Http404("Este shipment ainda não foi finalizado")
        return obj


class ShipmentUpdateView(View):
    """
    Exibe as etapas (pré-embarque em leitura e final para edição).
    Ao completar todas as etapas de SHIPMENT, define status=SHIPPED.
    """
    template_name = 'shipments/shipment_form.html'  # unificado

    def ensure_all_stages(self, shipment):
        existing = {ss.stage_id for ss in shipment.stages.all()}
        for st in Stage.objects.filter(workflow=Stage.WORKFLOW_PRELOADING):
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)
        for st in Stage.objects.filter(workflow=Stage.WORKFLOW_SHIPMENT):
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        if shipment.status != Shipment.STATUS_READY:
            raise Http404("Este shipment não está pronto para edição final.")
        self.ensure_all_stages(shipment)
        batch_fs = ShipmentBatchFormSet(instance=shipment, prefix='sb')

        final_form = FinalShipmentForm(instance=shipment)
        stages_fs  = ShipmentStageFormSet(instance=shipment, prefix='st')

        ctx = {
            'phase': 'final',
            'object': shipment,
            'main_form': final_form,
            'batch_fs': batch_fs,
            'stages_fs': stages_fs,
            'stages_forms': None,
            'show_batches': True,
            'read_only': False,
            'delete_url': None,
            'shipment_metrics': metrics.get_shipment_metrics(shipment.pk),
            #'cancel_url': reverse('shipments:shipment-detail', args=[shipment.pk]),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        if shipment.status != Shipment.STATUS_READY:
            raise Http404

        self.ensure_all_stages(shipment)

        final_form = FinalShipmentForm(request.POST, instance=shipment)
        stages_fs  = ShipmentStageFormSet(
            request.POST, request.FILES,
            prefix='st', instance=shipment
        )

        if final_form.is_valid() and stages_fs.is_valid():
            with transaction.atomic():
                final_form.save()
                stages_fs.save()
                done = all(
                    ss.actual_completion
                    for ss in shipment.stages.filter(stage__workflow=Stage.WORKFLOW_SHIPMENT)
                )
                if done:
                    shipment.status = Shipment.STATUS_SHIPPED
                    shipment.save()
            return redirect('shipments:shipment-detail', pk=pk)

        ctx = {
            'phase': 'final',
            'object': shipment,
            'main_form': final_form,
            'batch_fs': None,
            'stages_fs': stages_fs,
            'stages_forms': None,
            'show_batches': False,
            'read_only': False,
            'delete_url': None,
            #'cancel_url': reverse('shipments:shipment-detail', args=[shipment.pk]),
        }
        return render(request, self.template_name, ctx)
