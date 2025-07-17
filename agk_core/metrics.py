from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils.formats import number_format
from apps.orders.models import Order



def get_order_metrics(order_pk):
    # 1) Busca a Order, lança 404 se não existir
    order = get_object_or_404(Order, pk=order_pk)
    # 2) Busca os itens da order; ajuste o related_name se for diferente
    items = order.order_items.select_related('item').all()

    # 3) Calcula totais
    total_cost_price = sum(item.cost_price   * item.quantity for item in items)
    total_selling_price = sum(item.total for item in items)
    total_quantity = sum(item.quantity for item in items)
    total_profit = total_selling_price - total_cost_price
    deposit_payment = total_selling_price * order.down_payment * Decimal(0.01)
    # 4) Formata valores numéricos com duas casas decimais e agrupamento de milhar
    formatted_cost = number_format(total_cost_price, decimal_pos=2, force_grouping=True)
    formatted_selling = number_format(total_selling_price, decimal_pos=2, force_grouping=True)
    formatted_profit = number_format(total_profit, decimal_pos=2, force_grouping=True)
    formatted_dep_paymnt = number_format(deposit_payment, decimal_pos=2, force_grouping=True)
    
    return {
        'total_cost_price': formatted_cost,
        'total_selling_price': formatted_selling,
        'total_quantity': total_quantity,
        'total_profit': formatted_profit,
        'deposit_payment': formatted_dep_paymnt
    }
