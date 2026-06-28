from django.apps import AppConfig


class AgentApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agent_api'
    label = 'agent_api'
    verbose_name = 'Agent通信'
