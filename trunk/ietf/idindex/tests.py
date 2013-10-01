import datetime, shutil

from django.core.urlresolvers import reverse as urlreverse

from ietf.utils.test_data import make_test_data
from ietf.utils import TestCase

from ietf.doc.models import *
from ietf.idindex.index import *


class IndexTestCase(TestCase):
    # See ietf.utils.test_utils.TestCase for the use of perma_fixtures vs. fixtures
    perma_fixtures = ['names']

    def setUp(self):
        self.id_dir = os.path.abspath("tmp-id-dir")
        os.mkdir(self.id_dir)
        settings.INTERNET_DRAFT_PATH = self.id_dir

    def tearDown(self):
        shutil.rmtree(self.id_dir)
        
    def write_draft_file(self, name, size):
        with open(os.path.join(self.id_dir, name), 'w') as f:
            f.write("a" * size)

    def test_all_id_txt(self):
        draft = make_test_data()

        # active in IESG process
        draft.set_state(State.objects.get(type="draft", slug="active"))
        draft.set_state(State.objects.get(type="draft-iesg", slug="lc"))

        txt = all_id_txt()

        self.assertTrue(draft.name + "-" + draft.rev in txt)
        self.assertTrue(draft.get_state("draft-iesg").name in txt)

        # not active in IESG process
        draft.unset_state("draft-iesg")

        txt = all_id_txt()
        self.assertTrue(draft.name + "-" + draft.rev in txt)
        self.assertTrue("Active" in txt)

        # published
        draft.set_state(State.objects.get(type="draft", slug="rfc"))
        DocAlias.objects.create(name="rfc1234", document=draft)

        txt = all_id_txt()
        self.assertTrue(draft.name + "-" + draft.rev in txt)
        self.assertTrue("RFC\t1234" in txt)

        # replaced
        draft.set_state(State.objects.get(type="draft", slug="repl"))

        RelatedDocument.objects.create(
            relationship=DocRelationshipName.objects.get(slug="replaces"),
            source=Document.objects.create(type_id="draft", rev="00", name="draft-test-replacement"),
            target=draft.docalias_set.get(name__startswith="draft"))

        txt = all_id_txt()
        self.assertTrue(draft.name + "-" + draft.rev in txt)
        self.assertTrue("Replaced replaced by draft-test-replacement" in txt)

    def test_all_id2_txt(self):
        draft = make_test_data()

        def get_fields(content):
            self.assertTrue(draft.name + "-" + draft.rev in content)

            for line in content.splitlines():
                if line.startswith(draft.name + "-" + draft.rev):
                    return line.split("\t")
        # test Active
        draft.set_state(State.objects.get(type="draft", slug="active"))
        draft.set_state(State.objects.get(type="draft-iesg", slug="review-e"))

        NewRevisionDocEvent.objects.create(doc=draft, type="new_revision", rev=draft.rev, by=draft.ad)

        self.write_draft_file("%s-%s.txt" % (draft.name, draft.rev), 5000)
        self.write_draft_file("%s-%s.pdf" % (draft.name, draft.rev), 5000)

        t = get_fields(all_id2_txt())
        self.assertEqual(t[0], draft.name + "-" + draft.rev)
        self.assertEqual(t[1], "-1")
        self.assertEqual(t[2], "Active")
        self.assertEqual(t[3], "Expert Review")
        self.assertEqual(t[4], "")
        self.assertEqual(t[5], "")
        self.assertEqual(t[6], draft.latest_event(type="new_revision").time.strftime("%Y-%m-%d"))
        self.assertEqual(t[7], draft.group.acronym)
        self.assertEqual(t[8], draft.group.parent.acronym)
        self.assertEqual(t[9], unicode(draft.ad))
        self.assertEqual(t[10], draft.intended_std_level.name)
        self.assertEqual(t[11], "")
        self.assertEqual(t[12], ".pdf,.txt")
        self.assertEqual(t[13], draft.title)
        author = draft.documentauthor_set.order_by("order").get()
        self.assertEqual(t[14], "%s <%s>" % (author.author.person.name, author.author.address))
        self.assertEqual(t[15], "%s <%s>" % (draft.shepherd, draft.shepherd.email_address()))
        self.assertEqual(t[16], "%s <%s>" % (draft.ad, draft.ad.email_address()))


        # test RFC
        draft.set_state(State.objects.get(type="draft", slug="rfc"))
        DocAlias.objects.create(name="rfc1234", document=draft)
        t = get_fields(all_id2_txt())
        self.assertEqual(t[4], "1234")

        # test Replaced
        draft.set_state(State.objects.get(type="draft", slug="repl"))
        RelatedDocument.objects.create(
            relationship=DocRelationshipName.objects.get(slug="replaces"),
            source=Document.objects.create(type_id="draft", rev="00", name="draft-test-replacement"),
            target=draft.docalias_set.get(name__startswith="draft"))

        t = get_fields(all_id2_txt())
        self.assertEqual(t[5], "draft-test-replacement")

        # test Last Call
        draft.set_state(State.objects.get(type="draft", slug="active"))
        draft.set_state(State.objects.get(type="draft-iesg", slug="lc"))

        e = LastCallDocEvent.objects.create(doc=draft, type="sent_last_call", expires=datetime.datetime.now() + datetime.timedelta(days=14), by=draft.ad)

        DocAlias.objects.create(name="rfc1234", document=draft)
        t = get_fields(all_id2_txt())
        self.assertEqual(t[11], e.expires.strftime("%Y-%m-%d"))


    def test_id_index_txt(self):
        draft = make_test_data()

        draft.set_state(State.objects.get(type="draft", slug="active"))

        txt = id_index_txt()

        self.assertTrue(draft.name + "-" + draft.rev in txt)
        self.assertTrue(draft.title in txt)

        self.assertTrue(draft.abstract[:20] not in txt)

        txt = id_index_txt(with_abstracts=True)

        self.assertTrue(draft.abstract[:20] in txt)
