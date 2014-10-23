from django.contrib import admin
from models import *                    # pyflakes:ignore


class NameAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "desc", "used"]
    prepopulate_from = { "slug": ("name",) }

class DocRelationshipNameAdmin(NameAdmin):
    list_display = ["slug", "name", "revname", "desc", "used"]
    
admin.site.register(GroupTypeName, NameAdmin)
admin.site.register(GroupStateName, NameAdmin)
admin.site.register(RoleName, NameAdmin)
admin.site.register(StreamName, NameAdmin)
admin.site.register(DocRelationshipName, DocRelationshipNameAdmin)
admin.site.register(DocTypeName, NameAdmin)
admin.site.register(DocTagName, NameAdmin)
admin.site.register(StdLevelName, NameAdmin)
admin.site.register(IntendedStdLevelName, NameAdmin)
admin.site.register(DocReminderTypeName, NameAdmin)
admin.site.register(BallotPositionName, NameAdmin)
admin.site.register(SessionStatusName, NameAdmin)
admin.site.register(TimeSlotTypeName, NameAdmin)
admin.site.register(ConstraintName, NameAdmin)
admin.site.register(NomineePositionStateName, NameAdmin)
admin.site.register(FeedbackTypeName, NameAdmin)
admin.site.register(DBTemplateTypeName, NameAdmin)
