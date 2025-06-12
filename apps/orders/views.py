import pandas as pd
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View
from django.forms import HiddenInput, inlineformset_factory
from apps.inventory.models import Item
from apps.core.models import Customer, Company
from .models import Order, OrderBatch, OrderItem
from .forms import OrderItemFormSet, BatchItemFormSet, OrderForm, OrderBatchForm, OrderItemsImportForm

# —— ORDERS ——
class OrderListView(ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer')
        customer = self.request.GET.get('customer')
        if customer:
            queryset = queryset.filter(customer__name__icontains=customer)

        return  queryset 

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # lista todos os clientes para o filtro
        ctx['company'] = Company.objects.order_by('name')
        return ctx   


class OrderCreateView(CreateView):
    model         = Order
    form_class    = OrderForm
    template_name = 'orders/order_form.html'
    success_url   = reverse_lazy('orders:order-list')

    def get_initial(self):
        initial = super().get_initial()
        # 1) Pega dados principais da sessão, se houver
        order_data = self.request.session.pop(
            NewOrderItemsImportView.session_data_key, None
        )
        if order_data:
            initial.update(order_data)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 2) Prepara o formset de itens
        # sempre usando o formset importado (não recriando com inlineformset_factory)
        if self.request.method == 'POST':
            # Form POST: validar os dados enviados
            context['items_formset'] = OrderItemFormSet(
                self.request.POST,
                instance=self.object or Order()
            )
        else:
            # GET: carrega initial vindo da sessão, se existir
            initial_items = self.request.session.pop(
                NewOrderItemsImportView.session_items_key, None
            )
            if initial_items:
                context['items_formset'] = OrderItemFormSet(
                    instance=Order(),
                    initial=initial_items
                )
            else:
                context['items_formset'] = OrderItemFormSet(
                    instance=Order()
                )

        return context

    def form_valid(self, form):
        # salva a order primeiro
        self.object = form.save()

        # 3) Valida e salva o formset usando o mesmo OrderItemFormSet
        formset = OrderItemFormSet(
            self.request.POST,
            instance=self.object
        )
        if formset.is_valid():
            formset.save()
            return redirect(self.get_success_url())

        # se o formset falhar, renderiza o form principal com erros
        return self.form_invalid(form)


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
class OrderBatchListView(ListView):
    model = OrderBatch
    template_name = 'orders/batch_list.html'
    context_object_name = 'batches'
    paginate_by = 20

    def get_queryset(self):
        order_pk = self.kwargs.get('order_pk')
        return OrderBatch.objects.filter(order_id=order_pk)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['order'] = get_object_or_404(Order, pk=self.kwargs['order_pk'])
        return ctx

class OrderBatchCreateView(CreateView):
    model = OrderBatch
    form_class    = OrderBatchForm
    template_name = 'orders/batch_form.html'

    def dispatch(self, request, *args, **kwargs):
        # captura a ordem pela PK da URL
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # já preenche o campo order no form do batch
        return {'order': self.order}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # esconde o campo order (já está definido)
        form.fields['order'].widget = HiddenInput()
        return form

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['order'] = self.order
        if self.request.POST:
            fs = BatchItemFormSet(self.request.POST, instance=self.object)
        else:
            fs = BatchItemFormSet(instance=self.object)
        # aqui limitamos a queryset dos order_item
        for f in fs.forms:
            f.fields['order_item'].queryset = self.order.order_items.all()
        data['batch_items_fs'] = fs
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        fs = context['batch_items_fs']
        if fs.is_valid():
            # salva o batch com a ordem associada
            batch = form.save(commit=False)
            batch.order = self.order
            batch.save()
            # salva itens do batch
            fs.instance = batch
            fs.save()
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        # volta à lista de lotes da ordem
        return reverse_lazy('orders:order-edit', args=[self.order.pk])
