import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_wallet_me_returns_authenticated_user_wallet(authenticated_client, wallet_user):
    response = authenticated_client.get(reverse("wallet-me"))

    assert response.status_code == 200
    assert response.data["user"] == wallet_user.id
    assert response.data["currency"] == "USD"
    assert response.data["balance"] == "0.00"


@pytest.mark.django_db
def test_wallet_me_requires_authentication(api_client):
    response = api_client.get(reverse("wallet-me"))

    assert response.status_code == 401