from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .forms import CustomUserRegisterForm, UserLoginForm


class RegisterView(CreateView):
    form_class = CustomUserRegisterForm
    success_url = reverse_lazy("accounts:login")
    template_name = "accounts/register.html"


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            # Perform login logic
            return redirect("home")
    else:
        form = UserLoginForm()
    return render(request, "accounts/login.html", {"form": form})
