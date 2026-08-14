from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webhook.models import Webhook

User = get_user_model()


def _fake_external_resolution(hostname, *args, **kwargs):
    """Pretends any non-internal hostname resolves to a public IP."""
    return [(2, 1, 6, "", ("93.184.216.34", 0))]


@pytest.mark.django_db
class TestWebhookSubscriptionScoping:
    def test_user_can_create_and_list_own_webhook(self):
        user = User.objects.create_user(username="alice", password="pass12345")
        client = APIClient()
        client.force_authenticate(user)

        with patch("webhook.validators.socket.getaddrinfo", side_effect=_fake_external_resolution):
            response = client.post(
                "/webhooks/subscriptions/",
                {"url": "https://alice.example.com/hook", "event": "payment_completed"},
            )

        assert response.status_code == 201
        assert Webhook.objects.filter(user=user).count() == 1

        response = client.get("/webhooks/subscriptions/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_user_cannot_see_or_modify_another_users_webhook(self):
        alice = User.objects.create_user(username="alice2", password="pass12345")
        bob = User.objects.create_user(username="bob2", password="pass12345")

        webhook = Webhook.objects.create(
            user=alice, url="https://alice.example.com/hook", event="payment_completed"
        )

        client = APIClient()
        client.force_authenticate(bob)

        response = client.get("/webhooks/subscriptions/")
        assert response.status_code == 200
        assert response.data == []

        response = client.get(f"/webhooks/subscriptions/{webhook.id}/")
        assert response.status_code == 404

        response = client.patch(f"/webhooks/subscriptions/{webhook.id}/", {"is_active": False})
        assert response.status_code == 404

        response = client.delete(f"/webhooks/subscriptions/{webhook.id}/")
        assert response.status_code == 404

        webhook.refresh_from_db()
        assert webhook.is_active is True

    def test_user_can_update_and_delete_own_webhook(self):
        alice = User.objects.create_user(username="alice3", password="pass12345")
        webhook = Webhook.objects.create(
            user=alice, url="https://alice.example.com/hook", event="payment_completed"
        )

        client = APIClient()
        client.force_authenticate(alice)

        response = client.patch(f"/webhooks/subscriptions/{webhook.id}/", {"is_active": False})
        assert response.status_code == 200
        assert response.data["is_active"] is False

        response = client.delete(f"/webhooks/subscriptions/{webhook.id}/")
        assert response.status_code == 204
        assert Webhook.objects.filter(id=webhook.id).count() == 0

    def test_unauthenticated_user_cannot_access_subscriptions(self):
        client = APIClient()
        response = client.get("/webhooks/subscriptions/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestWebhookDispatchIsScopedToParticipants:
    def test_only_participants_wallets_receive_the_event(self):
        from services.webhook_services import WebhookService

        sender = User.objects.create_user(username="sender1", password="pass12345")
        receiver = User.objects.create_user(username="receiver1", password="pass12345")
        outsider = User.objects.create_user(username="outsider1", password="pass12345")

        Webhook.objects.create(user=sender, url="https://s.example.com/hook", event="payment_completed")
        Webhook.objects.create(user=receiver, url="https://r.example.com/hook", event="payment_completed")
        Webhook.objects.create(user=outsider, url="https://o.example.com/hook", event="payment_completed")

        with patch("services.webhook_services.requests.post") as mock_post:
            WebhookService.send_event(
                "payment_completed",
                {"x": 1},
                user_ids=[sender.id, receiver.id],
            )

        called_urls = {call.args[0] for call in mock_post.call_args_list}
        assert called_urls == {"https://s.example.com/hook", "https://r.example.com/hook"}

    def test_dispatch_does_not_follow_redirects(self):
        from services.webhook_services import WebhookService

        user = User.objects.create_user(username="redirtest", password="pass12345")
        Webhook.objects.create(user=user, url="https://s.example.com/hook", event="payment_completed")

        with patch("services.webhook_services.requests.post") as mock_post:
            WebhookService.send_event("payment_completed", {"x": 1}, user_ids=[user.id])

        assert mock_post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.django_db
class TestWebhookUrlSsrfProtection:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/hook",
            "http://localhost/hook",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.5/hook",
            "http://192.168.1.10/hook",
            "http://[::1]/hook",
            "ftp://example.com/hook",
        ],
    )
    def test_rejects_internal_or_disallowed_urls(self, url):
        user = User.objects.create_user(username="ssrf_tester", password="pass12345")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            "/webhooks/subscriptions/",
            {"url": url, "event": "payment_completed"},
        )

        assert response.status_code == 400
        assert Webhook.objects.filter(user=user).count() == 0

    def test_accepts_a_public_https_url(self):
        user = User.objects.create_user(username="legit_user", password="pass12345")
        client = APIClient()
        client.force_authenticate(user)

        with patch("webhook.validators.socket.getaddrinfo", side_effect=_fake_external_resolution):
            response = client.post(
                "/webhooks/subscriptions/",
                {"url": "https://myapp.example.com/webhooks/payflow", "event": "payment_completed"},
            )

        assert response.status_code == 201

    def test_rejects_hostname_that_resolves_to_private_ip(self):
        """
        Simulates a public-looking hostname that actually resolves to an
        internal address (the DNS-rebinding style case) — resolution is
        still checked even though the scheme/hostname look legitimate.
        """
        user = User.objects.create_user(username="rebind_tester", password="pass12345")
        client = APIClient()
        client.force_authenticate(user)

        def _fake_internal_resolution(hostname, *args, **kwargs):
            return [(2, 1, 6, "", ("10.0.0.5", 0))]

        with patch("webhook.validators.socket.getaddrinfo", side_effect=_fake_internal_resolution):
            response = client.post(
                "/webhooks/subscriptions/",
                {"url": "https://looks-legit.example.com/hook", "event": "payment_completed"},
            )

        assert response.status_code == 400
        assert Webhook.objects.filter(user=user).count() == 0