"""Collapse Prompt-Workspace M2M into a single required FK.

Backfill rule (run BEFORE making workspace_id NOT NULL):
1. If the prompt has any PromptWorkspace rows, take the first by id.
2. Else if creator has at least one WorkspaceMember, take the first.
3. Else fall back to the first Workspace in the same organization as the
   creator's active_organization (and log).
After backfill, drop the M2M relation and the through model.
"""

import logging

import django.db.models.deletion
from django.db import migrations, models

logger = logging.getLogger(__name__)


def backfill_prompt_workspace(apps, schema_editor):
    Prompt = apps.get_model('prompts', 'Prompt')
    PromptWorkspace = apps.get_model('prompts', 'PromptWorkspace')
    WorkspaceMember = apps.get_model('workspaces', 'WorkspaceMember')
    Workspace = apps.get_model('workspaces', 'Workspace')

    missing = list(Prompt.objects.filter(workspace__isnull=True).values_list('id', flat=True))
    logger.info('Prompt workspace backfill: %d candidates', len(missing))

    for prompt in Prompt.objects.filter(workspace__isnull=True).iterator():
        chosen = None

        link = PromptWorkspace.objects.filter(prompt=prompt).order_by('id').first()
        if link:
            chosen = link.workspace_id

        if chosen is None and prompt.created_by_id:
            membership = (
                WorkspaceMember.objects.filter(user_id=prompt.created_by_id)
                .order_by('id')
                .first()
            )
            if membership:
                chosen = membership.workspace_id

        if chosen is None and prompt.created_by_id:
            org_id = getattr(prompt.created_by, 'active_organization_id', None)
            if org_id:
                fallback = (
                    Workspace.objects.filter(organization_id=org_id).order_by('id').first()
                )
                if fallback:
                    chosen = fallback.id
                    logger.warning(
                        'Prompt %s has no membership; assigned org fallback workspace %s',
                        prompt.id,
                        chosen,
                    )

        if chosen is None:
            raise RuntimeError(
                f'Cannot determine workspace for prompt id={prompt.id} ({prompt.name!r}).'
                ' No M2M link, creator memberships, or org fallback found.'
            )

        prompt.workspace_id = chosen
        prompt.save(update_fields=['workspace_id'])


def reverse_noop(apps, schema_editor):
    raise RuntimeError(
        'Migration 0009 is one-way: PromptWorkspace and the M2M field have been removed.'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0008_prompt_thinking_budget'),
        ('workspaces', '0001_initial'),
    ]

    operations = [
        # 1. Backfill all NULL workspace_id rows.
        migrations.RunPython(backfill_prompt_workspace, reverse_noop),

        # 2. Drop the M2M field (table prompt_workspace stays for step 3).
        migrations.RemoveField(
            model_name='prompt',
            name='workspaces',
        ),

        # 3. Drop the through model (also drops the prompt_workspace table).
        migrations.DeleteModel(name='PromptWorkspace'),

        # 4. Promote single workspace FK to required, with PROTECT and new related_name.
        migrations.AlterField(
            model_name='prompt',
            name='workspace',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='prompts',
                to='workspaces.workspace',
                help_text='Workspace that owns this prompt (tenant boundary)',
            ),
        ),
    ]
