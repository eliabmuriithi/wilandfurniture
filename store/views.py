from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Profile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import (
    SignUpForm,
    UpdateUserForm,
    ChangePasswordForm,
    UserInfoForm,
    CategoryForm,
)
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django.db.models import Q
import json
from cart.cart import Cart


def search(request):
    if request.method == "POST":
        searched = request.POST["searched"]
        searched = Product.objects.filter(
            Q(name__icontains=searched) | Q(description__icontains=searched)
        )
        if not searched:
            messages.error(request, "That Product Does Not Exists.")
            return render(request, "search.html", {})
        else:
            return render(request, "search.html", {"searched": searched})
    else:
        return render(request, "search.html", {})


def update_info(request):
    if request.user.is_authenticated:
        # Get Current User
        current_user = Profile.objects.get(user__id=request.user.id)
        # Get Current User's Shipping Info
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)

        # Get original User Form
        form = UserInfoForm(request.POST or None, instance=current_user)
        # Get User's Shipping Form
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        if form.is_valid() or shipping_form.is_valid():
            # Save original form
            form.save()
            # Save shipping form
            shipping_form.save()

            messages.success(request, "Your Info Has Been Updated!!")
            return redirect("home")
        return render(
            request, "update_info.html", {"form": form, "shipping_form": shipping_form}
        )
    else:
        messages.success(request, "You Must Be Logged In To Access That Page!!")
        return redirect("home")


def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        if request.method == "POST":
            form = ChangePasswordForm(current_user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your Password has been updated...")
                login(request, current_user)
                return redirect("update_user")
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                return redirect("update_password")
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {"form": form})
    else:
        messages.success(request, "You must be logged in to view the page")
        return redirect("home")


def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)

        if user_form.is_valid():
            user_form.save()
            login(request, current_user)
            messages.success(request, "User has been Updated.")
            return redirect("home")

        return render(request, "update_user.html", {"user_form": user_form})
    else:
        messages.success(request, "You must be logged in to access that page!")
        return redirect("home")


def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("category_summary")
    else:
        form = CategoryForm()

    return render(request, "add_category.html", {"form": form})


def category_view(request):
    category = get_object_or_404(Category, name=category_name)
    products = Product.objects.filter(category=category)
    return render(
        request,
        "category_summary.html",
        {"category": category, "products": products},
    )


def category_summary(request):
    categories = Category.objects.all()
    return render(request, "category_summary.html", {"categories": categories})


def category(request, foo):
    foo = foo.replace("-", "")
    try:
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)
        return render(
            request, "category.html", {"products": products, "category": category}
        )
    except:
        messages.success(request, "That category doesn't exist")
        return redirect("home")


def product(request, pk):
    product = Product.objects.get(id=pk)
    return render(request, "product.html", {"product": product})


def home(request):
    products = Product.objects.all()
    return render(request, "home.html", {"products": products})


def about(request):
    return render(request, "about.html", {})


def login_user(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            current_user = Profile.objects.get(user__id=request.user.id)
            saved_cart = current_user.old_cart
            if saved_cart:
                converted_cart = json.loads(saved_cart)
                cart = Cart(request)
                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)
            messages.success(request, "You have been logged in")
            return redirect("home")
        else:
            messages.success(request, "There was an error, please try again")
            return redirect("login")
    else:
        return render(request, "login.html", {})


def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out")
    return redirect("home")


def register_user(request):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password1"]
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(
                request, "Username Created - Please Fill Out Your User Info!"
            )
            return redirect("update_info")
        else:
            messages.success(request, "There was a problem!")
            return redirect("register")
    else:
        return render(request, "register.html", {"form": form})
