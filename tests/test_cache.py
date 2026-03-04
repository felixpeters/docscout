"""Tests for the SQLite cache layer."""

import os

import pytest

from docscout.cache import Cache
from docscout.models import FileResult


@pytest.fixture
def tmp_cache(tmp_path):
    """Create a Cache instance in a temp directory."""
    return Cache(cache_dir=tmp_path / "cache")


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for cache testing."""
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"fake pdf content for testing")
    return f


@pytest.fixture
def sample_result(sample_file):
    """Create a sample FileResult."""
    return FileResult(
        file_path=str(sample_file),
        file_name=sample_file.name,
        file_size_bytes=sample_file.stat().st_size,
        file_type="pdf",
        file_category="documents",
        page_count=5,
        word_count=1000,
        char_count=6000,
        table_count=2,
        figure_count=1,
        heading_count=3,
        heading_max_depth=2,
        section_count=3,
        parsed=True,
        parse_duration_sec=0.5,
    )


class TestCache:
    def test_put_and_get(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        retrieved = tmp_cache.get(sample_file)
        assert retrieved is not None
        assert retrieved.file_name == sample_result.file_name
        assert retrieved.page_count == sample_result.page_count
        assert retrieved.word_count == sample_result.word_count

    def test_get_missing(self, tmp_cache, tmp_path):
        f = tmp_path / "nonexistent.pdf"
        f.write_bytes(b"data")
        assert tmp_cache.get(f) is None

    def test_stale_mtime(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        # Modify the file to change mtime
        sample_file.write_bytes(b"modified content that is different")
        result = tmp_cache.get(sample_file)
        assert result is None

    def test_stale_size(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        # Rewrite with different size but force same mtime won't work easily,
        # so just test that modifying the file invalidates (mtime changes too)
        original_mtime = sample_file.stat().st_mtime
        sample_file.write_bytes(b"x")
        os.utime(sample_file, (original_mtime, original_mtime))
        result = tmp_cache.get(sample_file)
        assert result is None  # size changed

    def test_clear(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        tmp_cache.clear()
        assert tmp_cache.get(sample_file) is None

    def test_invalidate(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        tmp_cache.invalidate(sample_file)
        assert tmp_cache.get(sample_file) is None

    def test_upsert(self, tmp_cache, sample_file, sample_result):
        tmp_cache.put(sample_file, sample_result)
        updated = sample_result.model_copy(update={"page_count": 99})
        tmp_cache.put(sample_file, updated)
        retrieved = tmp_cache.get(sample_file)
        assert retrieved is not None
        assert retrieved.page_count == 99

    def test_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "deep" / "nested" / "cache"
        Cache(cache_dir=cache_dir)
        assert cache_dir.exists()
        assert (cache_dir / "cache.db").exists()
