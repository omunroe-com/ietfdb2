import debug    # pyflakes:ignore
import factory
import datetime

from django.conf import settings

from ietf.doc.models import Document, DocEvent, NewRevisionDocEvent, DocAlias, State, DocumentAuthor, StateDocEvent
from ietf.group.models import Group

def draft_name_generator(type_id,group,n):
        return '%s-%s-%s-%s%d'%( 
              type_id,
              'bogusperson',
              group.acronym if group else 'netherwhere',
              'musings',
              n,
            )

class BaseDocumentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Faker('sentence',nb_words=6)
    rev = '00'
    std_level_id = None
    intended_std_level_id = None
    time = datetime.datetime.now()
    expires = factory.LazyAttribute(lambda o: o.time+datetime.timedelta(days=settings.INTERNET_DRAFT_DAYS_TO_EXPIRE))

    @factory.lazy_attribute_sequence
    def name(self, n):
        return draft_name_generator(self.type_id,self.group,n)

    newrevisiondocevent = factory.RelatedFactory('ietf.doc.factories.NewRevisionDocEventFactory','doc')

    alias = factory.RelatedFactory('ietf.doc.factories.DocAliasFactory','document')

    @factory.post_generation
    def other_aliases(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        if create and extracted:
            for alias in extracted:
                obj.docalias_set.create(name=alias) 

    @factory.post_generation
    def states(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        if create and extracted:
            for (state_type_id,state_slug) in extracted:
                obj.set_state(State.objects.get(type_id=state_type_id,slug=state_slug))

    @factory.post_generation
    def authors(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        if create and extracted:
            order = 0
            for person in extracted:
                DocumentAuthor.objects.create(document=obj, person=person, email=person.email(), order=order)
                order += 1

    @factory.post_generation
    def relations(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        if create and extracted:
            for (rel_id,docalias) in extracted:
                if isinstance(docalias,Document):
                    docalias = docalias.docalias_set.first()
                obj.relateddocument_set.create(relationship_id=rel_id,target=docalias)

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results:
            # Some post-generation hooks ran, and may have modified us.
            obj._has_an_event_so_saving_is_allowed = True
            obj.save()

#TODO remove this - rename BaseDocumentFactory to DocumentFactory
class DocumentFactory(BaseDocumentFactory):

    type_id = 'draft'
    group = factory.SubFactory('ietf.group.factories.GroupFactory',acronym='none')


class IndividualDraftFactory(BaseDocumentFactory):

    type_id = 'draft'
    group = factory.SubFactory('ietf.group.factories.GroupFactory',acronym='none')

    @factory.post_generation
    def states(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for (state_type_id,state_slug) in extracted:
                obj.set_state(State.objects.get(type_id=state_type_id,slug=state_slug))
        else:
            obj.set_state(State.objects.get(type_id='draft',slug='active'))

class IndividualRfcFactory(IndividualDraftFactory):

    alias2 = factory.RelatedFactory('ietf.doc.factories.DocAliasFactory','document',name=factory.Sequence(lambda n: 'rfc%04d'%(n+1000)))

    @factory.post_generation
    def states(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for (state_type_id,state_slug) in extracted:
                obj.set_state(State.objects.get(type_id=state_type_id,slug=state_slug))
        else:
            obj.set_state(State.objects.get(type_id='draft',slug='rfc'))

class WgDraftFactory(BaseDocumentFactory):

    type_id = 'draft'
    group = factory.SubFactory('ietf.group.factories.GroupFactory',type_id='wg')
    stream_id = 'ietf'

    @factory.post_generation
    def states(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for (state_type_id,state_slug) in extracted:
                obj.set_state(State.objects.get(type_id=state_type_id,slug=state_slug))
        else:
            obj.set_state(State.objects.get(type_id='draft',slug='active'))
            obj.set_state(State.objects.get(type_id='draft-stream-ietf',slug='wg-doc'))

class WgRfcFactory(WgDraftFactory):

    alias2 = factory.RelatedFactory('ietf.doc.factories.DocAliasFactory','document',name=factory.Sequence(lambda n: 'rfc%04d'%(n+1000)))

    std_level_id = 'ps'

    @factory.post_generation
    def states(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for (state_type_id,state_slug) in extracted:
                obj.set_state(State.objects.get(type_id=state_type_id,slug=state_slug))
        else:
            obj.set_state(State.objects.get(type_id='draft',slug='rfc'))

class CharterFactory(BaseDocumentFactory):

    type_id = 'charter'
    group = factory.SubFactory('ietf.group.factories.GroupFactory',type_id='wg')
    name = factory.LazyAttribute(lambda o: 'charter-ietf-%s'%o.group.acronym)

    @factory.post_generation
    def set_group_charter_document(obj, create, extracted, **kwargs):
        if not create:
            return
        obj.group.charter = extracted or obj
        obj.group.save()

class ConflictReviewFactory(BaseDocumentFactory):
    type_id='conflrev'
    
    @factory.post_generation
    def review_of(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            obj.relateddocument_set.create(relationship_id='conflrev',target=extracted.docalias_set.first())
        else:
            obj.relateddocument_set.create(relationship_id='conflrev',target=DocumentFactory(type_id='draft',group=Group.objects.get(type_id='individ')).docalias_set.first())

    @factory.post_generation
    def states(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for state in extracted:
                obj.set_state(state)
        else:
            obj.set_state(State.objects.get(type_id='conflrev',slug='iesgeval'))

class DocAliasFactory(factory.DjangoModelFactory):
    class Meta:
        model = DocAlias

    document = factory.SubFactory('ietf.doc.factories.DocumentFactory')

    @factory.lazy_attribute
    def name(self):
        return self.document.name
    

class DocEventFactory(factory.DjangoModelFactory):
    class Meta:
        model = DocEvent

    type = 'added_comment'
    by = factory.SubFactory('ietf.person.factories.PersonFactory')
    doc = factory.SubFactory(DocumentFactory)
    desc = factory.Faker('sentence',nb_words=6)

    @factory.lazy_attribute
    def rev(self):
        return self.doc.rev

class NewRevisionDocEventFactory(DocEventFactory):
    class Meta:
        model = NewRevisionDocEvent

    type = 'new_revision'
    rev = '00'

    @factory.lazy_attribute
    def desc(self):
         return 'New version available %s-%s'%(self.doc.name,self.rev)

class StateDocEventFactory(DocEventFactory):
    class Meta:
        model = StateDocEvent

    type = 'changed_state'
    state_type_id = 'draft-iesg'

    @factory.post_generation
    def state(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            (state_type_id, state_slug) = extracted
            obj.state = State.objects.get(type_id=state_type_id,slug=state_slug)
        else:
            obj.state = State.objects.get(type_id='draft-iesg',slug='ad-eval')
        obj.save()
