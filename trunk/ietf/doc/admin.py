from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.contrib import admin
from django import forms

from models import (StateType, State, DocAlias, DocumentAuthor, RelatedDocument,
    Document, DocHistory, BallotType, DocEvent,  NewRevisionDocEvent, StateDocEvent,
    ConsensusDocEvent, BallotDocEvent, WriteupDocEvent, LastCallDocEvent,
    TelechatDocEvent, BallotPositionDocEvent)

from ietf.doc.utils import get_state_types

class StateTypeAdmin(admin.ModelAdmin):
    list_display = ["slug", "label"]
admin.site.register(StateType, StateTypeAdmin)

class StateAdmin(admin.ModelAdmin):
    list_display = ["slug", "type", 'name', 'order', 'desc']
    list_filter = ["type", ]
    filter_horizontal = ["next_states"]
admin.site.register(State, StateAdmin)

class DocAliasInline(admin.TabularInline):
    model = DocAlias
    extra = 1

class DocAuthorInline(admin.TabularInline):
    model = DocumentAuthor
    raw_id_fields = ['person', 'email']
    extra = 1

class RelatedDocumentInline(admin.TabularInline):
    model = RelatedDocument
    raw_id_fields = ['target']
    extra = 1

# document form for managing states in a less confusing way

class StatesWidget(forms.SelectMultiple):
    """Display all applicable states as separate select boxes,
    requires 'instance' have been set on the widget."""
    def render(self, name, value, attrs=None, choices=()):

        types = StateType.objects.filter(slug__in=get_state_types(self.instance)).order_by("slug")
        
        categorized_choices = []
        for t in types:
            states = State.objects.filter(used=True, type=t).select_related()
            if states:
                categorized_choices.append((t.label, states))

        html = []
        first = True
        for label, states in categorized_choices:
            htmlid = "id_%s_%s" % (name, slugify(label))
            
            html.append('<div style="clear:both;padding-top:%s">' % ("1em" if first else "0.5em"))
            html.append(u'<label for="%s">%s:</label>' % (htmlid, label))
            html.append(u'<select name="%s" id="%s">' % (name, htmlid))
            html.append(u'<option value="">-----------</option>')
            for s in states:
                html.append('<option %s value="%s">%s</option>' % ("selected" if s.pk in value else "", s.pk, s.name))
            html.append(u'</select>')
            html.append("</div>")
            
            first = False
            
        return mark_safe(u"".join(html))

class StatesField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        # use widget with multiple select boxes
        kwargs['widget'] = StatesWidget
        super(StatesField, self).__init__(*args, **kwargs)
        
    def clean(self, value):
        if value and isinstance(value, (list, tuple)):
            # remove "", in case a state is reset
            value = [x for x in value if x]
        return super(StatesField, self).clean(value)
    
class DocumentForm(forms.ModelForm):
    states = StatesField(queryset=State.objects.all(), required=False)
    comment_about_changes = forms.CharField(
        widget=forms.Textarea(attrs={'rows':10,'cols':40,'class':'vLargeTextField'}), strip=False,
        help_text="This comment about the changes made will be saved in the document history.")
    
    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)

        # we don't normally have access to the instance in the widget
        # so set it here
        self.fields["states"].widget.instance = self.instance

    class Meta:
        fields = '__all__'
        model = Document

class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'rev', 'group', 'pages', 'intended_std_level', 'author_list', 'time']
    search_fields = ['name']
    list_filter = ['type']
    raw_id_fields = ['group', 'shepherd', 'ad']
    inlines = [DocAliasInline, DocAuthorInline, RelatedDocumentInline, ]
    form = DocumentForm

    def save_model(self, request, obj, form, change):
        e = DocEvent.objects.create(
                doc=obj,
                rev=obj.rev,
                by=request.user.person,
                type='changed_document',
                desc=form.cleaned_data.get('comment_about_changes'),
            )
        obj.save_with_history([e])

    def state(self, instance):
        return self.get_state()

admin.site.register(Document, DocumentAdmin)

class DocHistoryAdmin(admin.ModelAdmin):
    list_display = ['doc', 'rev', 'state', 'group', 'pages', 'intended_std_level', 'author_list', 'time']
    search_fields = ['doc__name']
    ordering = ['time', 'doc', 'rev']
    raw_id_fields = ['doc', 'group', 'shepherd', 'ad']

    def state(self, instance):
        return instance.get_state()

admin.site.register(DocHistory, DocHistoryAdmin)

class DocAliasAdmin(admin.ModelAdmin):
    list_display = ['name', 'document_link']
    search_fields = ['name', 'document__name']
    raw_id_fields = ['document']
admin.site.register(DocAlias, DocAliasAdmin)

class RelatedDocumentAdmin(admin.ModelAdmin):
    list_display = ['source', 'target', 'relationship', ]
    list_filter = ['relationship', ]
    search_fields = ['source__name', 'target__name', 'target__document__name', ]
    raw_id_fields = ['source', 'target', ]
admin.site.register(RelatedDocument, RelatedDocumentAdmin)

class BallotTypeAdmin(admin.ModelAdmin):
    list_display = ["slug", "doc_type", "name", "question"]
admin.site.register(BallotType, BallotTypeAdmin)

# events

class DocEventAdmin(admin.ModelAdmin):
    def event_type(self, obj):
        return str(obj.type)
    def doc_time(self, obj):
        h = obj.get_dochistory()
        return h.time if h else ""
    def short_desc(self, obj):
        return obj.desc[:32]
    list_display = ["id", "doc", "event_type", "rev", "by", "time", "doc_time", "short_desc" ]
    search_fields = ["doc__name", "by__name"]
    raw_id_fields = ["doc", "by"]
admin.site.register(DocEvent, DocEventAdmin)

admin.site.register(NewRevisionDocEvent, DocEventAdmin)
admin.site.register(StateDocEvent, DocEventAdmin)
admin.site.register(ConsensusDocEvent, DocEventAdmin)
admin.site.register(BallotDocEvent, DocEventAdmin)
admin.site.register(WriteupDocEvent, DocEventAdmin)
admin.site.register(LastCallDocEvent, DocEventAdmin)
admin.site.register(TelechatDocEvent, DocEventAdmin)

class BallotPositionDocEventAdmin(DocEventAdmin):
    raw_id_fields = ["doc", "by", "ad", "ballot"]
admin.site.register(BallotPositionDocEvent, BallotPositionDocEventAdmin)
    
class DocumentAuthorAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'person', 'email', 'affiliation', 'country', 'order']
    search_fields = ['document__docalias__name', 'person__name', 'email__address', 'affiliation', 'country']
    raw_id_fields = ["document", "person", "email"]
admin.site.register(DocumentAuthor, DocumentAuthorAdmin)
    
