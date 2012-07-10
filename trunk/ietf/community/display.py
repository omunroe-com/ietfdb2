import datetime

from django.db.models import Q
from django.core.urlresolvers import reverse as urlreverse

from ietf.ietfworkflows.utils import get_state_for_draft
from ietf.doc.models import DocAlias, DocEvent


class DisplayField(object):

    codename = ''
    description = ''

    def get_value(self, document, raw=False):
        return None


class FilenameField(DisplayField):
    codename = 'filename'
    description = 'I-D filename'

    def get_value(self, document, raw=False):
        if not raw:
            return '<a href="%s">%s</a>' % (document.get_absolute_url(), document.canonical_name())
        else:
            return document.canonical_name()


class TitleField(DisplayField):
    codename = 'title'
    description = 'I-D title'

    def get_value(self, document, raw=False):
        return document.title


class DateField(DisplayField):
    codename = 'date'
    description = 'Date of current I-D'

    def get_value(self, document, raw=False):
        date = document.latest_event(type='new_revision')
        if date:
            return date.time.strftime('%Y-%m-%d')
        return document.time.strftime('%Y-%m-%d')


class StatusField(DisplayField):
    codename = 'status'
    description = 'Status in the IETF process'

    def get_value(self, document, raw=False):
        draft_state = document.get_state('draft')
        stream_state = document.get_state('draft-stream-%s' % (document.stream.slug)) if document.stream else None
        iesg_state = document.get_state('draft-iesg')
        rfceditor_state = document.get_state('draft-rfceditor')
        if draft_state.slug == 'rfc':
            state = draft_state.name
        elif rfceditor_state:
            state = "%s<br/>%s<br/>%s" % (stream_state.name, iesg_state.name, rfceditor_state.name)
        elif iesg_state:
            state = "%s<br/>%s" % (stream_state.name, iesg_state.name)
        elif stream_state:
            state = stream_state.name
        else:
            state = ""
        #
        if draft_state.slug == 'rfc':
            tags = ""
        else:
            tags = [ tag.name for tag in document.tags.all() ]
            if tags:
                tags = '[%s]' % ",".join(tags)
            else:
                tags = ''
        return '%s<br/>%s' % (state, tags)

class WGField(DisplayField):
    codename = 'wg_rg'
    description = 'Associated WG or RG'

    def get_value(self, document, raw=False):
        if raw:
            return document.group.acronym
        else:
            return '<a href="%s">%s</a>' % (urlreverse('wg_docs', kwargs={'acronym':document.group.acronym}), document.group.acronym) if (document.group and document.group.acronym != 'none')  else ''


class ADField(DisplayField):
    codename = 'ad'
    description = 'Associated AD, if any'

    def get_value(self, document, raw=False):
        return document.ad or ''


class OneDayField(DisplayField):
    codename = '1_day'
    description = 'Changed within the last 1 day'

    def get_value(self, document, raw=False):
        now = datetime.datetime.now()
        last = now - datetime.timedelta(days=1)
        if document.docevent_set.filter(time__gte=last):
            return raw and 'YES' or '&#10004;'
        return ''


class TwoDaysField(DisplayField):
    codename = '2_days'
    description = 'Changed within the last 2 days'

    def get_value(self, document, raw=False):
        now = datetime.datetime.now()
        last = now - datetime.timedelta(days=2)
        if document.docevent_set.filter(time__gte=last):
            return raw and 'YES' or '&#10004;'
        return ''


class SevenDaysField(DisplayField):
    codename = '7_days'
    description = 'Changed within the last 7 days'

    def get_value(self, document, raw=False):
        now = datetime.datetime.now()
        last = now - datetime.timedelta(days=7)
        if document.docevent_set.filter(time__gte=last):
            return raw and 'YES' or '&#10004;'
        return ''


TYPES_OF_DISPLAY_FIELDS = [(i.codename, i.description) for i in DisplayField.__subclasses__()]


class SortMethod(object):
    codename = ''
    description = ''

    def get_sort_field(self):
        return 'pk'


class FilenameSort(SortMethod):
    codename = 'by_filename'
    description = 'Alphabetical by I-D filename and RFC number'

    def get_sort_field(self):
        return 'name'

    def get_full_rfc_sort(self, documents):
        return [i.document for i in DocAlias.objects.filter(document__in=documents, name__startswith='rfc').order_by('name')]


class TitleSort(SortMethod):
    codename = 'by_title'
    description = 'Alphabetical by document title'

    def get_sort_field(self):
        return 'title'


class WGSort(SortMethod):
    codename = 'by_wg'
    description = 'Alphabetical by associated WG'

    def get_sort_field(self):
        return 'group__name'


class PublicationSort(SortMethod):
    codename = 'date_publication'
    description = 'Date of publication of current version of the document'

    def get_sort_field(self):
        return '-documentchangedates__new_version_date'

class ChangeSort(SortMethod):
    codename = 'recent_change'
    description = 'Date of most recent change of status of any type'

    def get_sort_field(self):
        return '-documentchangedates__normal_change_date'


class SignificantSort(SortMethod):
    codename = 'recent_significant'
    description = 'Date of most recent significant change of status'

    def get_sort_field(self):
        return '-documentchangedates__significant_change_date'


TYPES_OF_SORT = [(i.codename, i.description) for i in SortMethod.__subclasses__()]
