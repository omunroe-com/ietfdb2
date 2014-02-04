import os
import shutil

from pyquery import PyQuery
from StringIO import StringIO
from textwrap import wrap


from django.conf import settings
from django.core.urlresolvers import reverse as urlreverse

from ietf.utils.test_utils import login_testing_unauthorized
from ietf.utils.test_data  import make_test_data
from ietf.utils.mail import outbox
from ietf.doc.utils import create_ballot_if_not_open
from ietf.doc.views_status_change import default_approval_text
from ietf.utils import TestCase

from ietf.doc.models import Document,DocEvent,NewRevisionDocEvent,BallotPositionDocEvent,TelechatDocEvent,WriteupDocEvent,DocAlias,State
from ietf.name.models import StreamName
from ietf.group.models import Person
from ietf.iesg.models import TelechatDate


class StatusChangeTests(TestCase):
    def test_start_review(self):

        url = urlreverse('start_rfc_status_change',kwargs=dict(name=""))
        login_testing_unauthorized(self, "secretary", url)

        # normal get should succeed and get a reasonable form
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=create_in_state]')),1)

        ad_strpk = str(Person.objects.get(name='Aread Irector').pk)
        state_strpk = str(State.objects.get(slug='adrev',type__slug='statchg').pk)        

        # faulty posts

        ## Must set a responsible AD
        r = self.client.post(url,dict(document_name="bogus",title="Bogus Title",ad="",create_in_state=state_strpk,notify='ipu@ietf.org'))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

        ## Must set a name
        r = self.client.post(url,dict(document_name="",title="Bogus Title",ad=ad_strpk,create_in_state=state_strpk,notify='ipu@ietf.org'))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

        ## Must not choose a document name that already exists
        r = self.client.post(url,dict(document_name="imaginary-mid-review",title="Bogus Title",ad=ad_strpk,create_in_state=state_strpk,notify='ipu@ietf.org'))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

        ## Must set a title
        r = self.client.post(url,dict(document_name="bogus",title="",ad=ad_strpk,create_in_state=state_strpk,notify='ipu@ietf.org'))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

        # successful status change start
        r = self.client.post(url,dict(document_name="imaginary-new",title="A new imaginary status change",ad=ad_strpk,
                                      create_in_state=state_strpk,notify='ipu@ietf.org',new_relation_row_blah="rfc9999",
                                      statchg_relation_row_blah="tois"))
        self.assertEqual(r.status_code, 302)
        status_change = Document.objects.get(name='status-change-imaginary-new')        
        self.assertEqual(status_change.get_state('statchg').slug,'adrev')
        self.assertEqual(status_change.rev,u'00')
        self.assertEqual(status_change.ad.name,u'Aread Irector')
        self.assertEqual(status_change.notify,u'ipu@ietf.org')
        self.assertTrue(status_change.relateddocument_set.filter(relationship__slug='tois',target__document__name='draft-ietf-random-thing'))

    def test_change_state(self):

        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_change_state',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # normal get 
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form select[name=new_state]')),1)
        
        # faulty post
        r = self.client.post(url,dict(new_state=""))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

        # successful change to AD Review
        adrev_pk = str(State.objects.get(slug='adrev',type__slug='statchg').pk)
        r = self.client.post(url,dict(new_state=adrev_pk,comment='RDNK84ZD'))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.get_state('statchg').slug,'adrev')
        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('RDNK84ZD'))
        self.assertFalse(doc.active_ballot())

        # successful change to Last Call Requested
        messages_before = len(outbox)
        doc.ad = Person.objects.get(user__username='ad')
        doc.save()
        lc_req_pk = str(State.objects.get(slug='lc-req',type__slug='statchg').pk)
        r = self.client.post(url,dict(new_state=lc_req_pk))
        self.assertEquals(r.status_code, 200)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEquals(doc.get_state('statchg').slug,'lc-req')
        self.assertEquals(len(outbox), messages_before + 1)
        self.assertTrue('iesg-secretary' in outbox[-1]['To'])
        self.assertTrue('Last Call:' in outbox[-1]['Subject'])

        # successful change to IESG Evaluation 
        iesgeval_pk = str(State.objects.get(slug='iesgeval',type__slug='statchg').pk)
        r = self.client.post(url,dict(new_state=iesgeval_pk,comment='TGmZtEjt'))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.get_state('statchg').slug,'iesgeval')
        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('TGmZtEjt'))
        self.assertTrue(doc.active_ballot())
        self.assertEqual(doc.latest_event(BallotPositionDocEvent, type="changed_ballot_position").pos_id,'yes')

    def test_edit_notices(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_notices',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # normal get 
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form input[name=notify]')),1)
        self.assertEqual(doc.notify,q('form input[name=notify]')[0].value)

        # change notice list
        newlist = '"Foo Bar" <foo@bar.baz.com>'
        r = self.client.post(url,dict(notify=newlist))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.notify,newlist)
        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('Notification list changed'))       

    def test_edit_ad(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_ad',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # normal get 
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('select[name=ad]')),1)

        # change ads
        ad2 = Person.objects.get(name='Ad No2')
        r = self.client.post(url,dict(ad=str(ad2.pk)))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.ad,ad2)
        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('Shepherding AD changed'))       

    def test_edit_telechat_date(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_telechat_date',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # normal get 
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('select[name=telechat_date]')),1)

        # set a date
        self.assertFalse(doc.latest_event(TelechatDocEvent, "scheduled_for_telechat"))
        telechat_date = TelechatDate.objects.active().order_by('date')[0].date
        r = self.client.post(url,dict(telechat_date=telechat_date.isoformat()))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.latest_event(TelechatDocEvent, "scheduled_for_telechat").telechat_date,telechat_date)

        # move it forward a telechat (this should set the returning item bit)
        telechat_date = TelechatDate.objects.active().order_by('date')[1].date
        r = self.client.post(url,dict(telechat_date=telechat_date.isoformat()))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertTrue(doc.returning_item())

        # clear the returning item bit
        r = self.client.post(url,dict(telechat_date=telechat_date.isoformat()))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertFalse(doc.returning_item())

        # set the returning item bit without changing the date
        r = self.client.post(url,dict(telechat_date=telechat_date.isoformat(),returning_item="on"))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertTrue(doc.returning_item())

        # Take the doc back off any telechat
        r = self.client.post(url,dict(telechat_date=""))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.latest_event(TelechatDocEvent, "scheduled_for_telechat").telechat_date,None)

    def test_edit_lc(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_last_call',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "ad", url)

        # additional setup
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9999'),relationship_id='tois')
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9998'),relationship_id='tohist')
        doc.ad =  Person.objects.get(name='Ad No2')
        doc.save()
        
        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.edit-last-call-text')),1)

        self.assertTrue( 'RFC9999 from Proposed Standard to Internet Standard' in ''.join(wrap(r.content,2**16)))
        self.assertTrue( 'RFC9998 from Informational to Historic' in ''.join(wrap(r.content,2**16)))
        
        # save
        r = self.client.post(url,dict(last_call_text="Bogus last call text",save_last_call_text="1"))
        self.assertEqual(r.status_code, 200)

        last_call_event = doc.latest_event(WriteupDocEvent, type="changed_last_call_text")
        self.assertEqual(last_call_event.text,"Bogus last call text")

        # reset
        r = self.client.post(url,dict(regenerate_last_call_text="1"))
        self.assertEqual(r.status_code,200)
        self.assertTrue( 'RFC9999 from Proposed Standard to Internet Standard' in ''.join(wrap(r.content,2**16)))
        self.assertTrue( 'RFC9998 from Informational to Historic' in ''.join(wrap(r.content,2**16)))
      
        # request last call
        messages_before = len(outbox)
        r = self.client.post(url,dict(last_call_text='stuff',send_last_call_request='Save+and+Request+Last+Call'))
        self.assertEqual(r.status_code,200)
        self.assertTrue( 'Last Call Requested' in ''.join(wrap(r.content,2**16)))
        self.assertEqual(len(outbox), messages_before + 1)
        self.assertTrue('iesg-secretary' in outbox[-1]['To'])
        self.assertTrue('Last Call:' in outbox[-1]['Subject'])
        self.assertTrue('Last Call Request has been submitted' in ''.join(wrap(unicode(outbox[-1]),2**16)))


    def test_approve(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_approve',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "secretary", url)
        
        # Some additional setup
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9999'),relationship_id='tois')
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9998'),relationship_id='tohist')
        create_ballot_if_not_open(doc,Person.objects.get(name="Sec Retary"),"statchg")
        doc.set_state(State.objects.get(slug='appr-pend',type='statchg'))
        doc.save()

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.approve')),1)
        # There should be two messages to edit
        self.assertEqual(q('input#id_form-TOTAL_FORMS').val(),'2')
        self.assertTrue( '(rfc9999) to Internet Standard' in ''.join(wrap(r.content,2**16)))
        self.assertTrue( '(rfc9998) to Historic' in ''.join(wrap(r.content,2**16)))
        
        # submit
        messages_before = len(outbox)
        msg0=default_approval_text(doc,doc.relateddocument_set.all()[0])
        msg1=default_approval_text(doc,doc.relateddocument_set.all()[1])
        r = self.client.post(url,{'form-0-announcement_text':msg0,'form-1-announcement_text':msg1,'form-TOTAL_FORMS':'2','form-INITIAL_FORMS':'2','form-MAX_NUM_FORMS':''})
        self.assertEqual(r.status_code, 302)

        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.get_state_slug(),'appr-sent')
        self.assertFalse(doc.ballot_open("statchg"))
        
        self.assertEqual(len(outbox), messages_before + 2)
        self.assertTrue('Action:' in outbox[-1]['Subject'])
        self.assertTrue('(rfc9999) to Internet Standard' in ''.join(wrap(unicode(outbox[-1])+unicode(outbox[-2]),2**16)))
        self.assertTrue('(rfc9998) to Historic' in ''.join(wrap(unicode(outbox[-1])+unicode(outbox[-2]),2**16)))

        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('The following approval message was sent'))       

    def test_edit_relations(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_relations',kwargs=dict(name=doc.name))

        login_testing_unauthorized(self, "secretary", url)
        
        # Some additional setup
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9999'),relationship_id='tois')
        doc.relateddocument_set.create(target=DocAlias.objects.get(name='rfc9998'),relationship_id='tohist')

        # get
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertEqual(len(q('form.edit-status-change-rfcs')),1)
        # There should be three rows on the form
        self.assertEqual(len(q('tr[id^=relation_row]')),3)

        # Try to add a relation to an RFC that doesn't exist
        r = self.client.post(url,dict(new_relation_row_blah="rfc9997",
                                      statchg_relation_row_blah="tois",
                                      Submit="Submit"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

       # Try to add a relation leaving the relation type blank
        r = self.client.post(url,dict(new_relation_row_blah="rfc9999",
                                      statchg_relation_row_blah="",
                                      Submit="Submit"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)

       # Try to add a relation with an unknown relationship type
        r = self.client.post(url,dict(new_relation_row_blah="rfc9999",
                                      statchg_relation_row_blah="badslug",
                                      Submit="Submit"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(len(q('form ul.errorlist')) > 0)
        
        # Successful change of relations
        r = self.client.post(url,dict(new_relation_row_blah="rfc9999",
                                      statchg_relation_row_blah="toexp",
                                      new_relation_row_foo="rfc9998",
                                      statchg_relation_row_foo="tobcp",
                                      Submit="Submit"))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.relateddocument_set.count(),2)
        verify9999 = doc.relateddocument_set.filter(target__name='rfc9999')
        self.assertTrue(verify9999)
        self.assertEqual(verify9999.count(),1)
        self.assertEqual(verify9999[0].relationship.slug,'toexp')
        verify9998 = doc.relateddocument_set.filter(target__name='rfc9998')
        self.assertTrue(verify9998)
        self.assertEqual(verify9998.count(),1)
        self.assertEqual(verify9998[0].relationship.slug,'tobcp')
        self.assertTrue(doc.latest_event(DocEvent,type="added_comment").desc.startswith('Affected RFC list changed.'))       
        
    def setUp(self):
        make_test_data()


class StatusChangeSubmitTests(TestCase):
    def test_initial_submission(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_submit',kwargs=dict(name=doc.name))
        login_testing_unauthorized(self, "ad", url)

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertTrue(q('textarea')[0].text.strip().startswith("Provide a description"))
        
        # Faulty posts using textbox
        # Right now, nothing to test - we let people put whatever the web browser will let them put into that textbox

        # sane post using textbox
        path = os.path.join(settings.STATUS_CHANGE_PATH, '%s-%s.txt' % (doc.canonical_name(), doc.rev))
        self.assertEqual(doc.rev,u'00')
        self.assertFalse(os.path.exists(path))
        r = self.client.post(url,dict(content="Some initial review text\n",submit_response="1"))
        self.assertEqual(r.status_code,302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.rev,u'00')
        with open(path) as f:
            self.assertEqual(f.read(),"Some initial review text\n")
            f.close()
        self.assertTrue( "mid-review-00" in doc.latest_event(NewRevisionDocEvent).desc)

    def test_subsequent_submission(self):
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        url = urlreverse('status_change_submit',kwargs=dict(name=doc.name))
        login_testing_unauthorized(self, "ad", url)

        # A little additional setup 
        # doc.rev is u'00' per the test setup - double-checking that here - if it fails, the breakage is in setUp
        self.assertEqual(doc.rev,u'00')
        path = os.path.join(settings.STATUS_CHANGE_PATH, '%s-%s.txt' % (doc.canonical_name(), doc.rev))
        with open(path,'w') as f:
            f.write('This is the old proposal.')
            f.close()

        # normal get
        r = self.client.get(url)
        self.assertEqual(r.status_code,200)
        q = PyQuery(r.content)
        self.assertTrue(q('textarea')[0].text.strip().startswith("This is the old proposal."))

        # faulty posts trying to use file upload
        # Copied from wgtracker tests - is this really testing the server code, or is it testing
        #  how client.post populates Content-Type?
        test_file = StringIO("\x10\x11\x12") # post binary file
        test_file.name = "unnamed"
        r = self.client.post(url, dict(txt=test_file,submit_response="1"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue("does not appear to be a text file" in r.content)

        # sane post uploading a file
        test_file = StringIO("This is a new proposal.")
        test_file.name = "unnamed"
        r = self.client.post(url,dict(txt=test_file,submit_response="1"))
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get(name='status-change-imaginary-mid-review')
        self.assertEqual(doc.rev,u'01')
        path = os.path.join(settings.STATUS_CHANGE_PATH, '%s-%s.txt' % (doc.canonical_name(), doc.rev))
        with open(path) as f:
            self.assertEqual(f.read(),"This is a new proposal.")
            f.close()
        self.assertTrue( "mid-review-01" in doc.latest_event(NewRevisionDocEvent).desc)

        # verify reset text button works
        r = self.client.post(url,dict(reset_text="1"))
        self.assertEqual(r.status_code, 200)
        q = PyQuery(r.content)
        self.assertTrue(q('textarea')[0].text.strip().startswith("Provide a description"))

    def setUp(self):
        make_test_data()
        self.test_dir = os.path.abspath("tmp-status-change-testdir")
        os.mkdir(self.test_dir)
        settings.STATUS_CHANGE_PATH = self.test_dir

    def tearDown(self):
        shutil.rmtree(self.test_dir)
