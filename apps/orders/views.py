import pandas as pd
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import ListView, CreateView, UpdateView, View
from django.forms import HiddenInput, inlineformset_factory
from django.db.models import Sum, F, DecimalField
from apps.inventory.models import Item
from apps.pricing.models import CustomerItemMargin
from apps.core.models import Company
from .models import Order, OrderBatch, OrderItem, BatchStage, BatchItem
from .forms import OrderItemForm, OrderItemFormSet, BatchItemFormSet, OrderForm, BaseBatchItemFormSet, OrderBatchForm, OrderItemsImportForm, BatchStageForm, BatchItemForm

# —— ORDERS ——
class OrderListView(ListView):  
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer')
        customer = self.request.GET.get('customer')
        company_id = self.request.GET.get('company')
        if customer:
            queryset = queryset.filter(customer__name__icontains=customer)
        
        if company_id:
            queryset = queryset.filter(company_id=company_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # lista todos os clientes para o filtro
        ctx['companies'] = Company.objects.order_by('name')
        ctx['selected_company']  = self.request.GET.get('company')
        return ctx


class OrderItemsImportView(View):
    """
    Importa linhas de CSV/XLSX criando OrderItem em um Order já salvo.
    """
    template_name     = 'orders/order_items_import.html'
    form_class        = OrderItemsImportForm

    def dispatch(self, request, *args, **kwargs):
        # carrega a ordem existente
        self.order = get_object_or_404(Order, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {
            'import_form': form,
            'order':       self.order,
        })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {
                'import_form': form,
                'order':       self.order,
            })

        # lê o arquivo
        file = form.cleaned_data['file']
        try:
            df = (pd.read_csv(file) if file.name.lower().endswith('.csv')
                  else pd.read_excel(file))
        except Exception as e:
            form.add_error(None, f'Erro ao ler o arquivo: {e}')
            return render(request, self.template_name, {
                'import_form': form,
                'order':       self.order,
            })

        # verifica colunas
        df.columns = [c.strip().lower() for c in df.columns]
        expected = {'item', 'quantity'}
        if not expected.issubset(df.columns):
            form.add_error(None, f'Colunas inválidas, precisa ter: {expected}')
            return render(request, self.template_name, {
                'import_form': form,
                'order':       self.order,
            })

        # valida e cria
        errors = []
        created = 0
        for idx, row in df.iterrows():
            num = idx + 1
            name = str(row['item']).strip()
            try:
                inv_item = Item.objects.get(name__iexact=name)
            except Item.DoesNotExist:
                errors.append(f'Linha {num}: item "{name}" não existe.')
                continue
            try:
                qty = float(row['quantity'])
                if qty <= 0:
                    raise ValueError
            except Exception:
                errors.append(f'Linha {num}: quantidade inválida.')
                continue

            # tudo ok, cria o OrderItem
            OrderItem.objects.create(
                order    = self.order,
                item     = inv_item,
                quantity = qty
            )
            created += 1

        if errors:
            for e in errors:
                form.add_error(None, e)
            # exibimos também quantos já foram criados, se quiser
            form.add_error(None, f'{created} itens importados antes dos erros.')
            return render(request, self.template_name, {
                'import_form': form,
                'order':       self.order,
            })

        # sucesso: voltar para edição da ordem
        return redirect('orders:order-edit', self.order.pk)


