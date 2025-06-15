from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def workspaces_list(request):
    """View for workspaces page"""
    return render(request, 'base.html')
