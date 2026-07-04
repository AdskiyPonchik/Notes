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
        self.assertEqual(response.json(), [])

        self.client.force_login(self.alice)
        response = self.client.get(reverse('get_notes'),
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Alice note')

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
