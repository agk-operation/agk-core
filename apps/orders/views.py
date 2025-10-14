import pandas as pd
from decimal import Decimal
from django.http import HttpResponseForbidden
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import ListView, CreateView, UpdateView, View, DeleteView
from django.forms import HiddenInput, inlineformset_factory, modelformset_factory
from django.db.models import Sum, F, DecimalField, Q
from django.db import transaction
from apps.inventory.models import Item, ItemPackagingVersion
from apps.pricing.models import CustomerItemMargin
from apps.core.models import Company
from .models import Order, OrderBatch, OrderItem, BatchStage, BatchItem, Stage
from .forms import OrderItemForm, BatchItemFormSet, BatchItemForm, OrderForm, OrderBatchForm, OrderItemsImportForm, BatchStageFormSet, OrderItemPackagingForm
from agk_core import metrics

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
        status_id = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        search = self.request.GET.get('search')
        if customer:
            queryset = queryset.filter(customer__name__icontains=customer)
        
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        if status_id:
            queryset = queryset.filter(order_status_id=status_id)

        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                queryset = queryset.filter(created_at__date__gte=parsed_start)

        if start_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                queryset = queryset.filter(created_at__date__lte=parsed_end)

        if search:
            search = search.strip()
    
            filters = Q(customer__name__icontains=search)
            if search.isdigit():
                filters |= Q(id=int(search))
            queryset = queryset.filter(filters)
           
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
    template_name = 'orders/order_items_import.html'
    form_class = OrderItemsImportForm

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {
            'import_form': form,
            'order': self.order,
        })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {
                'import_form': form,
                'order': self.order,
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
                'order': self.order,
            })

        # verifica colunas
        df.columns = [c.strip().lower() for c in df.columns]
        expected = {'item', 'quantity'}
        if not expected.issubset(df.columns):
            form.add_error(None, f'Colunas inválidas, precisa ter: {expected}')
            return render(request, self.template_name, {
                'import_form': form,
                'order': self.order,
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
            oi = OrderItem.objects.create(
                order = self.order,
                item = inv_item, 
                packaging_version = inv_item.current_packaging_version(),
                quantity = qty,
                cost_price = inv_item.cost_price,   
            )
            try:
                cim = CustomerItemMargin.objects.get(
                    customer = self.order.customer,
                    item = inv_item
                )
                oi.margin = cim.margin
            except CustomerItemMargin.DoesNotExist:
                oi.margin = Decimal('0.00')
            created += 1

        if errors:
            for e in errors:
                form.add_error(None, e)
            # exibimos também quantos já foram criados, se quiser
            form.add_error(None, f'{created} itens importados antes dos erros.')
            return render(request, self.template_name, {
                'import_form': form,
                'order': self.order,
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
        initial = super().get_initial()
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
        # salva o pedido primeiro
        with transaction.atomic():
            self.object = form.save()

            # recupera o formset já ligado ao self.object
            formset = self.get_context_data()['items_formset']

            if not formset.is_valid():
                # se o formset falhar, rola tudo para trás
                return self.form_invalid(form)

            # salva os OrderItem sem commitar para ajustar campos
            saved_items = formset.save(commit=False)

            for oi in saved_items:
                # 1) garante o relacionamento com o pedido
                oi.order = self.object

                # 2) preço de custo
                oi.cost_price = oi.item.cost_price

                # 3) versão de embalagem vigente na criação
                if oi.packaging_version_id is None:
                    oi.packaging_version = (
                        oi.item
                          .packaging_versions
                          .filter(valid_to__isnull=True)
                          .order_by('-valid_from')
                          .first()
                    )

                # 4) margem de cliente-item
                if oi.margin is None:
                    try:
                        cim = CustomerItemMargin.objects.get(
                            customer=self.object.customer,
                            item=oi.item
                        )
                        oi.margin = cim.margin
                    except CustomerItemMargin.DoesNotExist:
                        oi.margin = Decimal('0.00')

                # 5) salva o OrderItem definitivo
                oi.save()

            # (se houver deletes no formset)
            formset.save_m2m()

        # limpa sessão, redireciona...
        self.request.session.pop(self.sess_data_key, None)
        self.request.session.pop(self.sess_items_key, None)
        return redirect(self.get_success_url())


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
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_locked and request.method.upper() == 'POST':
            return HttpResponseForbidden("Esta order está travada e não pode ser editada.")
        return super().dispatch(request, *args, **kwargs)
    

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
            'queryset': page_qs,
            'form_kwargs': {
                'customer': customer,
                'usd_rmb': usd_rmb,
            }
        }
        if self.request.method == 'POST':
            fs = FormSet(self.request.POST, **kwargs)
        else:
            fs = FormSet(**kwargs)

        # 4) se a order estiver travada, desabilita campos do formset
        if self.object.is_locked:
            for subform in fs.forms:
                for field in subform.fields.values():
                    field.disabled = True
                    field.widget.attrs['disabled'] = 'disabled'
                # opcional: também desabilita o checkbox de exclusão, se existir
                if 'DELETE' in subform.fields:
                    subform.fields['DELETE'].disabled = True
                    subform.fields['DELETE'].widget.attrs['disabled'] = 'disabled'

        return fs, page_obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx['form']
        # 4) lê page de GET (ou de POST, caso venha via hidden input)
        page_number = int(self.request.GET.get('page', 1) or
                          self.request.POST.get('page', 1) or
                          1
        )
        fs, page_obj = self._build_formset(form, page_number)
        ctx['order_metrics'] = metrics.get_order_metrics(self.object.pk)
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
                if oi.packaging_version_id is None:
                    oi.packaging_version = (
                        oi.item
                          .packaging_versions
                          .filter(valid_to__isnull=True)
                          .order_by('-valid_from')
                          .first()
                    )
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

            if page_obj.has_next():
                return redirect(f"{self.request.path}?page={page_number}")

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

    def dispatch(self, request, *args, **kwargs):
        # pega a order já no dispatch
        order = get_object_or_404(Order, pk=kwargs['pk'])
        if order.is_locked:
            # se estiver travada, retorna 403 (ou você pode redirecionar com mensagem)
            return HttpResponseForbidden("Esta ordem está travada e não pode ser modificada.")
        # injeta a order pra usar depois
        self.order = order
        return super().dispatch(request, *args, **kwargs)
    
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


class OrderItemPackagingListView(View):
    paginate_by   = 10
    template_name = 'orders/order_items_list.html'

    def get(self, request, order_pk):
        order = get_object_or_404(Order, pk=order_pk)
        q     = request.GET.get('q', '').strip()

        # 1) base queryset de itens do pedido
        qs = OrderItem.objects.filter(order=order).select_related('item')

        # 2) aplica busca (se houver)
        if q:
            qs = qs.filter(item__name__icontains=q)

        # 3) paginação
        paginator = Paginator(qs.order_by('pk'), self.paginate_by)
        page_obj  = paginator.get_page(request.GET.get('page'))

        # 4) monta packaging_fields: tupla (nome_do_campo, verbose_name)
        packaging_fields = [
            (f.name, f.verbose_name)
            for f in ItemPackagingVersion._meta.fields
            if f.name in ItemPackagingVersion.PACKAGING_FIELDS
        ]

        return render(request, self.template_name, {
            'order':            order,
            'order_items':      page_obj.object_list,
            'page_obj':         page_obj,
            'packaging_fields': packaging_fields,
            'q':                q,
        })


class OrderItemPackagingUpdateView(View):
    template_name = 'orders/order_items_packaging_update.html'
    paginate_by   = 10
    prefix        = 'oi'

    def get_page_number(self, request):
        # tenta GET, senão POST (hidden input)
        return request.GET.get('page') or request.POST.get('page')

    def get_queryset(self, order):
        return (
            OrderItem.objects
                     .filter(order=order)
                     .select_related('item')
                     .order_by('pk')
        )

    def get(self, request, order_pk):
        order   = get_object_or_404(Order, pk=order_pk)
        qs      = self.get_queryset(order)
        page_no = self.get_page_number(request)
        page    = Paginator(qs, self.paginate_by).get_page(page_no)

        FormSet = modelformset_factory(
            OrderItem,
            form=OrderItemPackagingForm,
            extra=0,
            can_delete=False
        )
        formset = FormSet(queryset=page.object_list, prefix=self.prefix)

        return render(request, self.template_name, {
            'order':   order,
            'formset': formset,
            'page_obj': page,
        })

    def post(self, request, order_pk):
        order   = get_object_or_404(Order, pk=order_pk)
        qs      = self.get_queryset(order)
        page_no = self.get_page_number(request)
        page    = Paginator(qs, self.paginate_by).get_page(page_no)

        FormSet = modelformset_factory(
            OrderItem,
            form=OrderItemPackagingForm,
            extra=0,
            can_delete=False
        )
        formset = FormSet(request.POST, queryset=page.object_list, prefix=self.prefix)

        if formset.is_valid():
            formset.save()
            # volta pra MESMA página de edição
            return redirect(
                f"{request.path}?page={page.number}"
            )

        # em caso de erro de validação, renderiza de novo com erros
        return render(request, self.template_name, {
            'order':   order,
            'formset': formset,
            'page_obj': page,
        })
    

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
    template_name       = 'batches/batch_list.html'
    context_object_name = 'batches'
    paginate_by         = 20

    def get_queryset(self):
        # Anota cada batch com total financeiro
        queryset = (
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
        customer = self.request.GET.get('customer')
        company_id = self.request.GET.get('company')
        status_id = self.request.GET.get('status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if customer:
            queryset = queryset.filter(customer__name__icontains=customer)
        
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        if status_id:
            queryset = queryset.filter(order_status_id=status_id)

        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                queryset = queryset.filter(created_at__date__gte=parsed_start)

        if start_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                queryset = queryset.filter(created_at__date__lte=parsed_end)

           
        return queryset


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
    template_name = 'batches/batch_create.html'
    # instanciamos a fábrica de formset aqui pra não repetir

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # formulário do cabeçalho do lote
        batch_form = OrderBatchForm(initial={'order': self.order})
        batch_form.fields['order'].widget = HiddenInput()

        # formset de itens do lote, **sem** instância salva
        # passamos um stub OrderBatch() que NÃO é usado pra filtrar nada
        items_fs = BatchItemFormSet(
            instance=OrderBatch(),  # ainda sem pk, mas só pra gerar os extras
            prefix='items'
        )

        # restringe o campo order_item a apenas itens desse pedido
        allowed = self.order.order_items.all()
        for f in items_fs.forms:
            f.fields['order_item'].queryset = allowed

        return render(request, self.template_name, {
            'order':      self.order,
            'form': batch_form,
            'items_fs':   items_fs,
        })

    def post(self, request, *args, **kwargs):
        batch_form = OrderBatchForm(request.POST)
        batch_form.fields['order'].widget = HiddenInput()

        # 1) primeiro valida só o batch_form
        if not batch_form.is_valid():
            # se o lote estourar validação, reexibe *somente* o batch_form
            items_fs = BatchItemFormSet(
                instance=OrderBatch(),
                prefix='items'
            )
            for f in items_fs.forms:
                f.fields['order_item'].queryset = self.order.order_items.all()

            return render(request, self.template_name, {
                'order': self.order,
                'form': batch_form,
                'items_fs': items_fs,
            })

        # 2) batch_form válido → salva o OrderBatch e aí sim repassa ao formset
        with transaction.atomic():
            batch = batch_form.save(commit=False)
            batch.order = self.order
            batch.save()

            # agora o formset é “atrelado” a um batch que já existe no banco
            items_fs = BatchItemFormSet(
                request.POST,
                instance=batch,
                prefix='items'
            )

            # de novo: restringe order_item
            allowed = self.order.order_items.all()
            for f in items_fs.forms:
                f.fields['order_item'].queryset = allowed

            # 3) valida o items_fs
            if not items_fs.is_valid():
                # se houver erro nos itens, reexibe junto com batch_form
                return render(request, self.template_name, {
                    'order':      self.order,
                    'batch_form': batch_form,
                    'items_fs':   items_fs,
                })

            # 4) tudo OK → salva os BatchItems
            items_fs.save()

            # 5) cria os BatchStage
            for stage in Stage.objects.all().order_by('name'):
                BatchStage.objects.create(
                    batch=batch,
                    stage=stage,
                    active=True
                )

        return redirect('orders:batch-detail',
                        order_pk=self.order.pk,
                        pk=batch.pk)
    

class OrderBatchDetailView(View):
    template_name = 'batches/batch_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(
            OrderBatch,
            pk=kwargs['pk'],
            order_id=kwargs['order_pk']
        )
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        items_fs = BatchItemFormSet(
            instance=self.batch, 
            prefix='batch_item', 
            initial=[{'order': self.batch.order}]
        )
        # restringe queryset de order_item
        allowed = self.order.order_items.all()
        for f in items_fs.forms:
            f.fields['order_item'].queryset = allowed


        return render(request, self.template_name, {
            'batch_form': OrderBatchForm(instance=self.batch),
            'items_fs': items_fs,
            'stages_fs': BatchStageFormSet(instance=self.batch, prefix='batch_stages'),
            'batch': self.batch,
            'batch_metrics': metrics.get_batch_metrics(self.batch.pk)
            }
        )

    def post(self, request, *args, **kwargs):
        items_fs = BatchItemFormSet(request.POST, instance=self.batch, prefix='batch_item')
        stages_fs = BatchStageFormSet(request.POST, instance=self.batch, prefix='batch_stages')
        
        if items_fs.is_valid() and stages_fs.is_valid(): 
            items_fs.save()
            stages_fs.save()
            
            return redirect(
                'orders:batch-detail',
                order_pk=self.batch.order.pk,
                pk=self.batch.pk
            )

        messages.error(request, 'Existem erros no formulário. Verifique os campos abaixo.')
        
        return render(request, self.template_name, {
            'items_fs': items_fs,
            'stages_fs': stages_fs,
            'batch': self.batch,
            'batch_metrics': metrics.get_batch_metrics(self.batch.pk)
            }
        )


class OrderBatchDeleteView(DeleteView):
    model = OrderBatch
    template_name = 'batches/order_batch_delete.html'
    context_object_name = 'batch'

    # 1) Garante que só vamos deletar o batch que pertence à Order correta
    def get_queryset(self):
        order_pk = self.kwargs['order_pk']
        return super().get_queryset().filter(order__pk=order_pk)

    # 2) Mensagem e redirecionamento dinâmico depois de excluir
    def get_success_url(self):
        order_pk = self.kwargs['order_pk']
        messages.success(
            self.request,
            f"Batch #{self.object.pk} deletede successfully."
        )
        # Aqui usamos reverse, não reverse_lazy, pois é em runtime
        return reverse('orders:order-edit', kwargs={'pk': order_pk})