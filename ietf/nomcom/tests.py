# -*- coding: utf-8 -*-
import os
import tempfile
import datetime

from ietf.utils import TestCase
from django.db import IntegrityError
from django.core.urlresolvers import reverse
from django.core.files import File
from django.contrib.formtools.preview import security_hash
from django.contrib.auth.models import User

from ietf.utils.test_utils import login_testing_unauthorized
from ietf.utils.mail import outbox


from ietf.person.models import Email, Person
from ietf.group.models import Group
from ietf.message.models import Message

from ietf.nomcom.test_data import nomcom_test_data, generate_cert, check_comments, \
                                  COMMUNITY_USER, CHAIR_USER, \
                                  MEMBER_USER, SECRETARIAT_USER, EMAIL_DOMAIN, NOMCOM_YEAR
from ietf.nomcom.models import NomineePosition, Position, Nominee, \
                               NomineePositionState, Feedback, FeedbackType, \
                               Nomination
from ietf.nomcom.forms import EditChairForm, EditMembersForm
from ietf.nomcom.utils import get_nomcom_by_year, get_or_create_nominee
from ietf.nomcom.management.commands.send_reminders import Command, is_time_to_send


class NomcomViewsTest(TestCase):
    """Tests to create a new nomcom"""
    # See ietf.utils.test_utils.TestCase for the use of perma_fixtures vs. fixtures
    perma_fixtures = ['nomcom_templates']

    def check_url_status(self, url, status):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status)

    def setUp(self):
        nomcom_test_data()
        self.cert_file, self.privatekey_file = generate_cert()
        self.year = NOMCOM_YEAR

        # private urls
        self.private_index_url = reverse('nomcom_private_index', kwargs={'year': self.year})
        self.private_merge_url = reverse('nomcom_private_merge', kwargs={'year': self.year})
        self.edit_members_url = reverse('nomcom_edit_members', kwargs={'year': self.year})
        self.edit_chair_url = reverse('nomcom_edit_chair', kwargs={'year': self.year})
        self.edit_nomcom_url = reverse('nomcom_edit_nomcom', kwargs={'year': self.year})
        self.private_nominate_url = reverse('nomcom_private_nominate', kwargs={'year': self.year})
        self.add_questionnaire_url = reverse('nomcom_private_questionnaire', kwargs={'year': self.year})
        self.private_feedback_url = reverse('nomcom_private_feedback', kwargs={'year': self.year})

        # public urls
        self.index_url = reverse('nomcom_year_index', kwargs={'year': self.year})
        self.requirements_url = reverse('nomcom_requirements', kwargs={'year': self.year})
        self.questionnaires_url = reverse('nomcom_questionnaires', kwargs={'year': self.year})
        self.public_feedback_url = reverse('nomcom_public_feedback', kwargs={'year': self.year})
        self.public_nominate_url = reverse('nomcom_public_nominate', kwargs={'year': self.year})

    def access_member_url(self, url):
        login_testing_unauthorized(self, COMMUNITY_USER, url)
        login_testing_unauthorized(self, CHAIR_USER, url)
        self.check_url_status(url, 200)
        self.client.logout()
        login_testing_unauthorized(self, MEMBER_USER, url)
        self.check_url_status(url, 200)

    def access_chair_url(self, url):
        login_testing_unauthorized(self, COMMUNITY_USER, url)
        login_testing_unauthorized(self, MEMBER_USER, url)
        login_testing_unauthorized(self, CHAIR_USER, url)
        self.check_url_status(url, 200)

    def access_secretariat_url(self, url):
        login_testing_unauthorized(self, COMMUNITY_USER, url)
        login_testing_unauthorized(self, CHAIR_USER, url)
        login_testing_unauthorized(self, SECRETARIAT_USER, url)
        self.check_url_status(url, 200)

    def test_private_index_view(self):
        """Verify private home view"""
        self.access_member_url(self.private_index_url)
        self.client.logout()

    def test_private_merge_view(self):
        """Verify private merge view"""

        nominees = [u'nominee0@example.com',
                    u'nominee1@example.com',
                    u'nominee2@example.com',
                    u'nominee3@example.com']

        # do nominations
        login_testing_unauthorized(self, COMMUNITY_USER, self.public_nominate_url)
        self.nominate_view(public=True,
                           nominee_email=nominees[0],
                           position='IAOC')
        self.nominate_view(public=True,
                           nominee_email=nominees[0],
                           position='IAOC')
        self.nominate_view(public=True,
                           nominee_email=nominees[0],
                           position='IAB')
        self.nominate_view(public=True,
                           nominee_email=nominees[0],
                           position='TSV')
        self.nominate_view(public=True,
                           nominee_email=nominees[1],
                           position='IAOC')
        self.nominate_view(public=True,
                           nominee_email=nominees[1],
                           position='IAOC')
        self.nominate_view(public=True,
                           nominee_email=nominees[2],
                           position='IAB')
        self.nominate_view(public=True,
                           nominee_email=nominees[2],
                           position='IAB')
        self.nominate_view(public=True,
                           nominee_email=nominees[3],
                           position='TSV')
        self.nominate_view(public=True,
                           nominee_email=nominees[3],
                           position='TSV')
        # Check nominee positions
        self.assertEqual(NomineePosition.objects.count(), 6)
        self.assertEqual(Feedback.objects.nominations().count(), 10)

        # Accept and declined nominations
        nominee_position = NomineePosition.objects.get(position__name='IAOC',
                                                       nominee__email__address=nominees[0])
        nominee_position.state = NomineePositionState.objects.get(slug='accepted')
        nominee_position.save()

        nominee_position = NomineePosition.objects.get(position__name='IAOC',
                                                       nominee__email__address=nominees[1])
        nominee_position.state = NomineePositionState.objects.get(slug='declined')
        nominee_position.save()

        nominee_position = NomineePosition.objects.get(position__name='IAB',
                                                       nominee__email__address=nominees[2])
        nominee_position.state = NomineePositionState.objects.get(slug='declined')
        nominee_position.save()

        nominee_position = NomineePosition.objects.get(position__name='TSV',
                                                       nominee__email__address=nominees[3])
        nominee_position.state = NomineePositionState.objects.get(slug='accepted')
        nominee_position.save()

        self.client.logout()

        # fill questionnaires (internally the function does new nominations)
        self.access_chair_url(self.add_questionnaire_url)

        self.add_questionnaire(public=False,
                               nominee_email=nominees[0],
                               position='IAOC')
        self.add_questionnaire(public=False,
                               nominee_email=nominees[1],
                               position='IAOC')
        self.add_questionnaire(public=False,
                               nominee_email=nominees[2],
                               position='IAB')
        self.add_questionnaire(public=False,
                               nominee_email=nominees[3],
                               position='TSV')
        self.assertEqual(Feedback.objects.questionnaires().count(), 4)

        self.client.logout()

        ## Add feedbacks (internally the function does new nominations)
        self.access_member_url(self.private_feedback_url)
        self.feedback_view(public=False,
                           nominee_email=nominees[0],
                           position='IAOC')
        self.feedback_view(public=False,
                           nominee_email=nominees[1],
                           position='IAOC')
        self.feedback_view(public=False,
                           nominee_email=nominees[2],
                           position='IAB')
        self.feedback_view(public=False,
                           nominee_email=nominees[3],
                           position='TSV')

        self.assertEqual(Feedback.objects.comments().count(), 4)
        self.assertEqual(Feedback.objects.nominations().count(), 18)
        self.assertEqual(Feedback.objects.nominations().filter(nominees__email__address=nominees[0]).count(), 6)
        self.assertEqual(Feedback.objects.nominations().filter(nominees__email__address=nominees[1]).count(), 4)
        self.assertEqual(Feedback.objects.nominations().filter(nominees__email__address=nominees[2]).count(), 4)
        self.assertEqual(Feedback.objects.nominations().filter(nominees__email__address=nominees[3]).count(), 4)
        for nominee in nominees:
            self.assertEqual(Feedback.objects.comments().filter(nominees__email__address=nominee).count(),
                         1)
            self.assertEqual(Feedback.objects.questionnaires().filter(nominees__email__address=nominee).count(),
                         1)

        self.client.logout()

        ## merge nominations
        self.access_chair_url(self.private_merge_url)

        test_data = {"secondary_emails": "%s, %s" % (nominees[0], nominees[1]),
                     "primary_email": nominees[0]}
        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-error")

        test_data = {"primary_email": nominees[0],
                     "secondary_emails": ""}
        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-error")

        test_data = {"primary_email": "",
                     "secondary_emails": nominees[0]}
        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-error")

        test_data = {"primary_email": "unknown@example.com",
                     "secondary_emails": nominees[0]}
        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-error")

        test_data = {"primary_email": nominees[0],
                     "secondary_emails": "unknown@example.com"}
        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-error")

        test_data = {"secondary_emails": """%s,
                                            %s,
                                            %s""" % (nominees[1], nominees[2], nominees[3]),
                     "primary_email": nominees[0]}

        response = self.client.post(self.private_merge_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-success")

        self.assertEqual(Nominee.objects.filter(email__address=nominees[1],
                                                duplicated__isnull=False).count(), 1)
        self.assertEqual(Nominee.objects.filter(email__address=nominees[2],
                                                duplicated__isnull=False).count(), 1)
        self.assertEqual(Nominee.objects.filter(email__address=nominees[3],
                                                duplicated__isnull=False).count(), 1)

        nominee = Nominee.objects.get(email__address=nominees[0])

        self.assertEqual(Nomination.objects.filter(nominee=nominee).count(), 18)
        self.assertEqual(Feedback.objects.nominations().filter(nominees__in=[nominee]).count(),
                         18)
        self.assertEqual(Feedback.objects.comments().filter(nominees__in=[nominee]).count(),
                         4)
        self.assertEqual(Feedback.objects.questionnaires().filter(nominees__in=[nominee]).count(),
                         4)

        for nominee_email in nominees[1:]:
            self.assertEqual(Feedback.objects.nominations().filter(nominees__email__address=nominee_email).count(),
                         0)
            self.assertEqual(Feedback.objects.comments().filter(nominees__email__address=nominee_email).count(),
                         0)
            self.assertEqual(Feedback.objects.questionnaires().filter(nominees__email__address=nominee_email).count(),
                         0)

        self.assertEqual(NomineePosition.objects.filter(nominee=nominee).count(), 3)

        # Check nominations state
        self.assertEqual(NomineePosition.objects.get(position__name='TSV',
                                                     nominee=nominee).state.slug, u'accepted')
        self.assertEqual(NomineePosition.objects.get(position__name='IAOC',
                                                     nominee=nominee).state.slug, u'accepted')
        self.assertEqual(NomineePosition.objects.get(position__name='IAB',
                                                     nominee=nominee).state.slug, u'declined')

        self.client.logout()

    def change_members(self, members):
        members_emails = u','.join(['%s%s' % (member, EMAIL_DOMAIN) for member in members])
        test_data = {'members': members_emails,
                     'stage': 1}
        # preview
        self.client.post(self.edit_members_url, test_data)

        hash = security_hash(None, EditMembersForm(test_data))
        test_data.update({'hash': hash, 'stage': 2})

        # submit
        self.client.post(self.edit_members_url, test_data)

    def test_edit_members_view(self):
        """Verify edit member view"""
        self.access_chair_url(self.edit_members_url)
        self.change_members([CHAIR_USER, COMMUNITY_USER])

        # check member actions
        self.client.login(remote_user=COMMUNITY_USER)
        self.check_url_status(self.private_index_url, 200)

        # revert edit nomcom members
        login_testing_unauthorized(self, CHAIR_USER, self.edit_members_url)
        self.change_members([CHAIR_USER])
        self.client.login(remote_user=COMMUNITY_USER)
        self.check_url_status(self.private_index_url, 403)

        self.client.logout()

    def change_chair(self, user):
        test_data = {'chair': '%s%s' % (user, EMAIL_DOMAIN),
                     'stage': 1}
        # preview
        self.client.post(self.edit_chair_url, test_data)

        hash = security_hash(None, EditChairForm(test_data))
        test_data.update({'hash': hash, 'stage': 2})

        # submit
        self.client.post(self.edit_chair_url, test_data)

    def test_edit_chair_view(self):
        """Verify edit chair view"""
        self.access_secretariat_url(self.edit_chair_url)
        self.change_chair(COMMUNITY_USER)

        # check chair actions
        self.client.login(remote_user=COMMUNITY_USER)
        self.check_url_status(self.edit_members_url, 200)
        self.check_url_status(self.edit_nomcom_url, 200)

        # revert edit nomcom chair
        login_testing_unauthorized(self, SECRETARIAT_USER, self.edit_chair_url)
        self.change_chair(CHAIR_USER)
        self.client.logout()

    def test_edit_nomcom_view(self):
        """Verify edit nomcom view"""
        self.access_chair_url(self.edit_nomcom_url)

        f = open(self.cert_file.name)
        response = self.client.post(self.edit_nomcom_url, {'public_key': f})
        f.close()
        self.assertEqual(response.status_code, 200)

        nominee = Nominee.objects.get(email__person__name=COMMUNITY_USER)
        position = Position.objects.get(name='OAM')

        comments = u'Plain text. Comments with accents äöåÄÖÅ éáíóú âêîôû ü àèìòù.'
        nomcom = get_nomcom_by_year(self.year)
        feedback = Feedback.objects.create(nomcom=nomcom,
                                           comments=comments,
                                           type=FeedbackType.objects.get(slug='nomina'))
        feedback.positions.add(position)
        feedback.nominees.add(nominee)

        # to check feedback comments are saved like enrypted data
        self.assertNotEqual(feedback.comments, comments)

        self.assertEqual(check_comments(feedback.comments, comments, self.privatekey_file), True)

        self.client.logout()

    def test_index_view(self):
        """Verify home view"""
        self.check_url_status(self.index_url, 200)

    def test_announcements_view(self):
        nomcom = Group.objects.get(acronym="nomcom%s" % self.year, type="nomcom")
        msg = Message.objects.create(
            by=Person.objects.all()[0],
            subject="This is a test",
            to="test@example.com",
            frm="nomcomchair@example.com",
            body="Hello World!",
            content_type="",
            )
        msg.related_groups.add(nomcom)
        
        r = self.client.get(reverse('ietf.nomcom.views.announcements'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(("Messages from %s" % nomcom.time.year) in r.content)
        self.assertTrue(nomcom.role_set.filter(name="chair")[0].person.email_address() in r.content)
        self.assertTrue(msg.subject in r.content)


    def test_requirements_view(self):
        """Verify requirements view"""
        self.check_url_status(self.requirements_url, 200)

    def test_questionnaires_view(self):
        """Verify questionnaires view"""
        self.check_url_status(self.questionnaires_url, 200)

    def test_public_nominate(self):
        login_testing_unauthorized(self, COMMUNITY_USER, self.public_nominate_url)
        return self.nominate_view(public=True)
        self.client.logout()

    def test_private_nominate(self):
        self.access_member_url(self.private_nominate_url)
        return self.nominate_view(public=False)
        self.client.logout()

    def nominate_view(self, *args, **kwargs):
        public = kwargs.pop('public', True)
        nominee_email = kwargs.pop('nominee_email', u'nominee@example.com')
        nominator_email = kwargs.pop('nominator_email', "%s%s" % (COMMUNITY_USER, EMAIL_DOMAIN))
        position_name = kwargs.pop('position', 'IAOC')

        if public:
            nominate_url = self.public_nominate_url
        else:
            nominate_url = self.private_nominate_url
        response = self.client.get(nominate_url)
        self.assertEqual(response.status_code, 200)

        nomcom = get_nomcom_by_year(self.year)
        if not nomcom.public_key:
            self.assertNotContains(response, "nominateform")

        # save the cert file in tmp
        nomcom.public_key.storage.location = tempfile.gettempdir()
        nomcom.public_key.save('cert', File(open(self.cert_file.name, 'r')))

        response = self.client.get(nominate_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nominateform")

        position = Position.objects.get(name=position_name)
        candidate_email = nominee_email
        candidate_name = u'nominee'
        comments = u'Test nominate view. Comments with accents äöåÄÖÅ éáíóú âêîôû ü àèìòù.'
        candidate_phone = u'123456'

        test_data = {'candidate_name': candidate_name,
                     'candidate_email': candidate_email,
                     'candidate_phone': candidate_phone,
                     'position': position.id,
                     'comments': comments}
        if not public:
            test_data['nominator_email'] = nominator_email

        response = self.client.post(nominate_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-success")

        # check objects
        email = Email.objects.get(address=candidate_email)
        Person.objects.get(name=candidate_name, address=candidate_email)
        nominee = Nominee.objects.get(email=email)
        NomineePosition.objects.get(position=position, nominee=nominee)
        feedback = Feedback.objects.filter(positions__in=[position],
                                           nominees__in=[nominee],
                                           type=FeedbackType.objects.get(slug='nomina')).latest('id')
        if public:
            self.assertEqual(feedback.author, nominator_email)

        # to check feedback comments are saved like enrypted data
        self.assertNotEqual(feedback.comments, comments)

        self.assertEqual(check_comments(feedback.comments, comments, self.privatekey_file), True)
        Nomination.objects.get(position=position,
                               candidate_name=candidate_name,
                               candidate_email=candidate_email,
                               candidate_phone=candidate_phone,
                               nominee=nominee,
                               comments=feedback,
                               nominator_email="%s%s" % (COMMUNITY_USER, EMAIL_DOMAIN))

    def test_add_questionnaire(self):
        self.access_chair_url(self.add_questionnaire_url)
        return self.add_questionnaire()
        self.client.logout()

    def add_questionnaire(self, *args, **kwargs):
        public = kwargs.pop('public', False)
        nominee_email = kwargs.pop('nominee_email', u'nominee@example.com')
        nominator_email = kwargs.pop('nominator_email', "%s%s" % (COMMUNITY_USER, EMAIL_DOMAIN))
        position_name = kwargs.pop('position', 'IAOC')

        self.nominate_view(public=public,
                           nominee_email=nominee_email,
                           position=position_name,
                           nominator_email=nominator_email)

        response = self.client.get(self.add_questionnaire_url)
        self.assertEqual(response.status_code, 200)

        nomcom = get_nomcom_by_year(self.year)
        if not nomcom.public_key:
            self.assertNotContains(response, "questionnnaireform")

        # save the cert file in tmp
        nomcom.public_key.storage.location = tempfile.gettempdir()
        nomcom.public_key.save('cert', File(open(self.cert_file.name, 'r')))

        response = self.client.get(self.add_questionnaire_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "questionnnaireform")

        position = Position.objects.get(name=position_name)
        nominee = Nominee.objects.get(email__address=nominee_email)

        comments = u'Test add questionnaire view. Comments with accents äöåÄÖÅ éáíóú âêîôû ü àèìòù.'

        test_data = {'comments': comments,
                     'nominee': '%s_%s' % (position.id, nominee.id)}

        response = self.client.post(self.add_questionnaire_url, test_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-success")

        ## check objects
        feedback = Feedback.objects.filter(positions__in=[position],
                                           nominees__in=[nominee],
                                           type=FeedbackType.objects.get(slug='questio')).latest('id')

        ## to check feedback comments are saved like enrypted data
        self.assertNotEqual(feedback.comments, comments)

        self.assertEqual(check_comments(feedback.comments, comments, self.privatekey_file), True)

    def test_public_feedback(self):
        login_testing_unauthorized(self, COMMUNITY_USER, self.public_feedback_url)
        return self.feedback_view(public=True)
        self.client.logout()

    def test_private_feedback(self):
        self.access_member_url(self.private_feedback_url)
        return self.feedback_view(public=False)
        self.client.logout()

    def feedback_view(self, *args, **kwargs):
        public = kwargs.pop('public', True)
        nominee_email = kwargs.pop('nominee_email', u'nominee@example.com')
        nominator_email = kwargs.pop('nominator_email', "%s%s" % (COMMUNITY_USER, EMAIL_DOMAIN))
        position_name = kwargs.pop('position', 'IAOC')

        self.nominate_view(public=public,
                           nominee_email=nominee_email,
                           position=position_name,
                           nominator_email=nominator_email)

        feedback_url = self.public_feedback_url
        if not public:
            feedback_url = self.private_feedback_url

        response = self.client.get(feedback_url)
        self.assertEqual(response.status_code, 200)

        nomcom = get_nomcom_by_year(self.year)
        if not nomcom.public_key:
            self.assertNotContains(response, "feedbackform")

        # save the cert file in tmp
        nomcom.public_key.storage.location = tempfile.gettempdir()
        nomcom.public_key.save('cert', File(open(self.cert_file.name, 'r')))

        response = self.client.get(feedback_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "feedbackform")

        position = Position.objects.get(name=position_name)
        nominee = Nominee.objects.get(email__address=nominee_email)

        comments = u'Test feedback view. Comments with accents äöåÄÖÅ éáíóú âêîôû ü àèìòù.'

        test_data = {'comments': comments,
                     'position_name': position.name,
                     'nominee_name': nominee.email.person.name,
                     'nominee_email': nominee.email.address}

        if public:
            test_data['nominator_email'] = nominator_email
            test_data['nominator_name'] = nominator_email

        feedback_url += "?nominee=%d&position=%d" % (nominee.id, position.id)

        nominee_position = NomineePosition.objects.get(nominee=nominee,
                                                       position=position)
        state = nominee_position.state
        if not state.slug == 'accepted':
            response = self.client.post(feedback_url, test_data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "info-message-error")
            # accept nomination
            nominee_position.state = NomineePositionState.objects.get(slug='accepted')
            nominee_position.save()

        response = self.client.post(feedback_url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "info-message-success")

        ## check objects
        feedback = Feedback.objects.filter(positions__in=[position],
                                           nominees__in=[nominee],
                                           type=FeedbackType.objects.get(slug='comment')).latest('id')
        if public:
            self.assertEqual(feedback.author, nominator_email)

        ## to check feedback comments are saved like enrypted data
        self.assertNotEqual(feedback.comments, comments)

        self.assertEqual(check_comments(feedback.comments, comments, self.privatekey_file), True)

        # recovery state
        if state != nominee_position.state:
            nominee_position.state = state
            nominee_position.save()


class NomineePositionStateSaveTest(TestCase):
    """Tests for the NomineePosition save override method"""
    # See ietf.utils.test_utils.TestCase for the use of perma_fixtures vs. fixtures
    perma_fixtures = ['nomcom_templates']

    def setUp(self):
        nomcom_test_data()
        self.nominee = Nominee.objects.get(email__person__name=COMMUNITY_USER)

    def test_state_autoset(self):
        """Verify state is autoset correctly"""
        position = Position.objects.get(name='APP')
        nominee_position = NomineePosition.objects.create(position=position,
                                                          nominee=self.nominee)
        self.assertEqual(nominee_position.state.slug, 'pending')

    def test_state_specified(self):
        """Verify state if specified"""
        position = Position.objects.get(name='INT')
        nominee_position = NomineePosition.objects.create(position=position,
                                                          nominee=self.nominee,
                                                          state=NomineePositionState.objects.get(slug='accepted'))
        self.assertEqual(nominee_position.state.slug, 'accepted')

    def test_nomine_position_unique(self):
        """Verify nomine and position are unique together"""
        position = Position.objects.get(name='OAM')
        NomineePosition.objects.create(position=position,
                                       nominee=self.nominee)
        nominee_position = NomineePosition(position=position, nominee=self.nominee)

        self.assertRaises(IntegrityError, nominee_position.save)


class FeedbackTest(TestCase):
    perma_fixtures = ['nomcom_templates']

    def setUp(self):
        nomcom_test_data()
        self.cert_file, self.privatekey_file = generate_cert()

    def test_encrypted_comments(self):

        nominee = Nominee.objects.get(email__person__name=COMMUNITY_USER)
        position = Position.objects.get(name='OAM')
        nomcom = position.nomcom

        # save the cert file in tmp
        nomcom.public_key.storage.location = tempfile.gettempdir()
        nomcom.public_key.save('cert', File(open(self.cert_file.name, 'r')))

        comments = u'Plain text. Comments with accents äöåÄÖÅ éáíóú âêîôû ü àèìòù.'
        feedback = Feedback.objects.create(nomcom=nomcom,
                                           comments=comments,
                                           type=FeedbackType.objects.get(slug='nomina'))
        feedback.positions.add(position)
        feedback.nominees.add(nominee)

        # to check feedback comments are saved like enrypted data
        self.assertNotEqual(feedback.comments, comments)

        self.assertEqual(check_comments(feedback.comments, comments, self.privatekey_file), True)

        os.unlink(self.privatekey_file.name)
        os.unlink(self.cert_file.name)

class ReminderTest(TestCase):
    perma_fixtures = ['nomcom_templates']

    def setUp(self):
        nomcom_test_data()
        self.nomcom = get_nomcom_by_year(NOMCOM_YEAR)
        self.cert_file, self.privatekey_file = generate_cert()
        self.nomcom.public_key.storage.location = tempfile.gettempdir()
        self.nomcom.public_key.save('cert', File(open(self.cert_file.name, 'r')))

        gen = Position.objects.get(nomcom=self.nomcom,name='GEN')
        rai = Position.objects.get(nomcom=self.nomcom,name='RAI')
        iab = Position.objects.get(nomcom=self.nomcom,name='IAB')

        today = datetime.date.today()
        t_minus_3 = today - datetime.timedelta(days=3)
        t_minus_4 = today - datetime.timedelta(days=4)
        n = get_or_create_nominee(self.nomcom,"Nominee 1","nominee1@example.org",gen,None)
        np = n.nomineeposition_set.get(position=gen)
        np.time = t_minus_3
        np.save()
        n = get_or_create_nominee(self.nomcom,"Nominee 1","nominee1@example.org",iab,None)
        np = n.nomineeposition_set.get(position=iab)
        np.state = NomineePositionState.objects.get(slug='accepted')
        np.time = t_minus_3
        np.save()
        n = get_or_create_nominee(self.nomcom,"Nominee 2","nominee2@example.org",rai,None)
        np = n.nomineeposition_set.get(position=rai)
        np.time = t_minus_4
        np.save()
        n = get_or_create_nominee(self.nomcom,"Nominee 2","nominee2@example.org",gen,None)
        np = n.nomineeposition_set.get(position=gen)
        np.state = NomineePositionState.objects.get(slug='accepted')
        np.time = t_minus_4
        np.save()
        feedback = Feedback.objects.create(nomcom=self.nomcom,
                                           comments='some non-empty comments',
                                           type=FeedbackType.objects.get(slug='questio'),
                                           user=User.objects.get(username=CHAIR_USER))
        feedback.positions.add(gen)
        feedback.nominees.add(n)

    def test_is_time_to_send(self):
        self.nomcom.reminder_interval = 4
        today = datetime.date.today()
        self.assertTrue(is_time_to_send(self.nomcom,today+datetime.timedelta(days=4),today))
        for delta in range(4):
            self.assertFalse(is_time_to_send(self.nomcom,today+datetime.timedelta(days=delta),today))
        self.nomcom.reminder_interval = None
        self.assertFalse(is_time_to_send(self.nomcom,today,today))
        self.nomcom.reminderdates_set.create(date=today)
        self.assertTrue(is_time_to_send(self.nomcom,today,today))

    def test_command(self):
        c = Command()
        messages_before=len(outbox)
        self.nomcom.reminder_interval = 3
        self.nomcom.save()
        c.handle(None,None)
        self.assertEqual(len(outbox), messages_before + 2)
        self.assertTrue('nominee1@example.org' in outbox[-1]['To'])
        self.assertTrue('please complete' in outbox[-1]['Subject'])
        self.assertTrue('nominee1@example.org' in outbox[-2]['To'])
        self.assertTrue('please accept' in outbox[-2]['Subject'])
        messages_before=len(outbox)
        self.nomcom.reminder_interval = 4
        self.nomcom.save()
        c.handle(None,None)
        self.assertEqual(len(outbox), messages_before + 1)
        self.assertTrue('nominee2@example.org' in outbox[-1]['To'])
        self.assertTrue('please accept' in outbox[-1]['Subject'])
     
    def test_remind_accept_view(self):
        url = reverse('nomcom_send_reminder_mail', kwargs={'year': NOMCOM_YEAR,'type':'accept'})
        login_testing_unauthorized(self, CHAIR_USER, url)
        messages_before=len(outbox)
        test_data = {'selected': [x.id for x in Nominee.objects.filter(nomcom=self.nomcom)]}
        response = self.client.post(url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(outbox), messages_before + 2)

    def test_remind_questionnaire_view(self):
        url = reverse('nomcom_send_reminder_mail', kwargs={'year': NOMCOM_YEAR,'type':'questionnaire'})
        login_testing_unauthorized(self, CHAIR_USER, url)
        messages_before=len(outbox)
        test_data = {'selected': [x.id for x in Nominee.objects.filter(nomcom=self.nomcom)]}
        response = self.client.post(url, test_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(outbox), messages_before + 1)