class NewOrderItemsImportView(View):
    template_name      = 'orders/new_order_item_import.html'
    session_data_key   = 'new_order_data'
    session_items_key  = 'new_order_items'

    def get(self, request):
        # só exibe o template de upload, já pode mostrar order_data em texto
        import_form = OrderItemsImportForm()
        order_data  = request.session.get(self.session_data_key, {})
        return render(request, self.template_name, {
            'import_form': import_form,
            'order_data':  order_data,
        })

    def post(self, request):
        # Se não veio arquivo, estamos na 1ª etapa: cachear os hidden inputs
        if 'file' not in request.FILES:
            return self._cache_order_data(request)

        # se veio arquivo, processa a importação
        return self._handle_file_upload(request)

    def _cache_order_data(self, request):
        data = {}
        for field in ('customer','exporter','company'):
            if val := request.POST.get(field):
                data[field] = val
        request.session[self.session_data_key] = data

        # reexibe o mesmo template, agora com order_data em sessão
        import_form = OrderItemsImportForm()
        return render(request, self.template_name, {
            'import_form': import_form,
            'order_data':  data,
        })

    def _handle_file_upload(self, request):
        import_form = OrderItemsImportForm(request.POST, request.FILES)
        if not import_form.is_valid():
            return render(request, self.template_name, {
                'import_form': import_form,
                'order_data':  request.session.get(self.session_data_key, {}),
            })

        file = import_form.cleaned_data['file']
        try:
            df = (pd.read_csv(file)
                  if file.name.lower().endswith('.csv')
                  else pd.read_excel(file))
        except Exception as e:
            import_form.add_error(None, f'Erro ao ler o arquivo: {e}')
            return render(request, self.template_name, {
                'import_form': import_form,
                'order_data':  request.session.get(self.session_data_key, {}),
            })

        # valida cabeçalho
        df.columns = [c.strip().lower() for c in df.columns]
        expected = {'item','quantity'}
        if not expected.issubset(df.columns):
            import_form.add_error(
                None,
                f'Colunas inválidas. O arquivo deve conter: {expected}'
            )
            return render(request, self.template_name, {
                'import_form': import_form,
                'order_data':  request.session.get(self.session_data_key, {}),
            })

        # valida conteúdo linha a linha
        errors = []
        seen = set()
        for idx, row in df.iterrows():
            linha = idx + 1
            name  = str(row['item']).strip()
            try:
                item = Item.objects.get(name__iexact=name)
            except Item.DoesNotExist:
                errors.append(f'Linha {linha}: produto "{name}" não encontrado.')
                continue

            key = name.lower()
            if key in seen:
                errors.append(f'Linha {linha}: produto "{name}" duplicado.')
            else:
                seen.add(key)

            try:
                qty = float(row['quantity'])
                if qty <= 0:
                    errors.append(f'Linha {linha}: quantidade deve ser > 0.')
            except Exception:
                errors.append(f'Linha {linha}: quantidade inválida.')

        if errors:
            for err in errors:
                import_form.add_error(None, err)
            return render(request, self.template_name, {
                'import_form': import_form,
                'order_data':  request.session.get(self.session_data_key, {}),
            })

        # monta initial_items e grava na sessão
        initial_items = [
            {'item': Item.objects.get(name__iexact=str(row['item']).strip()).pk,
             'quantity': float(row['quantity'])}
            for _, row in df.iterrows()
        ]
        request.session[self.session_items_key] = initial_items

        return redirect('orders:order-add')


@method_decorator(never_cache, name='dispatch')
class OrderCreateView(CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:order-list')
    sess_data_key = NewOrderItemsImportView.session_data_key
    sess_items_key = NewOrderItemsImportView.session_items_key
    PAGINATE_BY = 5
    FORMSET_PREFIX  = 'orderitems'

    def get_initial(self):
        initial    = super().get_initial()
        order_data = self.request.session.pop(self.sess_data_key, None)
        if order_data:
            initial.update(order_data)
        return initial

    def get_formset_class(self):
        initial_items = self.request.session.get(self.sess_items_key, [])
        return inlineformset_factory(
            Order,
            OrderItem,
            form=OrderItemForm,
            extra=max(1, len(initial_items)),
            can_delete=True
        )
    
    def _build_formset(self, form):
        if form.is_bound and form.is_valid():
            customer = form.cleaned_data.get('customer')
        else:
            customer = form.initial.get('customer')

        FormSet = self.get_formset_class()
        if self.request.method == 'POST':
            fs = FormSet(
                self.request.POST,
                instance=self.object or Order(),
                prefix=self.FORMSET_PREFIX,
                form_kwargs={'customer': customer}
            )
        else:
            fs = FormSet(
                instance=self.object or Order(),
                prefix=self.FORMSET_PREFIX,
                initial=self.request.session.get(self.sess_items_key, []),
                form_kwargs={'customer': customer}
            )
        return fs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fs = self._build_formset(context['form'])
        paginator = Paginator(fs.forms, self.PAGINATE_BY)
        page_number = (
            self.request.POST.get('page') \
            or self.request.GET.get('page') \
            or 1
        )
        page_obj = paginator.get_page(page_number)
        context['items_formset'] = fs
        context['items_page'] = page_obj
        return context
    
    def form_valid(self, form):
        self.object = form.save()
        formset = self.get_context_data()['items_formset']
        if formset.is_valid():
            saved_items = formset.save(commit=False)
            for oi in saved_items:
                oi.cost_price = oi.item.cost_price
                if oi.margin is None:
                    try:
                        cim = CustomerItemMargin.objects.get(
                            customer=self.object.customer,
                            item=oi.item
                        )
                        oi.margin = cim.margin
                    except CustomerItemMargin.DoesNotExist:
                        oi.margin = Decimal('0.00')
                oi.save()
            self.request.session.pop(self.sess_data_key, None)
            self.request.session.pop(self.sess_items_key, None)
            
            return redirect(self.success_url)

        return self.form_invalid(form)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {
            'form': form,
            'items_formset': self.get_context_data()['items_formset'],
        })
    
    def get_success_url(self):
        if self.request.POST.get('action') == 'save_continue':
            return reverse('orders:order-edit', args=[self.object.pk])
        return super().get_success_url()


