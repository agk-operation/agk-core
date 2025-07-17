from django.views.generic import CreateView, DetailView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from apps.orders.models import Order
from .models import ProformaInvoice
from .forms import ProformaInvoiceForm


class ProformaInvoiceCreateView(CreateView):
    model = ProformaInvoice
    form_class = ProformaInvoiceForm
    template_name = 'finance/proforma_invoice_form.html'

    def dispatch(self, request, *args, **kwargs):
        # carrega a Order antes de tudo
        self.order = get_object_or_404(Order, pk=kwargs['order_pk'])
        # se já existe PI, vai direto ao detalhe
        if hasattr(self.order, 'proforma'):
            return redirect('finance:proforma-detail', pk=self.order.proforma.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # expõe a order no contexto para usar em form template
        context['order'] = self.order
        return context

    def form_valid(self, form):
        pi = form.save(commit=False)
        pi.order = self.order
        pi.save()

        # tranca a order
        self.order.is_locked = True
        self.order.save()

        # gera e salva o PDF
        pi.generate_pdf()

        # redireciona sempre ao detail com pk válido
        return super().form_valid(form)

    def get_success_url(self):
        # aqui object é a PI recém-criada
        return reverse('finance:proforma-detail', args=[self.object.pk])


class ProformaInvoiceDetailView(DetailView):
    model = ProformaInvoice
    template_name = 'finance/proforma_invoice_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # traz todos os OrderItem ligados à Order da PI
        ctx['order_items'] = (
            self.object.order
                .order_items
                .select_related('item')  # embarca o FK “item” pra não fazer N+1
                .all()
        )
        return ctx


class ProformaInvoiceDeleteView(DeleteView):
    model               = ProformaInvoice
    template_name       = 'finance/proforma_invoice_delete.html'
    context_object_name = 'pi'
    # depois de apagar, volta para edição da Order
    def get_success_url(self):
        order_pk = self.object.order.pk
        messages.success(
            self.request, 
            f"Proforma Invoice #{self.object.pk} excluída com sucesso."
        )
        return reverse_lazy('orders:order-edit', args=[order_pk])

