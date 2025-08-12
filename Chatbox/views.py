from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,HttpResponse
from .models import ChatSession, Message, UserProfile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import send_mail
from django.conf import settings
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
from django.db import transaction


@login_required
def chat_view(request):
    user =  request.user 
    if not user.is_authenticated :
        return redirect('login')
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
    # if request.user.is_authenticated :
    #     return redirect('chat:chat')
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        print(username,password)
        user = authenticate(request, username=username, password=password)
        print('user',user)
        if user is not None:
            login(request, user)
            return redirect("chat:chat")  # লগইন সফল হলে চ্যাট পেজে নিয়ে যাবে
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, "login.html")


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
                    'unit_amount': 500, 
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://14413dc2e21d.ngrok-free.app/payment-success/', 
            cancel_url='https://14413dc2e21d.ngrok-free.app/payment-cancel/',
            metadata={
                'user_id': request.user.id,
                'type' : 'Premium Access',
                'limit' : '10,000',
                'email': UserProfile.objects.get(user = request.user).email
            }
        )
        return redirect(session.url, code=303)

    return render(request, "payment.html")

def payment_success(request):
    return HttpResponse("Payment Success !")

def payment_cancel(request):
    return HttpResponse("Payment Cancel !")


# views.py

stripe.api_key = settings.STRIPE_SECRET_KEY

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import UserProfile
import stripe
import json

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    print("📥 Stripe webhook received!")
    print("Signature Header:", sig_header)
    print("Payload:", payload)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        print("❌ Invalid payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        print("❌ Invalid signature")
        return HttpResponse(status=400)

    print("✅ Event type:", event['type'])

    # ইউজার আপডেট করার ফাংশন
    def upgrade_user(metadata):
        user_id = metadata.get('user_id')
        plan_type = metadata.get('type')
        limit = metadata.get('limit')
        email = metadata.get('email')

        if not user_id:
            print("❌ No user_id in metadata")
            return

        # limit থেকে কমা সরিয়ে ইন্টে কনভার্ট করার চেষ্টা
        if limit:
            try:
                limit = int(str(limit).replace(',', '').strip())
            except ValueError:
                print(f"⚠️ Invalid limit value: {limit}, setting to 0")
                limit = 0
        else:
            limit = 0

        try:
            with transaction.atomic():
                profile = UserProfile.objects.get(user_id=user_id)
                profile.is_premium = True
                profile.message_limit = limit
                profile.save()

                subject = 'Payment Successful'
                message = (
                    f'Your payment for {plan_type} with a new limit of {limit} '
                    f'has been activated. Enjoy chatting!'
                )

                if email:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    print(f"📧 Email sent to {email}")
                else:
                    print("⚠️ No email in metadata, skipping email send")

                print(f"✅ UserProfile for user_id={user_id} upgraded to premium")
        except UserProfile.DoesNotExist:
            print(f"❌ UserProfile not found for user_id={user_id}")
        except Exception as e:
            print(f"💥 Error updating UserProfile: {str(e)}")

    # ইভেন্ট টাইপ অনুযায়ী হ্যান্ডেলিং
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        print("📝 Metadata from checkout.session.completed:", metadata)
        upgrade_user(metadata)

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        metadata = payment_intent.get('metadata', {})
        print("📝 Metadata from payment_intent.succeeded:", metadata)
        upgrade_user(metadata)

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        print(f"❌ Payment failed: {payment_intent['id']}")

    elif event['type'] == 'invoice.paid':
        invoice = event['data']['object']
        customer_id = invoice['customer']
        print(f"📄 Subscription payment successful for customer {customer_id}")

    else:
        print(f"ℹ️ Unhandled event type: {event['type']}")

    return HttpResponse(status=200)

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
