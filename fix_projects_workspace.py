#!/usr/bin/env python
import os
import sys
import django

# Add the label-studio directory to Python path
sys.path.insert(0, '/Users/qinqiang02/workspace/python/label-studio/label_studio')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')
django.setup()

from projects.models import Project
from workspaces.models import Workspace

def main():
    # Find projects without workspace
    projects = Project.objects.filter(workspace__isnull=True)
    workspaces = Workspace.objects.all()
    
    print(f'Found {projects.count()} projects without workspace')
    print(f'Found {workspaces.count()} workspaces')
    
    if workspaces.count() == 0:
        print('No workspaces found!')
        return
    
    # Assign projects to workspaces
    for i, project in enumerate(projects):
        workspace = workspaces[i % workspaces.count()]
        project.workspace = workspace
        project.save()
        print(f'Assigned project "{project.title}" to workspace "{workspace.name}"')
    
    print('Done!')

if __name__ == '__main__':
    main() 