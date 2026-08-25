from email.message import Message
from urllib.error import HTTPError

import pytest

import agent_readable_site.fetch as fetch_module
from agent_readable_site.fetch import FetchFailure, fetch_text


def test_redirect_loop_has_specific_message(monkeypatch) -> None:
    url = "https://loop.invalid/start"

    def redirect_loop(request, timeout):
        raise HTTPError(
            request.full_url,
            302,
            "The HTTP server returned a redirect error that would lead to an infinite loop.",
            Message(),
            None,
        )

    monkeypatch.setattr(fetch_module, "urlopen", redirect_loop)

    with pytest.raises(FetchFailure) as caught:
        fetch_text(url)

    assert str(caught.value) == f"redirect loop detected for {url}: too many redirects"
