from decimal import Decimal
from django.utils import timezone
from django.test import TestCase

# Create your tests here.
from apps.core import models as core_models
from apps.inventory import models as inv_models
from apps.orders import models as order_models


class PackagingVersionTest(TestCase):
    def setUp(self):
        city = core_models.City.objects.create(name='C')
        province = core_models.Province.objects.create(name='P')
        self.supplier = core_models.Supplier.objects.create(
            name='S', email='s@s.com', address='', city=city,
            province=province, country='BR'
        )
        self.currency = core_models.Currency.objects.create(name='USD')

        self.category = inv_models.Category.objects.create(name='Cat')
        self.subcategory = inv_models.Subcategory.objects.create(name='Sub')
        self.inv_project = inv_models.Project.objects.create(name='Proj')
        self.supplier_chain = inv_models.SupplierChain.objects.create(name='SC')
        self.chain = inv_models.Chain.objects.create(name='Ch')
        self.ncm = inv_models.Ncm.objects.create(name='NCM')
        self.brand = inv_models.BrandManufacturer.objects.create(name='Brand', country='BR')

        self.item = inv_models.Item.objects.create(
            p_code='P1', s_code='S1', cost_price=Decimal('1'), selling_price=Decimal('2'),
            currency=self.currency, name='Item', supplier=self.supplier, category=self.category,
            subcategory=self.subcategory, project=self.inv_project, supplier_chain=self.supplier_chain,
            brand_manufacturer=self.brand, chain=self.chain, ncm=self.ncm,
            net_weight=Decimal('1'), package_gross_weight=Decimal('1.1'),
            packing_lengh=Decimal('10'), packing_width=Decimal('20'), packing_height=Decimal('30'),
            individual_packing_size=Decimal('1'), individual_packing_type='Box', moq=1
        )

        self.pkg1 = inv_models.ItemPackagingVersion.objects.create(
            item=self.item,
            net_weight=self.item.net_weight,
            package_gross_weight=self.item.package_gross_weight,
            packing_lengh=self.item.packing_lengh,
            packing_width=self.item.packing_width,
            packing_height=self.item.packing_height,
            individual_packing_size=self.item.individual_packing_size,
            individual_packing_type=self.item.individual_packing_type,
            valid_from=timezone.now(),
        )

        company = core_models.Company.objects.create(name='C1', country='BR')
        self.exporter = core_models.Exporter.objects.create(name='E', country='BR', company=company)
        self.customer = core_models.Customer.objects.create(name='Cust', email='c@c.com')
        self.port = core_models.Port.objects.create(name='Port', city=city)
        self.rep = core_models.SalesRepresentative.objects.create(name='Rep')
        self.business_unit = core_models.BusinessUnit.objects.create(name='BU')
        self.core_project = core_models.Project.objects.create(name='CoreP', business_unit=self.business_unit)
        self.order_type = core_models.OrderType.objects.create(name='OT')

    def _create_order(self):
        return order_models.Order.objects.create(
            customer=self.customer,
            exporter=self.exporter,
            company=self.exporter.company,
            validity=timezone.now(),
            usd_rmb=Decimal('1'),
            usd_brl=Decimal('1'),
            required_schedule=timezone.now(),
            asap=True,
            down_payment=Decimal('0'),
            pol=self.port,
            pod=self.port,
            sales_representative=self.rep,
            business_unit=self.business_unit,
            project=self.core_project,
            order_type=self.order_type,
        )

    def test_order_items_keep_packaging_versions(self):
        order1 = self._create_order()
        oi1 = order_models.OrderItem.objects.create(order=order1, item=self.item, quantity=1)
        self.assertEqual(oi1.packaging_version, self.pkg1)

        # create new packaging version
        inv_models.ItemPackagingVersion.objects.filter(pk=self.pkg1.pk).update(valid_to=timezone.now())
        pkg2 = inv_models.ItemPackagingVersion.objects.create(
            item=self.item,
            net_weight=Decimal('2'),
            package_gross_weight=Decimal('2.2'),
            packing_lengh=Decimal('11'),
            packing_width=Decimal('21'),
            packing_height=Decimal('31'),
            individual_packing_size=Decimal('2'),
            individual_packing_type='Crate',
            valid_from=timezone.now(),
        )

        order2 = self._create_order()
        oi2 = order_models.OrderItem.objects.create(order=order2, item=self.item, quantity=1)
        self.assertEqual(oi2.packaging_version, pkg2)
        # ensure first order item kept original
        oi1.refresh_from_db()
        self.assertEqual(oi1.packaging_version, self.pkg1)