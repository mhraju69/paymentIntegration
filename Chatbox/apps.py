from django.apps import AppConfig

class ChatboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Chatbox'

    def ready(self):
        import Chatbox.signals

