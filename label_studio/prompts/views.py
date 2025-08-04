from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.decorators import module_permission_required


@login_required
@module_permission_required('prompts')
def prompts_list(request):
    """View for prompts page"""
    return render(request, 'base.html')
