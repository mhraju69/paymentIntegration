from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import ChatSession, Message, UserProfile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User



@login_required
def chat_view(request):
    profile = UserProfile.objects.get(user=request.user)
    
    if request.method == "POST":
        if profile.messages_sent >= profile.message_limit and not profile.is_premium:
            return redirect("chat:payment")

        content = request.POST.get("message")
        session, created = ChatSession.objects.get_or_create(user=request.user)
        Message.objects.create(session=session, user=request.user, content=content)

        profile.messages_sent += 1
        profile.save()

    session, _ = ChatSession.objects.get_or_create(user=request.user)
    messages = session.messages.all()
    
    return render(request, "chat.html", {"messages": messages, "profile": profile})


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect("chat:chat")  # লগইন সফল হলে চ্যাট পেজে নিয়ে যাবে
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, "login.html")


from django.conf import settings
from django.shortcuts import render, redirect
import stripe
from .models import UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY

def payment_view(request):
    if request.method == "POST":
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Premium Access',
                    },
                    'unit_amount': 500,  # $5.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:8000/chat/payment-success/',
            cancel_url='http://localhost:8000/chat/payment-cancel/',
        )
        return redirect(session.url, code=303)

    return render(request, "payment.html")

def payment_success(request):
    profile = UserProfile.objects.get(user=request.user)
    profile.is_premium = True
    profile.message_limit = 10000  # অনেক বেশি লিমিট
    profile.save()
    return render(request, "chat/success.html")

def payment_cancel(request):
    return render(request, "chat/cancel.html")





def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("signup")

        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Account created successfully. You can now log in.")
        return redirect("login")

    return render(request, "signup.html")
