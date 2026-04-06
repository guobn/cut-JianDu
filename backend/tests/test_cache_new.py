"""
Cache API 端点测试
测试 cache.py 中的三个端点：
- POST /api/cache/save
- GET /api/cache/{source_image_id}/{cache_type}
- DELETE /api/cache/{source_image_id}
"""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
from app.api.cache import router
from fastapi import Depends
from app.core.auth import get_current_user


# 创建测试用的 FastAPI 应用
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)


def override_get_current_user():
    """覆盖认证依赖，返回测试用户"""
    return {"id": str(uuid4()), "email": "test@example.com", "role": "user"}


# 应用认证覆盖
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_cache_data():
    """样本缓存数据"""
    return {
        "source_image_id": str(uuid4()),
        "cache_type": "thumbnail",
        "cache_url": "https://example.com/cache/image1.png",
        "cache_meta": {"width": 800, "height": 600}
    }


class TestSaveCache:
    """测试 POST /api/cache/save 端点"""

    def test_save_cache_success(self, client, sample_cache_data):
        """测试成功保存缓存"""
        with patch('app.api.cache.requests.post') as mock_post:
            # Mock Supabase 响应
            mock_response = MagicMock()
            mock_response.status_code = 201
            saved_id = str(uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            mock_response.json.return_value = [{
                "id": saved_id,
                "source_image_id": sample_cache_data["source_image_id"],
                "cache_type": sample_cache_data["cache_type"],
                "cache_url": sample_cache_data["cache_url"],
                "cache_meta": sample_cache_data["cache_meta"],
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }]
            mock_post.return_value = mock_response

            response = client.post("/api/cache/save", json=sample_cache_data)

            assert response.status_code == 200
            data = response.json()
            assert data["source_image_id"] == sample_cache_data["source_image_id"]
            assert data["cache_type"] == sample_cache_data["cache_type"]
            assert data["cache_url"] == sample_cache_data["cache_url"]

    def test_save_cache_supabase_error(self, client, sample_cache_data):
        """测试 Supabase 错误处理"""
        with patch('app.api.cache.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            response = client.post("/api/cache/save", json=sample_cache_data)

            assert response.status_code == 500
            assert "保存缓存记录失败" in response.json()["detail"]

    def test_save_cache_missing_fields(self, client):
        """测试缺少必填字段"""
        incomplete_data = {
            "cache_type": "thumbnail",
            "cache_url": "https://example.com/cache/image1.png"
            # 缺少 source_image_id
        }

        response = client.post("/api/cache/save", json=incomplete_data)

        assert response.status_code == 422  # Validation error


class TestGetCache:
    """测试 GET /api/cache/{source_image_id}/{cache_type} 端点"""

    def test_get_cache_success(self, client, sample_cache_data):
        """测试成功获取缓存"""
        source_image_id = sample_cache_data["source_image_id"]
        cache_type = sample_cache_data["cache_type"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        with patch('app.api.cache.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{
                "id": str(uuid4()),
                "source_image_id": source_image_id,
                "cache_type": cache_type,
                "cache_url": sample_cache_data["cache_url"],
                "cache_meta": sample_cache_data["cache_meta"],
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }]
            mock_get.return_value = mock_response

            response = client.get(f"/api/cache/{source_image_id}/{cache_type}")

            assert response.status_code == 200
            data = response.json()
            assert data["source_image_id"] == source_image_id
            assert data["cache_type"] == cache_type

    def test_get_cache_not_found(self, client):
        """测试缓存未找到"""
        source_image_id = str(uuid4())
        cache_type = "thumbnail"

        with patch('app.api.cache.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            response = client.get(f"/api/cache/{source_image_id}/{cache_type}")

            assert response.status_code == 404
            assert "Cache not found" in response.json()["detail"]

    def test_get_cache_expired(self, client, sample_cache_data):
        """测试缓存已过期"""
        source_image_id = sample_cache_data["source_image_id"]
        cache_type = sample_cache_data["cache_type"]
        # 设置过期时间为过去
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)

        with patch('app.api.cache.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{
                "id": str(uuid4()),
                "source_image_id": source_image_id,
                "cache_type": cache_type,
                "cache_url": sample_cache_data["cache_url"],
                "cache_meta": {},
                "expires_at": expired_at.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }]
            mock_get.return_value = mock_response

            response = client.get(f"/api/cache/{source_image_id}/{cache_type}")

            assert response.status_code == 404
            assert "Cache expired" in response.json()["detail"]

    def test_get_cache_supabase_error(self, client):
        """测试 Supabase 查询错误"""
        source_image_id = str(uuid4())
        cache_type = "thumbnail"

        with patch('app.api.cache.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            response = client.get(f"/api/cache/{source_image_id}/{cache_type}")

            assert response.status_code == 500
            assert "查询缓存失败" in response.json()["detail"]


class TestDeleteCache:
    """测试 DELETE /api/cache/{source_image_id} 端点"""

    def test_delete_cache_success(self, client):
        """测试成功删除缓存"""
        source_image_id = str(uuid4())

        with patch('app.api.cache.requests.delete') as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/cache/{source_image_id}")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert source_image_id in data["message"]

    def test_delete_cache_no_content(self, client):
        """测试删除不存在的缓存（返回 404 但应正常处理）"""
        source_image_id = str(uuid4())

        with patch('app.api.cache.requests.delete') as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/cache/{source_image_id}")

            # 根据实现，404 不应抛出错误
            assert response.status_code == 200

    def test_delete_cache_supabase_error(self, client):
        """测试 Supabase 删除错误"""
        source_image_id = str(uuid4())

        with patch('app.api.cache.requests.delete') as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/cache/{source_image_id}")

            assert response.status_code == 500
            assert "删除缓存失败" in response.json()["detail"]
