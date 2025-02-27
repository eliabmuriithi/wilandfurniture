from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.contrib.auth.models import User
from store.models import Product, Profile
import datetime

# importing paypal requirements
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
import uuid  # creatign user id for duplicate orders


def orders(request, pk):

    if request.user.is_authenticated and request.user.is_superuser:
        # get the order
        order = Order.objects.get(id=pk)
        # get the order items
        items = OrderItem.objects.filter(order=pk)

        if request.POST:
            status = request.POST["shipping_status"]
            # check if true or false
            if status == "true":
                # get the order
                order = Order.objects.filter(id=pk)
                # update status
                now = datetime.datetime.now()
                order.update(shipped=True)
            else:
                order = Order.objects.filter(id=pk)
                order.update(shipped=False)
            messages.success(request, "Shipping Status Updated")
            return redirect("home")

        return render(request, "payment/orders.html", {"order": order, "items": items})
    else:
        messages.success(request, "Access Denied!")
        return redirect("home")


def not_shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:

        orders = Order.objects.filter(shipped=False)
        if request.POST:
            status = request.POST["shipping_status"]
            num = request.POST["num"]
            order = Order.objects.filter(id=num)
            # grab date time
            now = datetime.datetime.now()
            # update order
            order.update(shipped=True, date_shipped=now)
            # redirect
            messages.success(request, "Shipping Status Updated")
            return redirect("home")

        return render(
            request,
            "payment/not_shipped_dash.html",
            {"orders": orders},
        )
    else:
        messages.success(request, "Access Denied!")
        return redirect("home")


def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        if request.POST:
            status = request.POST["shipping_status"]
            num = request.POST["num"]
            order = Order.objects.filter(id=num)
            # grab date time
            now = datetime.datetime.now()
            # update order
            order.update(shipped=False)
            # redirect
            messages.success(request, "Shipping Status Updated")
            return redirect("home")

        return render(
            request,
            "payment/shipped_dash.html",
            {"orders": orders},
        )
        messages.success(request, "Order Has Not Been Shipped!")
        return redirect("home")
    else:
        messages.success(request, "Access Denied!")
        return redirect("home")


def process_order(request):
    if request.POST:
        # get the cart
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        # get billing info
        payment_form = PaymentForm(request.POST or None)
        my_shipping = request.session.get("my_shipping")
        # gether order info

        full_name = my_shipping["shipping_full_name"]
        email = my_shipping["shipping_email"]
        # create shipping address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals

        # create an order
        if request.user.is_authenticated:
            # logged in
            user = request.user
            # create order
            create_order = Order(
                user=user,
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid,
            )
            create_order.save()

            # get the order id
            order_id = create_order.pk
            # get product info

            for product in cart_products():
                # get product id
                product_id = product.id
                # get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # get quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(
                            order_id=order_id,
                            product_id=product_id,
                            user=user,
                            quantity=value,
                            price=price,
                        )
                        create_order_item.save()
        # del the cart
        for key in list(request.session.keys()):
            if key == "session_key":
                # delete the key
                del request.session[key]

            # del cart from db old_cart filed
            current_user = Profile.objects.filter(user__id=request.user.id)
            # del shopping cart in db (old_cart field)
            current_user.update(old_cart="")
            messages.success(request, "Order Placed!")
            return redirect("home")

        else:
            # not logged in
            create_order = Order(
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid,
            )
            create_order.save()

            order_id = create_order.pk
            # get product info

            for product in cart_products():
                # get product id
                product_id = product.id
                # get product price
                if product.is_sale:
                    price = product.sale_price
                else:
                    price = product.price

                # get quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # create order item
                        create_order_item = OrderItem(
                            order_id=order_id,
                            product_id=product_id,
                            quantity=value,
                            price=price,
                        )
                        create_order_item.save()

            # delete the cart
            for key in list(request.session.keys()):
                if key == "session_key":
                    # delete the key
                    del request.session[key]

        messages.success(request, "Order Placed!")
        return redirect("home")

    else:
        messages.success(request, "Access Denied!")
        return redirect("home")


