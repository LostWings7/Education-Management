"""
Django admin registration for AI service models.
"""

from django.contrib import admin
from .models import AIConversation, AIMessage, AIMessageFeedback, AIInteractionLog


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'title', 'is_archived', 'updated_at')
    list_filter = ('role', 'is_archived', 'updated_at')
    search_fields = ('user__email', 'title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'token_count', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('conversation__user__email', 'content')
    readonly_fields = ('created_at',)


@admin.register(AIMessageFeedback)
class AIMessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'is_helpful', 'category', 'created_at')
    list_filter = ('is_helpful', 'category', 'created_at')
    search_fields = ('message__conversation__user__email', 'comments')


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'request_type', 'provider', 'model', 'latency_ms', 'success', 'validation_status', 'created_at')
    list_filter = ('role', 'request_type', 'provider', 'success', 'validation_status')
    search_fields = ('user__email', 'error_code')
    readonly_fields = ('created_at',)
