from django.core.urlresolvers import reverse
from ietf.utils.test_utils import TestCase

from ietf.meeting.models import Meeting
from ietf.utils.test_data import make_test_data


SECR_USER='secretary'

class MainTestCase(TestCase):
    def test_main(self):
        "Main Test"
        url = reverse('meetings')
        response = self.client.get(url, REMOTE_USER=SECR_USER)
        self.assertEqual(response.status_code, 200)

    def test_view(self):
        "View Test"
        make_test_data()
        meeting = Meeting.objects.all()[0]
        url = reverse('meetings_view', kwargs={'meeting_id':meeting.number})
        response = self.client.get(url, REMOTE_USER=SECR_USER)
        self.assertEqual(response.status_code, 200)