def billing_info(request):
    if request.POST:
        # get the billing_form
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        # /create a session with shipping billing_info
        my_shipping = request.POST
        request.session["my_shipping"] = my_shipping

        full_name = my_shipping["shipping_full_name"]
        email = my_shipping["shipping_email"]
        # create shipping address from session info
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals
        # get the host
        host = request.get_host()
        # create an invoice number
        my_Invoice = str(uuid.uuid4())

        # paypal form dictionary
        paypal_dict = {
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "amount": totals,
            "item_name ": "Product Order",  # this will later be changed to specific product order.
            "no_shipping": "2",
            "invoice": str(uuid.uuid4()),
            "currency_code": "USD",
            "notify_url": "https://{}{}".format(host, reverse("paypal-ipn")),
            "return_url": "https://{}{}".format(host, reverse("payment_success")),
            "cancel_return": "https://{}{}".format(host, reverse("payment_failed")),
        }

        # create actual paypal button
        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        if request.user.is_authenticated:
            # Get the billing form
            billing_form = PaymentForm()

            user = request.user
            # Create order
            create_order = Order(
                user=user,
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid,
                invoice=my_Invoice,
            )
            create_order.save()

            # Get the order ID
            order_id = create_order.pk

            # Get product info
            for product in cart_products():
                # Get product ID
                product_id = product.id

                # Get product price
                price = product.sale_price if product.is_sale else product.price

                # Get quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(
                            order_id=order_id,
                            product_id=product_id,
                            user=user,
                            quantity=value,
                            price=price,
                        )
                        create_order_item.save()

            # Delete cart from database (old_cart field)
            current_user = Profile.objects.filter(user__id=request.user.id)
            current_user.update(old_cart="")

            return render(
                request,
                "payment/billing_info.html",
                {
                    "paypal_form": paypal_form,
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "totals": totals,
                    "shipping_info": request.POST,
                    "billing_form": billing_form,
                },
            )

        else:
            # Not logged in
            create_order = Order(
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid,
                invoice=my_Invoice,
            )
            create_order.save()

            order_id = create_order.pk

            # Get product info
            for product in cart_products():
                # Get product ID
                product_id = product.id

                # Get product price
                price = product.sale_price if product.is_sale else product.price

                # Get quantity
                for key, value in quantities().items():
                    if int(key) == product.id:
                        # Create order item
                        create_order_item = OrderItem(
                            order_id=order_id,
                            product_id=product_id,
                            quantity=value,
                            price=price,
                        )
                        create_order_item.save()

            # Returning the billing form
            billing_form = PaymentForm()
            return render(
                request,
                "payment/billing_info.html",
                {
                    "paypal_form": paypal_form,
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "totals": totals,
                    "shipping_info": request.POST,
                    "billing_form": billing_form,
                },
            )

    else:
        messages.success(request, "Access Denied")
        return redirect("home")


def payment_success(request):
    # delete the browser cart
    # get the cart as the first step
    # get the billing_form
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()

    # delete the cart
    for key in list(request.session.keys()):
        if key == "session_key":
            # delete the key
            del request.session[key]
    # adjust to go back home or proceed to cart.
    return render(request, "payment/payment_success.html", {})


def payment_failed(request):
    # adjust to back home, btn retry. (retry to start over gain)
    return render(request, "payment/payment_failed.html", {})


def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()

    if request.user.is_authenticated:
        try:
            shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        except ShippingAddress.DoesNotExist:
            # Handle the case where the shipping address does not exist
            shipping_form = ShippingForm(request.POST or None)
        return render(
            request,
            "payment/checkout.html",
            {
                "cart_products": cart_products,
                "quantities": quantities,
                "totals": totals,
                "shipping_form": shipping_form,
            },
        )
    else:
        shipping_form = ShippingForm(request.POST or None)
        return render(
            request,
            "payment/checkout.html",
            {
                "cart_products": cart_products,
                "quantities": quantities,
                "totals": totals,
                "shipping_form": shipping_form,
            },
        )
