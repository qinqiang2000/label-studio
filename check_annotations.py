#!/usr/bin/env python3

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'label_studio.core.settings.label_studio')
sys.path.insert(0, '/Users/qinqiang02/colab/codespace/ai/label-studio/label_studio')

django.setup()

from tasks.models import Annotation

print("Recent Annotations:")
print("=" * 50)
for a in Annotation.objects.all().order_by('-id')[:10]:
    print(f"id={a.id}, unique_id={a.unique_id}, task_id={a.task_id}")

print("\nLooking for annotations with ID patterns like 'VR0sF':")
print("=" * 50)
# 尝试查找相关的annotations
for a in Annotation.objects.all():
    if str(a.id).endswith('sF') or 'VR0' in str(a.unique_id) or 'VR0sF' in str(a.id):
        print(f"Found: id={a.id}, unique_id={a.unique_id}, task_id={a.task_id}")

print("\nTask 661 related annotations:")
print("=" * 50)
for a in Annotation.objects.filter(task_id=661):
    print(f"Task 661: id={a.id}, unique_id={a.unique_id}")