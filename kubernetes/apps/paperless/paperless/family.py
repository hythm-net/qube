#!/usr/bin/env python3
"""Paperless as one archive the family shares, set up through Django in the running pod; idempotent.

- group `family`: what a member needs to keep documents (documents, tags, correspondents, types,
  storage paths, custom fields, notes, saved views, share links, mail rules, their own UI settings),
  a look at tasks, history, users and groups (the sharing dialogs list them), and nothing of the
  admin's (editing users or groups, workflows, app config). Pocket ID sign-ups join it through
  PAPERLESS_SOCIAL_ACCOUNT_DEFAULT_GROUPS (helmrelease); only Pocket ID's `family` may sign in.
- workflow `Share with family`: every new document, whoever adds it, is seen and edited by the group
- the admin's defaults for what they create in the web UI (tags and the like; documents are the
  workflow's): seen and edited by the group. The admin is a superuser and sees the rest already.

Documents from before the workflow keep their permissions. Run with kubectl access:

    kubernetes/apps/paperless/paperless/family.py
"""
import subprocess

# app.model: actions; everything not listed stays with the admin
PERMISSIONS = {
    **{f"documents.{m}": ("add", "change", "delete", "view") for m in (
        "document", "tag", "correspondent", "documenttype", "storagepath", "customfield",
        "customfieldinstance", "note", "savedview", "savedviewfilterrule", "sharelink",
        "sharelinkbundle", "uisettings")},
    "paperless_mail.mailaccount": ("add", "change", "delete", "view"),
    "paperless_mail.mailrule": ("add", "change", "delete", "view"),
    "paperless_mail.processedmail": ("view",),
    "documents.paperlesstask": ("change", "view"),  # change: dismissing finished tasks
    "auditlog.logentry": ("view",),
    "auth.user": ("view",),
    "auth.group": ("view",),
}
ADMIN = "hythm"

DJANGO = f"""
from django.contrib.auth.models import Group, Permission, User
from documents.models import UiSettings, Workflow, WorkflowAction, WorkflowTrigger

group, _ = Group.objects.get_or_create(name="family")
wanted = []
for label, actions in {PERMISSIONS!r}.items():
    app, model = label.split(".")
    for action in actions:
        wanted.append(Permission.objects.get(content_type__app_label=app, content_type__model=model,
                                             codename=f"{{action}}_{{model}}"))
group.permissions.set(wanted)
print(f"group family: {{group.permissions.count()}} permissions, members {{sorted(group.user_set.values_list('username', flat=True))}}")

workflow = Workflow.objects.filter(name="Share with family").first()
if workflow is None:
    workflow = Workflow.objects.create(name="Share with family", order=0, enabled=True)
    workflow.triggers.add(WorkflowTrigger.objects.create(type=WorkflowTrigger.WorkflowTriggerType.DOCUMENT_ADDED))
    workflow.actions.add(WorkflowAction.objects.create(type=WorkflowAction.WorkflowActionType.ASSIGNMENT))
workflow.enabled = True
workflow.save()
for action in workflow.actions.all():
    action.assign_view_groups.set([group])
    action.assign_change_groups.set([group])
print(f"workflow {{workflow.name!r}}: on {{[t.get_type_display() for t in workflow.triggers.all()]}}, shares with family")

ui, _ = UiSettings.objects.get_or_create(user=User.objects.get(username={ADMIN!r}))
perms = ui.settings.setdefault("permissions", {{}})
perms["default_view_groups"] = [group.id]
perms["default_edit_groups"] = [group.id]
ui.save()
print(f"{ADMIN}: new objects from the web UI shared with family")
"""


def main() -> None:
    # as paperless (1000), not the container's root: whatever Django writes stays paperless's
    subprocess.run(["kubectl", "-n", "paperless", "exec", "deploy/paperless", "-c", "app", "--",
                    "s6-setuidgid", "paperless", "python3", "/usr/src/paperless/src/manage.py", "shell", "-c", DJANGO],
                   check=True)


if __name__ == "__main__":
    main()
