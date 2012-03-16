import os

from django.conf import settings

from ietf.group.models import *


def save_group_in_history(group):
    def get_model_fields_as_dict(obj):
        return dict((field.name, getattr(obj, field.name))
                    for field in obj._meta.fields
                    if field is not obj._meta.pk)

    # copy fields
    fields = get_model_fields_as_dict(group)
    del fields["charter"] # Charter is saved canonically on Group
    fields["group"] = group
    
    grouphist = GroupHistory(**fields)
    grouphist.save()

    # save RoleHistory
    for role in group.role_set.all():
        rh = RoleHistory(name=role.name, group=grouphist, email=role.email, person=role.person)
        rh.save()

    # copy many to many
    for field in group._meta.many_to_many:
        if field.rel.through and field.rel.through._meta.auto_created:
            setattr(grouphist, field.name, getattr(group, field.name).all())

    return grouphist

def get_charter_text(group):
    # get file path from settings. Syntesize file name from path, acronym, and suffix
    try:
        # Try getting charter from new charter tool
        from ietf.wgcharter.utils import get_charter_for_revision, approved_revision

        charter = group.charter
        ch = get_charter_for_revision(charter, charter.rev)
        name = ch.name
        rev = approved_revision(ch.rev)
        filename = os.path.join(charter.get_file_path(), "%s-%s.txt" % (name, rev))
        desc_file = open(filename)
        desc = desc_file.read()
        return desc
    except:
        try:
            filename = os.path.join(settings.IETFWG_DESCRIPTIONS_PATH, group.acronym) + ".desc.txt"
            desc_file = open(filename)
            desc = desc_file.read()
        except:
            desc = 'Error Loading Work Group Description'
        return desc
