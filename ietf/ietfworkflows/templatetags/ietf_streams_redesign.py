from django import template
from django.conf import settings
from django.core.urlresolvers import reverse as urlreverse

from ietf.idrfc.idrfc_wrapper import IdRfcWrapper, IdWrapper
from ietf.ietfworkflows.utils import (get_workflow_for_draft,
                                      get_state_for_draft)
from ietf.wgchairs.accounts import (can_manage_shepherd_of_a_document,
                                    can_manage_writeup_of_a_document)
from ietf.ietfworkflows.streams import get_stream_from_wrapper
from ietf.ietfworkflows.models import Stream
from ietf.ietfworkflows.accounts import (can_edit_state, can_edit_stream,
                                         is_chair_of_stream, can_adopt)

register = template.Library()


@register.inclusion_tag('ietfworkflows/stream_state_redesign.html', takes_context=True)
def stream_state(context, doc):
    data = {}
    stream = doc.stream
    data.update({'stream': stream})
    if not stream:
        return data

    if doc.type.slug != 'draft':
        return data

    state = get_state_for_draft(doc)

    data.update({
                 'state': state,
                 'doc': doc,
                })

    return data


@register.inclusion_tag('ietfworkflows/workflow_history_entry.html', takes_context=True)
def workflow_history_entry(context, entry):
    real_entry = entry.get_real_instance()
    return {'entry': real_entry,
            'entry_class': real_entry.__class__.__name__.lower()}


@register.inclusion_tag('ietfworkflows/edit_actions.html', takes_context=True)
def edit_actions(context, wrapper):
    request = context.get('request', None)
    user = request and request.user
    if not user:
        return {}
    idwrapper = None
    if isinstance(wrapper, IdRfcWrapper):
        idwrapper = wrapper.id
    elif isinstance(wrapper, IdWrapper):
        idwrapper = wrapper
    if not idwrapper:
        return None
    doc = wrapper
    draft = wrapper._draft

    actions = []
    if can_adopt(user, draft):
        actions.append(("Adopt in WG", urlreverse('edit_adopt', kwargs=dict(name=doc.draft_name))))

    if can_edit_state(user, draft):
        actions.append(("Change stream state", urlreverse('edit_state', kwargs=dict(name=doc.draft_name))))

    if can_edit_stream(user, draft):
        actions.append(("Change stream", urlreverse('edit_stream', kwargs=dict(name=doc.draft_name))))

    if can_manage_shepherd_of_a_document(user, draft):
        actions.append(("Change shepherd", urlreverse('doc_managing_shepherd', kwargs=dict(acronym=draft.group.acronym, name=draft.filename))))

    if can_manage_writeup_of_a_document(user, draft):
        actions.append(("Change stream writeup", urlreverse('doc_managing_writeup', kwargs=dict(acronym=draft.group.acronym, name=draft.filename))))
    else:
        actions.append(("View writeup", urlreverse('doc_managing_writeup', kwargs=dict(acronym=draft.group.acronym, name=draft.filename))))

    return dict(actions=actions)


class StreamListNode(template.Node):

    def __init__(self, user, var_name):
        self.user = user
        self.var_name = var_name

    def render(self, context):
        user = self.user.resolve(context)
        streams = []
        for i in Stream.objects.all():
            if "Legacy" in i.name:
                continue
            if is_chair_of_stream(user, i):
                streams.append(i)
        context.update({self.var_name: streams})
        return ''


@register.tag
def get_user_managed_streams(parser, token):
    firstbits = token.contents.split(None, 2)
    if len(firstbits) != 3:
        raise template.TemplateSyntaxError("'get_user_managed_streams' tag takes three arguments")
    user = parser.compile_filter(firstbits[1])
    lastbits_reversed = firstbits[2][::-1].split(None, 2)
    if lastbits_reversed[1][::-1] != 'as':
        raise template.TemplateSyntaxError("next-to-last argument to 'get_user_managed_stream' tag must"
                                  " be 'as'")
    var_name = lastbits_reversed[0][::-1]
    return StreamListNode(user, var_name)
