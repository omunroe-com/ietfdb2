import shutil

from StringIO import StringIO
from django.conf import settings
from django.urls import reverse as urlreverse

import debug                            # pyflakes:ignore

from ietf.doc.models import State
from ietf.person.models import Person
from ietf.submit.models import Preapproval
from ietf.utils.test_utils import TestCase
from ietf.utils.test_data import make_test_data
from ietf.secr.drafts.email import get_email_initial

from pyquery import PyQuery

SECR_USER='secretary'

class SecrDraftsTestCase(TestCase):
    def setUp(self):
        self.saved_internet_draft_path = settings.INTERNET_DRAFT_PATH
        self.repository_dir = self.tempdir('submit-repository')
        settings.INTERNET_DRAFT_PATH = self.repository_dir

        self.saved_internet_draft_archive_dir = settings.INTERNET_DRAFT_ARCHIVE_DIR
        self.archive_dir = self.tempdir('submit-archive')
        settings.INTERNET_DRAFT_ARCHIVE_DIR = self.archive_dir

        self.saved_idsubmit_manual_staging_dir = settings.IDSUBMIT_MANUAL_STAGING_DIR
        self.manual_dir =  self.tempdir('submit-manual')
        settings.IDSUBMIT_MANUAL_STAGING_DIR = self.manual_dir

    def tearDown(self):
        shutil.rmtree(self.repository_dir)
        shutil.rmtree(self.archive_dir)
        shutil.rmtree(self.manual_dir)
        settings.INTERNET_DRAFT_PATH = self.saved_internet_draft_path
        settings.INTERNET_DRAFT_ARCHIVE_DIR = self.saved_internet_draft_archive_dir
        settings.IDSUBMIT_MANUAL_STAGING_DIR = self.saved_idsubmit_manual_staging_dir
        
    def test_abstract(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.abstract', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_add(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.add')
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # dummy upload file
        txt_file = StringIO('This is a simple text file.')
        txt_file.name = "draft-dummy-00.txt"
        
        post = dict(title='A test draft',
            group=draft.group.pk,
            start_date='2015-01-01',
            pages='10',
            txt=txt_file
        )
        response = self.client.post(url,post)
        self.assertEqual(response.status_code, 302)
        
    def test_announce(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.announce', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
    def test_approvals(self):
        make_test_data()
        Preapproval.objects.create(name='draft-dummy',
            by=Person.objects.get(name="(System)"))
        url = urlreverse('ietf.secr.drafts.views.approvals')
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('draft-dummy' in response.content)
    
    def test_edit(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.edit', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_email(self):
        # can't test this directly, test via drafts actions
        pass
    
    def test_get_email_initial(self):
        # Makes sure that a manual posting by the Secretariat of an I-D that is
        # in the RFC Editor Queue will result in notification of the RFC Editor
        draft = make_test_data()
        state = State.objects.get(type='draft-iesg',slug='rfcqueue')
        draft.set_state(state)
        data = get_email_initial(draft,type='revision')
        self.assertTrue('rfc-editor@rfc-editor.org' in data['to'])

    def test_revision_rfcqueue(self):
        # Makes sure that a manual posting by the Secretariat of an I-D that is
        # in the RFC Editor Queue will result in notification of the RFC Editor
        draft = make_test_data()
        state = State.objects.get(type='draft-iesg',slug='rfcqueue')
        draft.set_state(state)
        url = urlreverse('ietf.secr.drafts.views.revision', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        rev = str(int(draft.rev) + 1).zfill(2)
        file = StringIO("This is a test.")
        file.name = "%s-%s.txt" % (draft.name, rev)
        post = {'title':'The Title','pages':'10','txt':file}
        response = self.client.post(url,post,follow=True)
        self.assertEqual(response.status_code, 200)
        q = PyQuery(response.content)
        self.assertTrue('rfc-editor@rfc-editor.org' in q("#draft-confirm-email tr:first-child td").html())

    def test_makerfc(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.edit', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(draft.intended_std_level)
        
    def test_search(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.search')
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        post = dict(filename='draft',state=1,submit='submit')
        response = self.client.post(url, post)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(draft.name in response.content)
    
    def test_update(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.update', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_view(self):
        draft = make_test_data()
        url = urlreverse('ietf.secr.drafts.views.view', kwargs={'id':draft.name})
        self.client.login(username="secretary", password="secretary+password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