class OrderUpdateView(UpdateView):
    model           = Order
    form_class      = OrderForm
    template_name   = 'orders/order_form.html'
    success_url     = reverse_lazy('orders:order-list')
    FORMSET_PREFIX  = 'orderitems'
    PAGINATE_BY     = 10

    def get_orderitems_qs(self):
        return OrderItem.objects.filter(order=self.object).order_by('pk')

    def get_formset_class(self):
        return inlineformset_factory(
            Order,
            OrderItem,
            form=OrderItemForm,
            extra=0,
            can_delete=True
        )

    def _build_formset(self, form, page_number):
        # 1) extrai customer e usd_rmb do form pai
        if form.is_bound and form.is_valid():
            customer = form.cleaned_data.get('customer')
            usd_rmb = form.cleaned_data.get('usd_rmb') or Decimal('0')
        else:
            customer = form.initial.get('customer')
            usd_rmb = form.initial.get('usd_rmb') or Decimal('0')

        # 2) determina quais PKs pertencem à fatia atual
        full_qs = self.get_orderitems_qs()
        paginator = Paginator(full_qs, self.PAGINATE_BY)
        page_obj = paginator.get_page(page_number)
        slice_pks = [oi.pk for oi in page_obj.object_list]
        page_qs = full_qs.filter(pk__in=slice_pks)
        # 3) monta o formset apenas com esses itens
        FormSet = self.get_formset_class()
        kwargs = {
            'instance': self.object,
            'prefix': self.FORMSET_PREFIX,
            'queryset':  page_qs,
            'form_kwargs': {
                'customer': customer,
                'usd_rmb': usd_rmb,
            }
        }       
        if self.request.method == 'POST':
            return FormSet(self.request.POST, **kwargs), page_obj

        return FormSet(**kwargs), page_obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx['form']
        # 4) lê page de GET (ou de POST, caso venha via hidden input)
        page_number = int(self.request.GET.get('page', 1) or
                          self.request.POST.get('page', 1) or
                          1
        )
        fs, page_obj = self._build_formset(form, page_number)

        ctx['items_formset'] = fs
        ctx['items_page'] = page_obj
        return ctx

    def form_valid(self, form):
        # 5) salva a Order
        self.object = form.save()

        # 6) pega o formset da página e salva apenas aqueles itens
        page_number = int(self.request.POST.get('page', 1))
        fs, page_obj = self._build_formset(form, page_number)

        if fs.is_valid():
            saved_items = fs.save(commit=False)
            # itens marcados para exclusão
            for oi in fs.deleted_objects:
                oi.delete()

            for oi in saved_items:
                # aplica sempre o cost_price
                oi.cost_price = oi.item.cost_price
                # margem padrão só para itens novos sem margin
                if oi.pk is None and oi.margin is None:
                    try:
                        cim = CustomerItemMargin.objects.get(
                            customer=self.object.customer,
                            item=oi.item
                        )
                        oi.margin = cim.margin
                    except CustomerItemMargin.DoesNotExist:
                        oi.margin = Decimal('0.00')
                oi.save()

            # se tiver próxima página, segue para ela
            if page_obj.has_next():
                return redirect(f"{self.request.path}?page={page_number+1}")

            # senão, acabou → volta para a lista
            return redirect(self.get_success_url())

        return self.form_invalid(form)

    def form_invalid(self, form):
        # garante form + formset(paginado) com erros
        context = self.get_context_data(form=form)
        return render(self.request, self.template_name, context)
    
    def get_success_url(self):
        if self.request.POST.get('action') == 'save_continue':
            return reverse('orders:order-edit', args=[self.object.pk])
        return super().get_success_url()


