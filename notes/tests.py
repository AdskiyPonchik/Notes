from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Note, Participant

User = get_user_model()


def make_user(username, email, password='StrongPass123!', verified=True):
    user = User.objects.create_user(username=username, email=email, password=password)
    participant = user.participant
    participant.email_verified = verified
    participant.save()
    return user


class ParticipantSignalTests(TestCase):
    def test_participant_created_with_user(self):
        user = User.objects.create_user(username='alice', email='alice@example.com')
        self.assertTrue(Participant.objects.filter(user=user).exists())
        self.assertFalse(user.participant.email_verified)


class SignupTests(TestCase):
    def test_signup_creates_user_and_sends_verification_email(self):
        response = self.client.post(reverse('signup'), {
            'username': 'bob',
            'email': 'bob@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('confirm_email'))
        user = User.objects.get(username='bob')
        self.assertFalse(user.participant.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('bob@example.com', mail.outbox[0].to)

    def test_signup_rejects_duplicate_email(self):
        make_user('carol', 'carol@example.com')
        response = self.client.post(reverse('signup'), {
            'username': 'carol2',
            'email': 'carol@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='carol2').exists())
        self.assertFormError(response.context['form'], 'email',
                             'An account with this email already exists.')


class LoginTests(TestCase):
    def test_unverified_user_gets_error_and_resent_email(self):
        make_user('dave', 'dave@example.com', verified=False)
        response = self.client.post(reverse('login'), {
            'username': 'dave',
            'password': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email not verified')
        self.assertEqual(len(mail.outbox), 1)

    def test_verified_user_logs_in(self):
        make_user('erin', 'erin@example.com')
        response = self.client.post(reverse('login'), {
            'username': 'erin',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('home'))


class EmailVerifyTests(TestCase):
    def test_valid_token_verifies_and_logs_in(self):
        user = make_user('frank', 'frank@example.com', verified=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token}))
        self.assertRedirects(response, reverse('home'))
        user.participant.refresh_from_db()
        self.assertTrue(user.participant.email_verified)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_invalid_token_redirects(self):
        user = make_user('grace', 'grace@example.com', verified=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': 'not-a-token'}))
        self.assertRedirects(response, reverse('invalid_token'))
        user.participant.refresh_from_db()
        self.assertFalse(user.participant.email_verified)


class NoteViewTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice', 'alice@example.com')
        self.bob = make_user('bob', 'bob@example.com')
        self.alice_note = Note.objects.create(
            title='Alice note', text='secret', participant=self.alice.participant)

    def test_home_requires_login(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_home_shows_only_own_notes(self):
        self.client.force_login(self.bob)
        response = self.client.get(reverse('home'))
        self.assertNotIn(self.alice_note, response.context['notes'])

        self.client.force_login(self.alice)
        response = self.client.get(reverse('home'))
        self.assertIn(self.alice_note, response.context['notes'])

    def test_get_notes_filters_by_user(self):
        self.client.force_login(self.bob)
        response = self.client.get(reverse('get_notes'),
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.json()['notes'], [])

        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'),
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        data = response.json()['notes']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Alice note')

    def test_get_notes_view_filter_and_counts(self):
        Note.objects.create(title='Archived', text='old', status=Note.Status.ARCHIVED,
                            participant=self.alice.participant)
        Note.objects.create(title='Trashed', text='gone', status=Note.Status.TRASH,
                            participant=self.alice.participant)
        self.client.force_login(self.alice)

        response = self.client.get(reverse('get_notes'), {'filter': 'archived'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        data = response.json()
        self.assertEqual([n['title'] for n in data['notes']], ['Archived'])
        self.assertEqual(data['counts'], {'active': 1, 'archived': 1, 'trash': 1})

        response = self.client.get(reverse('get_notes'), {'filter': 'trash'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual([n['title'] for n in response.json()['notes']], ['Trashed'])

    def test_get_notes_active_includes_favorites(self):
        Note.objects.create(title='Starred', text='fav', status=Note.Status.FAVORITE,
                            participant=self.alice.participant)
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'), {'filter': 'active'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        titles = [n['title'] for n in response.json()['notes']]
        self.assertEqual(titles, ['Alice note', 'Starred'])

    def test_get_notes_rejects_unknown_filter(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'), {'filter': 'bogus'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 400)

    def test_get_notes_extracts_tags(self):
        Note.objects.create(title='Tagged', text='Buy #milk and #Milk plus #to-do items',
                            participant=self.alice.participant)
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'),
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        tagged = [n for n in response.json()['notes'] if n['title'] == 'Tagged'][0]
        self.assertEqual(tagged['tags'], ['milk', 'to-do'])

    def test_get_notes_filters_by_tag_param(self):
        Note.objects.create(title='Tagged', text='Buy #milk today',
                            participant=self.alice.participant)
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'), {'tag': 'milk'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        titles = [n['title'] for n in response.json()['notes']]
        self.assertEqual(titles, ['Tagged'])

    def test_get_notes_tag_param_accepts_hash_prefix_and_case(self):
        Note.objects.create(title='Tagged', text='Buy #Milk today',
                            participant=self.alice.participant)
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'), {'tag': '#MILK'},
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        titles = [n['title'] for n in response.json()['notes']]
        self.assertEqual(titles, ['Tagged'])

    def test_get_notes_rejects_non_ajax(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'))
        self.assertEqual(response.status_code, 400)

    def test_create_note_attaches_to_current_participant(self):
        self.client.force_login(self.bob)
        response = self.client.post(reverse('home'),
                                    {'title': 'Bob note', 'text': 'hello'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        note = Note.objects.get(title='Bob note')
        self.assertEqual(note.participant, self.bob.participant)

    def test_create_note_invalid_returns_400(self):
        self.client.force_login(self.bob)
        response = self.client.post(reverse('home'), {'title': '', 'text': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
        self.assertIn('title', response.json()['errors'])


class UpdateNoteTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice', 'alice@example.com')
        self.bob = make_user('bob', 'bob@example.com')
        self.note = Note.objects.create(
            title='Alice note', text='secret', participant=self.alice.participant)

    def update(self, note_id, payload, client=None):
        client = client or self.client
        return client.post(
            reverse('update_note', kwargs={'note_id': note_id}),
            payload, content_type='application/json',
            headers={'X-Requested-With': 'XMLHttpRequest'})

    def test_requires_login(self):
        response = self.update(self.note.pk, {'title': 'Hacked'})
        self.assertEqual(response.status_code, 302)

    def test_updates_own_note_fields(self):
        self.client.force_login(self.alice)
        response = self.update(self.note.pk, {'title': 'Renamed', 'text': 'updated'})
        self.assertEqual(response.status_code, 200)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Renamed')
        self.assertEqual(self.note.text, 'updated')
        self.assertEqual(response.json()['note']['title'], 'Renamed')

    def test_toggles_status(self):
        self.client.force_login(self.alice)
        response = self.update(self.note.pk, {'status': Note.Status.FAVORITE})
        self.assertEqual(response.status_code, 200)
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, Note.Status.FAVORITE)

    def test_cannot_update_another_users_note(self):
        self.client.force_login(self.bob)
        response = self.update(self.note.pk, {'title': 'Hijacked'})
        self.assertEqual(response.status_code, 404)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Alice note')

    def test_rejects_invalid_status(self):
        self.client.force_login(self.alice)
        response = self.update(self.note.pk, {'status': 'X'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('status', response.json()['errors'])

    def test_rejects_empty_title(self):
        self.client.force_login(self.alice)
        response = self.update(self.note.pk, {'title': '   '})
        self.assertEqual(response.status_code, 400)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Alice note')

    def test_rejects_empty_payload(self):
        self.client.force_login(self.alice)
        response = self.update(self.note.pk, {})
        self.assertEqual(response.status_code, 400)

    def test_rejects_non_ajax(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('update_note', kwargs={'note_id': self.note.pk}),
            {'title': 'Nope'})
        self.assertEqual(response.status_code, 400)

    def test_accepts_form_encoded_post(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('update_note', kwargs={'note_id': self.note.pk}),
            {'title': 'Via form'},
            headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, 'Via form')


class NoteActionTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice', 'alice@example.com')
        self.bob = make_user('bob', 'bob@example.com')
        self.note = Note.objects.create(
            title='Alice note', text='secret', participant=self.alice.participant)

    def act(self, action, note_id=None):
        return self.client.post(
            reverse('note_action', kwargs={'note_id': note_id or self.note.pk,
                                           'action': action}),
            headers={'X-Requested-With': 'XMLHttpRequest'})

    def test_archive_trash_restore_cycle(self):
        self.client.force_login(self.alice)
        for action, expected in [('archive', Note.Status.ARCHIVED),
                                 ('trash', Note.Status.TRASH),
                                 ('restore', Note.Status.ACTIVE)]:
            response = self.act(action)
            self.assertEqual(response.status_code, 200)
            self.note.refresh_from_db()
            self.assertEqual(self.note.status, expected)
            self.assertEqual(response.json()['note']['status'], expected)

    def test_unknown_action_404s(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.act('explode').status_code, 404)

    def test_cannot_move_another_users_note(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.act('trash').status_code, 404)
        self.note.refresh_from_db()
        self.assertEqual(self.note.status, Note.Status.ACTIVE)

    def test_rejects_non_ajax(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse('note_action', kwargs={'note_id': self.note.pk, 'action': 'archive'}))
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.assertEqual(self.act('archive').status_code, 302)
