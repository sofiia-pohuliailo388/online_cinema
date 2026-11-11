"""Payments domain (owner: P7). Spec, section 5: Payment, PaymentItem, Stripe, webhooks.

Uses: ``src.orders.service.mark_order_paid``, ``src.notifications.service.send_email``.
Keep all Stripe SDK calls in ``src/payments/stripe_client.py`` so tests can mock one module.
"""
