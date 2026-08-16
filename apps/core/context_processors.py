"""
Context processors for Phase 7: Judge Mode and Demo Mode availability.
"""

from django.conf import settings


def platform_context(request):
    """
    Exposes judge_mode, demo_mode, and platform metadata globally to templates.
    """
    judge_param = request.GET.get('judge_mode')
    if judge_param == '1':
        request.session['judge_mode'] = True
    elif judge_param == '0':
        request.session['judge_mode'] = False

    judge_mode = request.session.get('judge_mode', False)

    return {
        'judge_mode': judge_mode,
        'demo_mode': getattr(settings, 'DEMO_MODE', True),
        'platform_version': 'Phase 7 (Competition Ready)',
    }
