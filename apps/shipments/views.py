from django.shortcuts import get_object_or_404, render, redirect
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
    template_name = 'shipments/pre_shipment_list.html'
    context_object_name = 'pre_shipments'

    def get_queryset(self):
        return Shipment.objects.filter(status=Shipment.STATUS_PRELOADING)


class PreShipmentCreateView(View):
    template_name = 'shipments/pre_shipment_form.html'

    

    def get(self, request):
        form = ShipmentForm()
        batch_fs = ShipmentBatchFormSet(prefix='sb')

        # 1) Carrega os stages
        pre_stages = list(
            Stage.objects
                 .filter(workflow=Stage.WORKFLOW_PRELOADING)
                 .order_by('sort_order')
        )

        fake_shipment = Shipment()
        # 2) Cria um formulário por etapa, com initial + stage associado
        stage_forms = []
        for stage in pre_stages:
            instance = ShipmentStage(stage=stage, shipment=fake_shipment)
            form_stage = ShipmentStageForm(
                prefix=f"st-{stage.pk}",
                initial={'stage': stage.pk},
                instance=instance
            )
            stage_forms.append({'stage': stage, 'form': form_stage})

        return render(request, self.template_name, {
            'form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,  # não estamos usando formset aqui
            'stages_data': stage_forms,
            'read_only': False,
            'is_create': True,
        })

    def post(self, request):
        form = ShipmentForm(request.POST)
        batch_fs = ShipmentBatchFormSet(request.POST, request.FILES, prefix='sb')

        # 1) Carrega os stages na ordem correta
        pre_stages = list(
            Stage.objects
                .filter(workflow=Stage.WORKFLOW_PRELOADING)
                .order_by('sort_order')
        )

        fake_shipment = Shipment()  # usado para construção inicial

        # 2) Constrói os formulários de etapa bindados
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

        # 3) Validação completa
        if form.is_valid() and batch_fs.is_valid() and forms_valid:
            with transaction.atomic():
                shipment = form.save(commit=False)

                # Salva dados dinâmicos de etapas no shipment
                for form_stage in stage_form_objects:
                    stage = form_stage.instance.stage
                    for cfg in stage.field_configs.all():
                        fname = cfg.field_name
                        if fname in form_stage.cleaned_data:
                            setattr(shipment, fname, form_stage.cleaned_data[fname])

                shipment.status = Shipment.STATUS_PRELOADING
                shipment.save()

                # Salva os batches
                batch_fs.instance = shipment
                batch_fs.save()

                # Cria as etapas
                for form_stage in stage_form_objects:
                    new_stage = form_stage.save(commit=False)
                    new_stage.shipment = shipment
                    new_stage.save()

            return redirect('shipments:pre_shipment-edit', pk=shipment.pk)

        # 4) Se inválido, reexibe o form
        return render(request, self.template_name, {
            'form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_data': stage_forms,
            'read_only': False,
            'is_create': True,
        })
    

