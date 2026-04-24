"""Tests for lib.sources.arxiv_pdf."""

import time
from pathlib import Path

import pytest
import responses

from lib.sources.arxiv_pdf import (
    download_pdf,
    InvalidArxivIdError,
)


PDF_BYTES = b"%PDF-1.4\n%EOF"


@responses.activate
def test_download_new_pdf(tmp_path):
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out == tmp_path / "2603.27703.pdf"
    assert out.read_bytes() == PDF_BYTES


@responses.activate
def test_cache_hit_within_7_days(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"cached-content")
    # mtime is now; well within 7 days
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out.read_bytes() == b"cached-content"
    assert len(responses.calls) == 0  # no network call


@responses.activate
def test_cache_expired(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"old")
    old_time = time.time() - (8 * 86400)  # 8 days ago
    import os
    os.utime(cached, (old_time, old_time))
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out.read_bytes() == PDF_BYTES  # re-downloaded


@responses.activate
def test_force_bypasses_cache(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"cached")
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path, force=True)
    assert out.read_bytes() == PDF_BYTES


@responses.activate
def test_download_retries_on_network_error(tmp_path):
    import requests
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=requests.ConnectionError("boom"),
    )
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=requests.ConnectionError("boom again"),
    )
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf(
        "2603.27703",
        cache_dir=tmp_path,
        retry_backoff=0,  # no real sleep in tests
    )
    assert out.read_bytes() == PDF_BYTES
    assert len(responses.calls) == 3


def test_invalid_arxiv_id_format(tmp_path):
    with pytest.raises(InvalidArxivIdError):
        download_pdf("cs/0601001", cache_dir=tmp_path)
    with pytest.raises(InvalidArxivIdError):
        download_pdf("not-an-id", cache_dir=tmp_path)
