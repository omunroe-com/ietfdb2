import datetime, os, shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse as urlreverse
from StringIO import StringIO
from pyquery import PyQuery

from ietf.utils.test_utils import login_testing_unauthorized
from ietf.utils.test_data import make_test_data
from ietf.utils.mail import outbox
from ietf.utils import TestCase

if settings.USE_DB_REDESIGN_PROXY_CLASSES:
    from ietf.person.models import Person, Email
    from ietf.group.models import Group, Role
    from ietf.doc.models import Document, State
    from ietf.doc.utils import *
    from ietf.name.models import DocTagName

class EditStreamInfoTestCase(TestCase):
    # See ietf.utils.test_utils.TestCase for the use of perma_fixtures vs. fixtures
    perma_fixtures = ['names']

    def test_adopt_document(self):
        draft = make_test_data()
        draft.stream = None
        draft.group = Group.objects.get(type="individ")
        draft.save()
        draft.unset_state("draft-stream-ietf")

        url = urlreverse('edit_adopt', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEquals(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEquals(len(q('form input[type=submit][value*=adopt]')), 1)
        self.assertEquals(len(q('form select[name="group"] option')), 1) # we can only select "mars"

        # adopt in mars WG
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()
        r = self.client.post(url,
                             dict(comment="some comment",
                                  group=Group.objects.get(acronym="mars").pk,
                                  weeks="10"))
        self.assertEquals(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEquals(draft.group.acronym, "mars")
        self.assertEquals(draft.stream_id, "ietf")
        self.assertEquals(draft.docevent_set.count() - events_before, 4)
        self.assertEquals(len(outbox), mailbox_before + 1)
        self.assertTrue("state changed" in outbox[-1]["Subject"].lower())
        self.assertTrue("wgchairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("wgdelegate@ietf.org" in unicode(outbox[-1]))

    def test_set_tags(self):
        draft = make_test_data()
        draft.tags = DocTagName.objects.filter(slug="w-expert")
        draft.group.unused_tags.add("w-refdoc")

        url = urlreverse('edit_state', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEquals(r.status_code, 200)
        q = PyQuery(r.content)
        # make sure the unused tags are hidden
        unused = draft.group.unused_tags.values_list("slug", flat=True)
        for t in q("input[name=tags]"):
            self.assertTrue(t.attrib["value"] not in unused)

        # set tags
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()
        r = self.client.post(url,
                             dict(comment="some comment",
                                  weeks="10",
                                  tags=["need-aut", "sheph-u"],
                                  only_tags="1",
                                  # unused but needed for validation
                                  new_state=draft.get_state("draft-stream-%s" % draft.stream_id).pk,
                                  ))
        self.assertEquals(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEquals(draft.tags.count(), 2)
        self.assertEquals(draft.tags.filter(slug="w-expert").count(), 0)
        self.assertEquals(draft.tags.filter(slug="need-aut").count(), 1)
        self.assertEquals(draft.tags.filter(slug="sheph-u").count(), 1)
        self.assertEquals(draft.docevent_set.count() - events_before, 2)
        self.assertEquals(len(outbox), mailbox_before + 1)
        self.assertTrue("tags changed" in outbox[-1]["Subject"].lower())
        self.assertTrue("wgchairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("wgdelegate@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("plain@example.com" in unicode(outbox[-1]))

    def test_set_state(self):
        draft = make_test_data()

        url = urlreverse('edit_state', kwargs=dict(name=draft.name))
        login_testing_unauthorized(self, "marschairman", url)
        
        # get
        r = self.client.get(url)
        self.assertEquals(r.status_code, 200)
        q = PyQuery(r.content)
        # make sure the unused states are hidden
        unused = draft.group.unused_states.values_list("pk", flat=True)
        for t in q("select[name=new_state]").find("option[name=tags]"):
            self.assertTrue(t.attrib["value"] not in unused)
        self.assertEquals(len(q('select[name=new_state]')), 1)

        old_state = draft.get_state("draft-stream-%s" % draft.stream_id )
        new_state = State.objects.get(used=True, type="draft-stream-%s" % draft.stream_id, slug="parked")
        self.assertTrue(old_state!=new_state)
        mailbox_before = len(outbox)
        events_before = draft.docevent_set.count()

        # First make sure cancel doesn't change anything
        r = self.client.post(url,
                             dict(comment="some comment",
                                  weeks="10",
                                  tags=[x.pk for x in draft.tags.filter(slug__in=get_tags_for_stream_id(draft.stream_id))],
                                  new_state=new_state.pk,
				  cancel="1",
                                  ))
        self.assertEquals(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEquals(draft.get_state("draft-stream-%s" % draft.stream_id), old_state)

        # Set new state
        r = self.client.post(url,
                             dict(comment="some comment",
                                  weeks="10",
                                  tags=[x.pk for x in draft.tags.filter(slug__in=get_tags_for_stream_id(draft.stream_id))],
                                  new_state=new_state.pk,
                                  ))
        self.assertEquals(r.status_code, 302)

        draft = Document.objects.get(pk=draft.pk)
        self.assertEquals(draft.get_state("draft-stream-%s" % draft.stream_id), new_state)
        self.assertEquals(draft.docevent_set.count() - events_before, 2)
        reminder = DocReminder.objects.filter(event__doc=draft, type="stream-s")
        self.assertEquals(len(reminder), 1)
        due = datetime.datetime.now() + datetime.timedelta(weeks=10)
        self.assertTrue(due - datetime.timedelta(days=1) <= reminder[0].due <= due + datetime.timedelta(days=1))
        self.assertEquals(len(outbox), mailbox_before + 1)
        self.assertTrue("state changed" in outbox[-1]["Subject"].lower())
        self.assertTrue("wgchairman@ietf.org" in unicode(outbox[-1]))
        self.assertTrue("wgdelegate@ietf.org" in unicode(outbox[-1]))

    def test_manage_stream_delegates(self):
        make_test_data()

        url = urlreverse('stream_delegates', kwargs=dict(stream_name="IETF"))
        login_testing_unauthorized(self, "secretary", url)

        # get
        r = self.client.get(url)
        self.assertEquals(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEquals(len(q('input[type=submit][value*=Add]')), 1)

        delegate = Email.objects.get(address="plain@example.com")

        # add delegate
        r = self.client.post(url,
                             dict(email=delegate.address))
        self.assertEquals(r.status_code, 200)

        self.assertEquals(Role.objects.filter(group__acronym="ietf", name="delegate", person__email__address=delegate.address).count(), 1)

        # remove delegate again
        r = self.client.post(url,
                             dict(remove_delegate=[delegate.person.pk],
                                  delete="1"))
        self.assertEquals(r.status_code, 200)

        self.assertEquals(Role.objects.filter(group__acronym="ietf", name="delegate", person__email__address=delegate.address).count(), 0)

if not settings.USE_DB_REDESIGN_PROXY_CLASSES:
    # the above tests only work with the new schema
    del EditStreamInfoTestCase
