from django.contrib import admin

from payments.models import Plan, PlanEntitlement, ProcessedWebhookEvent, Subscription

admin.site.register(Plan)
admin.site.register(PlanEntitlement)
admin.site.register(Subscription)
admin.site.register(ProcessedWebhookEvent)
