"""
Global RBAC-Scoped Search API View.
"""

from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.portal.services.search_service import GlobalSearchService


class GlobalSearchAPIView(LoginRequiredMixin, View):
    """
    Asynchronous JSON endpoint returning role-scoped search results.
    """
    def get(self, request):
        query = request.GET.get('q', '')
        results = GlobalSearchService.search(request.user, query)
        return JsonResponse({'success': True, 'results': results})
