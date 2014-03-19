from django.contrib import admin

from ietf.liaisons.models import LiaisonStatement

class LiaisonStatementAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'from_name', 'to_name', 'submitted', 'purpose', 'related_to']
    list_display_links = ['id', 'title']
    ordering = ('title', )
    raw_id_fields = ('from_contact', 'related_to', 'from_group', 'to_group', 'attachments')
admin.site.register(LiaisonStatement, LiaisonStatementAdmin)
