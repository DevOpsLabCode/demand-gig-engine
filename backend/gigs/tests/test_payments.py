from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.test import SimpleTestCase, override_settings

from gigs.payments import FakePaymentProvider, StripePaymentProvider, get_payment_provider


class PaymentProviderTests(SimpleTestCase):
    def test_fake_provider(self):
        p=FakePaymentProvider()
        result=p.collect_refundable_deposit(amount=Decimal('1'),currency='USD',email='a@b.com',idempotency_key='i',metadata={})
        self.assertTrue(result.reference.startswith('fake_pi_'))
        self.assertTrue(p.refund(payment_reference=result.reference).startswith('fake_re_'))
        self.assertEqual(p.finalize(payment_reference='x'),'x')
        self.assertEqual(p.get_client_secret(payment_reference='x'),'')

    @override_settings(PAYMENT_PROVIDER='fake')
    def test_provider_selection_fake(self):
        self.assertIsInstance(get_payment_provider(), FakePaymentProvider)

    @override_settings(PAYMENT_PROVIDER='stripe', STRIPE_SECRET_KEY='')
    def test_provider_selection_requires_key(self):
        with self.assertRaises(RuntimeError): get_payment_provider()

    @override_settings(PAYMENT_PROVIDER='stripe', STRIPE_SECRET_KEY='sk_test')
    def test_stripe_provider_operations(self):
        fake=SimpleNamespace(
            PaymentIntent=SimpleNamespace(create=Mock(return_value=SimpleNamespace(id='pi',client_secret=None,status='succeeded')), retrieve=Mock(return_value=SimpleNamespace(client_secret=None))),
            Refund=SimpleNamespace(create=Mock(return_value=SimpleNamespace(id='re'))), api_key=None,
        )
        with patch.dict('sys.modules', {'stripe': fake}):
            p=StripePaymentProvider()
            result=p.collect_refundable_deposit(amount=Decimal('1.23'),currency='USD',email='a@b.com',idempotency_key='i',metadata={})
            self.assertEqual((result.reference,result.client_secret,result.status),('pi','','succeeded'))
            self.assertEqual(p.refund(payment_reference='pi',amount=Decimal('1.00')),'re')
            self.assertEqual(p.refund(payment_reference='pi'),'re')
            self.assertEqual(p.finalize(payment_reference='pi'),'pi')
            self.assertEqual(p.get_client_secret(payment_reference='pi'),'')
