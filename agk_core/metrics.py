from decimal import Decimal, InvalidOperation
from django.shortcuts import get_object_or_404
from django.utils.formats import number_format
from apps.orders.models import Order, OrderBatch
from apps.inventory.models import ItemPackagingVersion
from apps.shipments.models import Shipment


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


def get_batch_metrics(order_batch_pk):
    batch = get_object_or_404(OrderBatch, pk=order_batch_pk)
    items = (
        batch.batch_items
             .select_related(
                 'order_item__packaging_version',
                 'order_item__item'
             )
             .all()
    )

    ZERO = Decimal('0')
    total_cost_price = ZERO
    total_selling_price = ZERO
    total_quantity = ZERO
    total_box_qty = ZERO
    total_gw = ZERO
    total_nw = ZERO
    total_cbm = ZERO
    packaging_info = []

    for bi in items:
        oi = bi.order_item
        qty = Decimal(bi.quantity)

        # 1) Monetários
        total_cost_price += oi.cost_price_usd * qty
        total_selling_price += oi.sale_price * qty
        total_quantity += qty

        pv = oi.packaging_version or oi.item.current_packaging_version
        if pv:
            packaging_info.append({
                'order_item_id': oi.pk,
                'packaging_version_id': pv.pk,
                **{ fld: getattr(pv, fld) for fld in ItemPackagingVersion.PACKAGING_FIELDS }
            })

            qpm = Decimal(pv.qty_per_master_box or 0)
            if qpm:
                masters = qty / qpm
                total_box_qty += masters
                total_gw += masters * pv.package_gross_weight                
                total_nw += masters * pv.net_weight
                total_cbm += masters * (pv.packing_lengh * pv.packing_width * pv.packing_height)

    # 4) Lucro e sinal
    total_profit = total_selling_price - total_cost_price
    deposit_payment = total_selling_price * batch.order.down_payment / Decimal('100')

    # 5) Formatação amigável
    fmt = lambda v: number_format(v, decimal_pos=2, force_grouping=True)

    return {
        'total_cost_price': fmt(total_cost_price),
        'total_selling_price': fmt(total_selling_price),
        'total_quantity': total_quantity,
        'total_profit': fmt(total_profit),
        'deposit_payment': fmt(deposit_payment),
        'total_box_qty': fmt(total_box_qty),
        'total_nw': fmt(total_nw),
        'total_gw': fmt(total_gw),
        'total_cbm': fmt(total_cbm),
        'packaging_info': packaging_info,
    }


def get_shipment_metrics(shipment_pk):
    shipment = get_object_or_404(Shipment, pk=shipment_pk)
    shipment_batches = shipment.shipment_batches.select_related('order_batch').all()

    ZERO = Decimal('0')
    total_box_qty = ZERO
    total_nw = ZERO
    total_gw = ZERO
    total_cbm = ZERO

    for sb in shipment_batches:
        order_batch = sb.order_batch
        items = (
            order_batch.batch_items
                .select_related(
                    'order_item__packaging_version',
                    'order_item__item'
                )
                .all()
        )

        for bi in items:
            oi = bi.order_item
            qty = Decimal(bi.quantity)

            pv = oi.packaging_version or oi.item.current_packaging_version
            if not pv:
                continue

            qpm = Decimal(pv.qty_per_master_box or 0)
            if qpm:
                masters = qty / qpm
                total_box_qty += masters
                total_gw += masters * pv.package_gross_weight
                total_nw += masters * pv.net_weight
                total_cbm += masters * (
                    pv.packing_lengh * pv.packing_width * pv.packing_height
                )

    fmt = lambda v: number_format(v, decimal_pos=2, force_grouping=True)

    return {
        'total_box_qty': fmt(total_box_qty),
        'total_nw': fmt(total_nw),
        'total_gw': fmt(total_gw),
        'total_cbm': fmt(total_cbm),
    }
