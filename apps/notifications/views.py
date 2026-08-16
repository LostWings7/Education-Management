"""
Views and API endpoints for Notification Center and Preferences.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from .models import Notification, NotificationPreference


class NotificationListView(LoginRequiredMixin, View):
    """
    Main user notification inbox.
    """
    template_name = 'notifications/list.html'

    def get(self, request):
        priority = request.GET.get('priority')
        qs = request.user.notifications.all()

        if priority:
            qs = qs.filter(priority=priority)

        notifications = qs[:50]
        unread_count = request.user.notifications.filter(is_read=False).count()

        return render(request, self.template_name, {
            'notifications': notifications,
            'unread_count': unread_count,
            'selected_priority': priority
        })


class NotificationMarkReadAPIView(LoginRequiredMixin, View):
    """
    AJAX endpoint to mark a single notification as read.
    """
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.mark_as_read()
        return JsonResponse({'success': True, 'unread_count': request.user.notifications.filter(is_read=False).count()})


class NotificationMarkAllReadAPIView(LoginRequiredMixin, View):
    """
    AJAX / POST endpoint to mark all notifications as read.
    """
    def post(self, request):
        request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'unread_count': 0})
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:list')


class NotificationPreferencesView(LoginRequiredMixin, View):
    """
    User notification preference settings view.
    """
    template_name = 'notifications/preferences.html'

    def get(self, request):
        prefs = NotificationPreference.get_for_user(request.user)
        return render(request, self.template_name, {'preferences': prefs})

    def post(self, request):
        prefs = NotificationPreference.get_for_user(request.user)
        prefs.enable_assignment_reminders = request.POST.get('enable_assignment_reminders') == 'on'
        prefs.enable_attendance_warnings = request.POST.get('enable_attendance_warnings') == 'on'
        prefs.enable_intervention_updates = request.POST.get('enable_intervention_updates') == 'on'
        prefs.enable_ai_insights = request.POST.get('enable_ai_insights') == 'on'
        prefs.enable_announcements = request.POST.get('enable_announcements') == 'on'
        prefs.digest_frequency = request.POST.get('digest_frequency', NotificationPreference.DigestFrequency.DAILY)
        prefs.save()

        messages.success(request, "Notification preferences updated successfully.")
        return redirect('notifications:preferences')