class PreShipmentUpdateView(View):
    template_name = 'shipments/pre_shipment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.shipment = get_object_or_404(
            Shipment,
            pk=kwargs['pk']
        )
        return super().dispatch(request, *args, **kwargs)

    def ensure_pre_stages(self, shipment):
        """
        Garante que para cada Stage de workflow PRE exista um ShipmentStage.
        """
        existing = { ss.stage_id for ss in shipment.stages.all() }
        qs = Stage.objects.filter(workflow=Stage.WORKFLOW_PRELOADING).order_by('sort_order')
        for st in qs:
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)

        # Garante que todas as etapas necessárias existem
        self.ensure_pre_stages(shipment)

        form  = ShipmentForm(instance=shipment)
        batch_fs = ShipmentBatchFormSet(instance=shipment, prefix='sb')

        # 1) Busca as etapas e os respectivos ShipmentStages
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

        return render(request, self.template_name, {
            'form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_data': stage_forms,
            'read_only': False,
            'is_create': False,
            'shipment_metrics': metrics.get_shipment_metrics(self.shipment.pk)
        })

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)

        self.ensure_pre_stages(shipment)

        form = ShipmentForm(request.POST, instance=shipment)
        batch_fs = ShipmentBatchFormSet(request.POST, prefix='sb', instance=shipment)

        # 1) Etapas do workflow
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

        # Validação combinada
        if form.is_valid() and batch_fs.is_valid() and forms_valid:
            with transaction.atomic():
                shipment = form.save(commit=False)
                # Atualiza os campos dinâmicos no objeto `shipment`
                for form_stage in stage_form_objects:
                    stage = form_stage.instance.stage
                    for cfg in stage.field_configs.all():
                        fname = cfg.field_name
                        if fname in form_stage.cleaned_data:
                            setattr(shipment, fname, form_stage.cleaned_data[fname])
                batch_fs.save()
                for form_stage in stage_form_objects:
                    form_stage.save()
                if all(
                    ss.actual_completion
                    for ss in shipment.stages.filter(stage__workflow=Stage.WORKFLOW_PRELOADING)
                ):
                    shipment.status = Shipment.STATUS_READY
                
                shipment.save()
                    

            return redirect('shipments:pre_shipment-edit', pk=shipment.pk)

        # Se inválido, reexibe
        return render(request, self.template_name, {
            'form': form,
            'batch_fs': batch_fs,
            'stages_fs': None,
            'stages_data': stage_forms,
            'read_only': False,
            'is_create': False,
            'shipment_metrics': metrics.get_shipment_metrics(self.shipment.pk)
        })


class PreShipmentDeleteView(View):
    """Excluir um Shipment em PRE-LOADING."""
    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, status=Shipment.STATUS_PRELOADING)
        shipment.delete()
        return redirect('shipments:pre_shipment-list')


# ───────────────────────────────────────────────────────────
#  Views para a fase de SHIPMENT FINAL (status = RDY ou SHP)
# ───────────────────────────────────────────────────────────



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
    Exibe as etapas (pré-embarque para leitura e final para edição).
    Ao completar todas as etapas de SHIPMENT, define status=RDY.
    """
    template_name = 'shipments/shipment_stages.html'

    def ensure_all_stages(self, shipment):
        """Garante que existam ShipmentStage para todas as Stages PRE e SHIPMENT."""
        existing = {ss.stage_id for ss in shipment.stages.all()}
        # pré‐loading (leitura apenas)
        for st in Stage.objects.filter(workflow=Stage.WORKFLOW_PRELOADING):
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)
        # final shipment (edição)
        for st in Stage.objects.filter(workflow=Stage.WORKFLOW_SHIPMENT):
            if st.pk not in existing:
                ShipmentStage.objects.create(shipment=shipment, stage=st)

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        # só permite editar final se está READY
        if shipment.status != Shipment.STATUS_READY:
            raise Http404("Este shipment não está pronto para edição final.")
        self.ensure_all_stages(shipment)

        # Form de campos finais
        final_form = FinalShipmentForm(instance=shipment)
        # FormSet de etapas (já inclui todas as PRE e SHIPMENT)
        stages_fs  = ShipmentStageFormSet(instance=shipment, prefix='st')
        return render(request, self.template_name, {
            'shipment':   shipment,
            'final_form': final_form,
            'stages_fs':  stages_fs,
        })

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
                # se todas as etapas de workflow SHIPMENT foram concluídas:
                done = all(
                    ss.actual_completion
                    for ss in shipment.stages.filter(workflow=Stage.WORKFLOW_SHIPMENT)
                )
                if done:
                    shipment.status = Shipment.STATUS_SHIPPED
                    shipment.save()
            return redirect('shipments:shipment-detail', pk=pk)

        return render(request, self.template_name, {
            'shipment':   shipment,
            'final_form': final_form,
            'stages_fs':  stages_fs,
        })