class UpdateOrderMarginsView(View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        updated = 0

        for oi in order.order_items.all():
            if oi.margin is None:
                cim = CustomerItemMargin.objects.filter(
                    customer=order.customer,
                    item=oi.item
                ).first()
                if cim:
                    oi.margin = cim.margin
                    oi.save()
                    updated += 1

        messages.success(request,
            f"{updated} item(s) tiveram a margem padrão aplicada."
        )
        return redirect('orders:order-edit', pk=order.pk)
    

# —— BATCHES ——
class AllBatchListView(ListView):
    """
    Lista *todos* os lotes de todos os pedidos, mostrando:
     - batch_code
     - created_at
     - order.customer
     - total_value = soma(quantity * item.price) de cada BatchItem
    """
    model               = OrderBatch
    template_name       = 'orders/batch_list.html'
    context_object_name = 'batches'
    paginate_by         = 20

    def get_queryset(self):
        # Anota cada batch com total financeiro
        qs = (
            OrderBatch.objects
            .select_related('order__customer')
            .annotate(
                total_value=Sum(
                    F('batch_items__quantity') *
                    F('batch_items__order_item__item__selling_price'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                )
            )
        )
        return qs


class OrderBatchListView(ListView):
    model = OrderBatch
    template_name = 'orders/order_batch_list.html'
    context_object_name = 'batches'
    paginate_by = 20

    def get_queryset(self):
        order_pk = self.kwargs.get('order_pk')
        return OrderBatch.objects.filter(order_id=order_pk)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = get_object_or_404(Order, pk=self.kwargs['order_pk'])
        return ctx


class OrderBatchCreateView(View):
    template_name = 'orders/batch_create.html'
    ItemFS = inlineformset_factory(
        OrderBatch, BatchItem,
        form=BatchItemForm,
        formset=BaseBatchItemFormSet,
        extra=1, can_delete=True
    )

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = OrderBatchForm(initial={'order': self.order})
        form.fields['order'].widget = HiddenInput()

        # instância nova, mas já “ligada” à ordem
        items_fs = self.ItemFS(instance=OrderBatch(order=self.order))

        allowed = self.order.order_items.all()
        for f in items_fs.forms:
            f.fields['order_item'].queryset = allowed
        items_fs.empty_form.fields['order_item'].queryset = allowed

        return render(request, self.template_name, {
            'form': form,
            'items_fs': items_fs,
            'order': self.order,
        })

    def post(self, request, *args, **kwargs):
        form = OrderBatchForm(request.POST)
        form.fields['order'].widget = HiddenInput()

        items_fs = self.ItemFS(
            request.POST,
            instance=OrderBatch(order=self.order)
        )

        allowed = self.order.order_items.all()
        for f in items_fs.forms:
            f.fields['order_item'].queryset = allowed
        items_fs.empty_form.fields['order_item'].queryset = allowed

        if form.is_valid() and items_fs.is_valid():
            batch = form.save(commit=False)
            batch.order = self.order
            batch.save()
            items_fs.instance = batch
            items_fs.save()
            for stage_name in DEFAULT_BATCH_STAGES:
                BatchStage.objects.create(batch=batch, name=stage_name)
            return redirect('orders:batch-detail',
                            order_pk=self.order.pk, pk=batch.pk)

        return render(request, self.template_name, {
            'form': form,
            'items_fs': items_fs,
            'order': self.order,
        })


DEFAULT_BATCH_STAGES = [
    'Order',
    'PO',
    'PI',
    'Deposit Payment',
    'Packing Confirm.',
    'Condition Confirm.',
    'Place the Order',
    'ETD',
    'Balance Payment',
    'Pre-Loading'
]

class OrderBatchDetailView(View):
    template_name = 'orders/batch_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(
            OrderBatch,
            pk=kwargs['pk'],
            order_id=kwargs['order_pk']
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._build_context())

    def post(self, request, *args, **kwargs):
        ctx = self._build_context()
        form = ctx['form']

        # atualiza dados principais
        form = OrderBatchForm(request.POST, instance=self.batch)
        if not form.is_valid():
            ctx['form'] = form
            return render(request, self.template_name, ctx)

        # processa cada etapa fixa
        for idx, name in enumerate(DEFAULT_BATCH_STAGES):
            prefix = f'stages-{idx}'
            active = request.POST.get(f'{prefix}-active') == 'on'
            stage_id = request.POST.get(f'{prefix}-id')
            est = request.POST.get(f'{prefix}-estimated') or None
            act = request.POST.get(f'{prefix}-actual') or None

            if active and stage_id:
                # update existente
                st = BatchStage.objects.get(pk=stage_id, batch=self.batch)
                st.estimated_completion = est
                st.actual_completion = act
                st.save()
            elif active and not stage_id:
                # criar nova
                BatchStage.objects.create(
                    batch=self.batch,
                    name=name,
                    estimated_completion=est,
                    actual_completion=act
                )
            elif not active and stage_id:
                # remove
                BatchStage.objects.filter(pk=stage_id, batch=self.batch).delete()

        form.save()
        return redirect('orders:order-edit', self.batch.order.pk)

    def _build_context(self):
        # dados principais
        form = OrderBatchForm(instance=self.batch)
        items_fs = BatchItemFormSet(instance=self.batch)

        # prepara o dicionário das etapas já salvas
        existing = {s.name: s for s in self.batch.stages.all()}

        # constrói um list de dicts para template
        stage_rows = []
        for idx, name in enumerate(DEFAULT_BATCH_STAGES):
            st = existing.get(name)
            stage_rows.append({
                'idx': idx,
                'name': name,
                'id': getattr(st, 'pk', ''),
                'estimated': getattr(st, 'estimated_completion', ''),
                'actual':    getattr(st, 'actual_completion', ''),
                'active':   bool(st),
            })

        return {
            'batch':    self.batch,
            'form':     form,
            'items_fs': items_fs,
            'stage_rows': stage_rows,
        }