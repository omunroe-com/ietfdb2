import os
import factory
import faker 
import shutil
import random
import faker.config
from unidecode import unidecode

from django.conf import settings
from django.contrib.auth.models import User

import debug                            # pyflakes:ignore

from ietf.person.models import Person, Alias, Email

fake = faker.Factory.create()

class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)
        exclude = ['locale', ]

    locale = random.sample(faker.config.AVAILABLE_LOCALES, 1)[0]
    first_name = factory.Faker('first_name', locale)
    last_name = factory.Faker('last_name', locale)
    email = factory.LazyAttributeSequence(lambda u, n: '%s.%s_%d@%s'%(unidecode(u.first_name),unidecode(u.last_name),n, fake.domain_name()))
    username = factory.LazyAttribute(lambda u: u.email)

    @factory.post_generation
    def set_password(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        obj.set_password( '%s+password' % obj.username ) # pylint: disable=no-value-for-parameter

class PersonFactory(factory.DjangoModelFactory):
    class Meta:
        model = Person

    user = factory.SubFactory(UserFactory)
    name = factory.LazyAttribute(lambda p: '%s %s'%(p.user.first_name,p.user.last_name))
    ascii = factory.LazyAttribute(lambda p: unicode(unidecode(p.name).strip()))

    class Params:
        with_bio = factory.Trait(
            biography = u"\n\n".join(fake.paragraphs()),
        )

    @factory.post_generation
    def default_aliases(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        make_alias = getattr(AliasFactory, 'create' if create else 'build')
        make_alias(person=obj,name=obj.name)
        make_alias(person=obj,name=obj.ascii)

    @factory.post_generation
    def default_emails(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        make_email = getattr(EmailFactory, 'create' if create else 'build')
        make_email(person=obj,address=obj.user.email)

    @factory.post_generation
    def default_photo(obj, create, extracted, **kwargs): # pylint: disable=no-self-argument
        import atexit
        if obj.biography:
            photo_name = obj.photo_name()
            media_name = u"%s/%s.jpg" % (settings.PHOTOS_DIRNAME, photo_name)
            obj.photo = media_name
            obj.photo_thumb = media_name
            photosrc = os.path.join(settings.TEST_DATA_DIR, "profile-default.jpg")
            photodst = os.path.join(settings.PHOTOS_DIR,  photo_name + '.jpg')
            if not os.path.exists(photodst):
                shutil.copy(photosrc, photodst)
            def delete_file(file):
                os.unlink(file)
            atexit.register(delete_file, photodst)

class AliasFactory(factory.DjangoModelFactory):
    class Meta:
        model = Alias

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        person = kwargs['person']
        name = kwargs['name']
        existing_aliases = set(model_class.objects.filter(person=person).values_list('name', flat=True))
        if not name in existing_aliases:
            obj = model_class(*args, **kwargs)
            obj.save()
            return obj

    name = factory.Faker('name')

class EmailFactory(factory.DjangoModelFactory):
    class Meta:
        model = Email
        django_get_or_create = ('address',)

    address = factory.Sequence(lambda n:'%s.%s_%d@%s' % (fake.first_name(),fake.last_name(),n,fake.domain_name()))
    active = True
    primary = False