import pandas as pd
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View
from django.forms import HiddenInput, inlineformset_factory
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from apps.inventory.models import Item
from apps.core.models import Customer, Company
from .models import Order, OrderBatch, OrderItem
from .forms import OrderItemForm, OrderItemFormSet, BatchItemFormSet, OrderForm, OrderBatchForm, OrderItemsImportForm

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


@method_decorator(never_cache, name='dispatch')
class OrderCreateView(CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:order-list')

    # atalho para as chaves de sessão
    sess_data_key = NewOrderItemsImportView.session_data_key
    sess_items_key = NewOrderItemsImportView.session_items_key

    # só pré-enche o form principal se vier da importação
    def get_initial(self):
        initial = super().get_initial()
        if data := self.request.session.pop(self.sess_data_key, None):
            initial.update(data)
        return initial

    # sempre monta o formset, puxando itens da sessão ou criando um vazio
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial_items = self.request.session.pop(self.sess_items_key, [])
        # dynamic extra: ao menos 1 form, ou tantos quantos vieram importados
        extra = max(1, len(initial_items))
        FormSet = inlineformset_factory(
            Order, OrderItem,
            form=OrderItemForm,
            extra=extra,
            can_delete=True
        )
        context['items_formset'] = FormSet(
            instance=self.object or Order(),
            initial=initial_items
        )
        return context

    # valida juntos form + formset antes de tudo
    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        form_set = OrderItemFormSet(request.POST, instance=Order())

        if form.is_valid() and form_set.is_valid():
            self.object = form.save()
            form_set.instance = self.object
            form_set.save()
            # limpa sessão de import
            request.session.pop(self.sess_data_key,  None)
            request.session.pop(self.sess_items_key, None)
            return redirect(self.success_url)

        return render(request, self.template_name, {
            'form': form,
            'items_formset': form_set,
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
        # Cria um OrderBatch “temporário” para o formset
        temp_batch = OrderBatch(order=self.order)
        # Instancia o formset com POST se for o caso
        fs = BatchItemFormSet(self.request.POST or None, instance=temp_batch)
        # 1) Atualiza a base do formset para que o empty_form use o limited_qs
        fs.form.base_fields['order_item'].queryset = self.order.order_items.all()
        # 2) Atualiza cada subform já renderizado
        for form in fs.forms:
            form.fields['order_item'].queryset = self.order.order_items.all()

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
