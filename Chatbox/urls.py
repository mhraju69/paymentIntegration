from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_view, name="chat"),
    path("payment/", views.payment_view, name="payment"),
    path("payment-success/", views.payment_success, name="payment-success"),
    path("payment-cancel/", views.payment_cancel, name="payment-cancel"),
    path('payment/stripe-webhook/', views.stripe_webhook, name='stripe-webhook'),
]
