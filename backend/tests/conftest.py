import os
import pytest

# Test ortami icin zorunlu env degiskenlerini set et
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "eyJ.test.service.key")
os.environ.setdefault("SUPABASE_ANON_KEY", "eyJ.test.anon.key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ELASTICSEARCH_URL", "http://localhost:9200")
