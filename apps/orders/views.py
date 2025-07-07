import pandas as pd
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View
from django.forms import HiddenInput, inlineformset_factory
from django.db.models import Sum, F, DecimalField
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from apps.inventory.models import Item, CustomerItemMargin
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
        # captura e armazena customer & due_date
        order_data = {}
        for field in ('customer', 'exporter', 'company'):
            if val := request.GET.get(field):
                order_data[field] = val
        request.session[self.session_data_key] = order_data

        # exibe form de import com dados principais como texto
        import_form = OrderItemsImportForm()
        return render(request, self.template_name, {
            'import_form': import_form,
        })

    def post(self, request):
        import_form = OrderItemsImportForm(request.POST, request.FILES)

        if not import_form.is_valid():
            return render(request, self.template_name, {
                'import_form': import_form,
            })

        # 1) Lê arquivo
        file = import_form.cleaned_data['file']
        try:
            df = (
                pd.read_csv(file)
                if file.name.lower().endswith('.csv')
                else pd.read_excel(file)
            )
        except Exception as e:
            import_form.add_error(None, f'Erro ao ler o arquivo: {e}')
            return render(request, self.template_name, {
                'import_form': import_form,
            })

        # 2) Checa cabeçalho
        df.columns = [c.strip().lower() for c in df.columns]
        expected = {'item', 'quantity'}
        if not expected.issubset(df.columns):
            import_form.add_error(
                None,
                f'Colunas inválidas. O arquivo deve conter: {expected}'
            )
            return render(request, self.template_name, {
                'import_form': import_form,
            })

        # 3) Valida conteúdo linha a linha
        errors = []
        seen = set()
        for idx, row in df.iterrows():
            linha = idx + 1
            item_name = str(row['item']).strip()

            # existe o produto?
            try:
                item = Item.objects.get(name__iexact=item_name)
            except Item.DoesNotExist:
                errors.append(f'Linha {linha}: produto "{item_name}" não encontrado.')
                continue

            # não duplicar
            key = item_name.lower()
            if key in seen:
                errors.append(f'Linha {linha}: produto "{item_name}" duplicado.')
            else:
                seen.add(key)

            # quantidade > 0
            try:
                qty = float(row['quantity'])
                if qty <= 0:
                    errors.append(f'Linha {linha}: quantidade deve ser > 0.')
            except Exception:
                errors.append(f'Linha {linha}: quantidade inválida.')


        # se encontrou erros "fatais", reexibe form com mensagens
        if errors:
            for err in errors:
                import_form.add_error(None, err)
            return render(request, self.template_name, {
                'import_form': import_form,
            })

        # 4) Monta initial_items e armazena na sessão
        initial_items = []
        for idx, row in df.iterrows():
            item = Item.objects.get(name__iexact=str(row['item']).strip())
            initial_items.append({
                'item':    item.pk,
                'quantity':   float(row['quantity']),
            })

        request.session[self.session_items_key] = initial_items
        return redirect('orders:order-add')


class OrderCreateView(CreateView):
    model         = Order
    form_class    = OrderForm
    template_name = 'orders/order_form.html'
    success_url   = reverse_lazy('orders:order-list')
    sess_data_key  = NewOrderItemsImportView.session_data_key
    sess_items_key = NewOrderItemsImportView.session_items_key
    FORMSET_PREFIX = 'orderitems'

    def get_formset_class(self):
        initial_items = self.request.session.get(self.sess_items_key, [])
        extra = max(1, len(initial_items))
        return inlineformset_factory(
            Order,
            OrderItem,
            form=OrderItemForm,
            extra=extra,
            can_delete=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')

        if form and form.is_bound and form.is_valid():
            customer = form.cleaned_data.get('customer')
        else:
            customer = form.initial.get('customer') if form else None

        FormSet = self.get_formset_class()
        context['items_formset'] = FormSet(
            self.request.POST or None,
            instance=self.object or Order(),
            prefix=self.FORMSET_PREFIX,
            form_kwargs={'customer': customer}
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        FormSet = self.get_formset_class()
        formset = FormSet(
            request.POST,
            instance=Order(),
            prefix=self.FORMSET_PREFIX,
            form_kwargs={'customer': form.cleaned_data.get('customer') if form.is_valid() else None}
        )

        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            items = formset.save(commit=False)
            for oi in items:
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
            request.session.pop(self.sess_data_key,  None)
            request.session.pop(self.sess_items_key, None)
            return redirect(self.success_url)
        
        return render(request, self.template_name, {
            'form': form,
            'items_formset': formset,
        })


class OrderUpdateView(UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:order-list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items_formset'] = OrderItemFormSet(self.request.POST, instance=self.object)
        else:
            data['items_formset'] = OrderItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items_fs = context['items_formset']
        if items_fs.is_valid():
            self.object = form.save()
            items_fs.instance = self.object
            items_fs.save()
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

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