from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
from django.conf import settings
import time
from .models import Order


@receiver(valid_ipn_received)
def paypal_payment_received(sender, **kwargs):
    # add a ten sec pause for paypal to send ip data
    time.sleep(5)  # grab the info from paypal

    paypal_obj = sender
    # ge the invoice

    my_Invoice = str(paypal_obj.invoice)

    # match the invoice to order invoice
    # lookup the order
    my_Order = Order.objects.get(invoice=my_Invoice)
    # record order was paid
    my_Order.paid = True
    # save the order
    my_Order.save()

    # print(paypal_obj)
    # print(f"Amount Paid: {paypal_obj.mc_gross}")
