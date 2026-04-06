"""
图像组 API 测试用例
测试 groups.py 中的主要端点功能
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from uuid import uuid4
import json

from app.main import app
from app.models.groups import ImageGroupCreate, ImageGroupUpdate


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """模拟认证用户"""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "role": "user"
    }


@pytest.fixture
def override_auth():
    """覆盖认证依赖"""
    from app.api.groups import get_current_user

    def mock_get_current_user():
        return {
            "id": str(uuid4()),
            "email": "test@example.com",
            "role": "user"
        }

    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase_config():
    """模拟 Supabase 配置"""
    with patch('app.api.groups.settings') as mock_settings:
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_service_key"
        mock_settings.supabase_jwt_secret = "test_jwt_secret"
        yield mock_settings


@pytest.fixture
def mock_requests_post():
    """模拟 requests.post"""
    with patch('app.api.groups.requests.post') as mock_post:
        yield mock_post


@pytest.fixture
def mock_requests_get():
    """模拟 requests.get"""
    with patch('app.api.groups.requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_requests_patch():
    """模拟 requests.patch"""
    with patch('app.api.groups.requests.patch') as mock_patch:
        yield mock_patch


@pytest.fixture
def mock_requests_delete():
    """模拟 requests.delete"""
    with patch('app.api.groups.requests.delete') as mock_delete:
        yield mock_delete


@pytest.fixture
def sample_group_data():
    """样本组数据"""
    return {
        "name": "测试图像组",
        "description": "这是一个测试组",
        "source_site": "测试遗址",
        "period": "汉代",
        "material": "竹简",
        "collection": "测试收藏",
        "excavation_year": "2020",
        "batch_no": "BATCH-001"
    }


@pytest.fixture
def sample_group_response():
    """样本组响应数据"""
    group_id = str(uuid4())
    user_id = str(uuid4())
    return {
        "id": group_id,
        "user_id": user_id,
        "name": "测试图像组",
        "description": "这是一个测试组",
        "source_site": "测试遗址",
        "period": "汉代",
        "material": "竹简",
        "collection": "测试收藏",
        "excavation_year": "2020",
        "batch_no": "BATCH-001",
        "status": "created",
        "total_images": 0,
        "processed_images": 0,
        "thumbnail_url": None,
        "export_url": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


# ============================================
# 测试用例 1: 创建组 (POST /api/groups)
# ============================================
class TestCreateGroup:
    """测试创建图像组"""

    def test_create_group_success(
        self, client, mock_supabase_config, mock_requests_post, sample_group_data, sample_group_response, override_auth
    ):
        """成功创建图像组"""
        # 模拟 POST 请求返回
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = [sample_group_response]
        mock_requests_post.return_value = mock_response

        response = client.post("/api/groups", json=sample_group_data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == sample_group_data["name"]
        assert result["status"] == "created"
        assert "id" in result

    def test_create_group_with_minimal_data(self, client, mock_supabase_config, mock_requests_post, override_auth):
        """使用最小数据集创建图像组"""
        minimal_data = {"name": "最小组"}

        # 模拟 POST 请求返回
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = [{
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "最小组",
            "description": None,
            "source_site": None,
            "period": None,
            "material": None,
            "collection": None,
            "excavation_year": None,
            "batch_no": None,
            "status": "created",
            "total_images": 0,
            "processed_images": 0,
            "thumbnail_url": None,
            "export_url": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }]
        mock_requests_post.return_value = mock_response

        response = client.post("/api/groups", json=minimal_data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "最小组"
        assert result["status"] == "created"


# ============================================
# 测试用例 2: 获取组列表 (GET /api/groups)
# ============================================
class TestListGroups:
    """测试获取图像组列表"""

    def test_list_groups_success(
        self, client, mock_supabase_config, mock_requests_get, sample_group_response, override_auth
    ):
        """成功获取图像组列表"""
        # 模拟 GET 请求返回
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_response

        response = client.get("/api/groups")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == sample_group_response["name"]

    def test_list_groups_empty(self, client, mock_supabase_config, mock_requests_get, override_auth):
        """组列表为空时返回空数组"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests_get.return_value = mock_response

        response = client.get("/api/groups")

        assert response.status_code == 200
        result = response.json()
        assert result == []


# ============================================
# 测试用例 3: 获取单个组 (GET /api/groups/{id})
# ============================================
class TestGetGroup:
    """测试获取单个图像组"""

    def test_get_group_success(
        self, client, mock_supabase_config, mock_requests_get, sample_group_response, override_auth
    ):
        """成功获取单个图像组"""
        group_id = sample_group_response["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_response

        response = client.get(f"/api/groups/{group_id}")

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == group_id
        assert result["name"] == sample_group_response["name"]

    def test_get_group_not_found(
        self, client, mock_supabase_config, mock_requests_get, override_auth
    ):
        """组不存在时返回 404"""
        group_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests_get.return_value = mock_response

        response = client.get(f"/api/groups/{group_id}")

        assert response.status_code == 404


# ============================================
# 测试用例 4: 更新组 (PUT /api/groups/{id})
# ============================================
class TestUpdateGroup:
    """测试更新图像组"""

    def test_update_group_success(
        self, client, mock_supabase_config, mock_requests_patch, mock_requests_get,
        sample_group_response, override_auth
    ):
        """成功更新图像组"""
        group_id = sample_group_response["id"]
        update_data = {"name": "更新后的名称", "description": "更新后的描述"}

        # 模拟 PATCH 请求返回
        updated_response = sample_group_response.copy()
        updated_response["name"] = update_data["name"]
        updated_response["description"] = update_data["description"]

        mock_patch_response = MagicMock()
        mock_patch_response.status_code = 200
        mock_patch_response.json.return_value = [updated_response]
        mock_requests_patch.return_value = mock_patch_response

        # 模拟 GET 请求（用于验证）
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_get_response

        response = client.put(f"/api/groups/{group_id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == update_data["name"]

    def test_update_group_no_changes(
        self, client, mock_supabase_config, mock_requests_get, sample_group_response, override_auth
    ):
        """没有实际更新内容时直接返回当前状态"""
        group_id = sample_group_response["id"]
        update_data = {}  # 空更新

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_response

        response = client.put(f"/api/groups/{group_id}", json=update_data)

        assert response.status_code == 200


# ============================================
# 测试用例 5: 删除组 (DELETE /api/groups/{id})
# ============================================
class TestDeleteGroup:
    """测试删除图像组"""

    def test_delete_group_success(
        self, client, mock_supabase_config, mock_requests_delete, sample_group_response, override_auth
    ):
        """成功删除图像组"""
        group_id = sample_group_response["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests_delete.return_value = mock_response

        response = client.delete(f"/api/groups/{group_id}")

        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Group deleted"
        assert result["group_id"] == group_id

    def test_delete_group_error(
        self, client, mock_supabase_config, mock_requests_delete, override_auth
    ):
        """删除失败时返回错误"""
        group_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Delete failed"
        mock_requests_delete.return_value = mock_response

        response = client.delete(f"/api/groups/{group_id}")

        assert response.status_code == 400


# ============================================
# 测试用例 6: 获取处理进度 (GET /api/groups/{id}/progress)
# ============================================
class TestGetProgress:
    """测试获取处理进度"""

    def test_get_progress_success(
        self, client, mock_supabase_config, mock_requests_get, sample_group_response, override_auth
    ):
        """成功获取处理进度"""
        group_id = sample_group_response["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_response

        response = client.get(f"/api/groups/{group_id}/progress")

        assert response.status_code == 200
        result = response.json()
        assert "total" in result
        assert "completed" in result
        assert "progress" in result
        assert "status" in result

    def test_get_progress_not_found(
        self, client, mock_supabase_config, mock_requests_get, override_auth
    ):
        """组不存在时返回 404"""
        group_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests_get.return_value = mock_response

        response = client.get(f"/api/groups/{group_id}/progress")

        assert response.status_code == 404


# ============================================
# 测试用例 7: 批量预处理 (POST /api/groups/{id}/preprocess)
# ============================================
class TestPreprocessGroup:
    """测试批量预处理"""

    def test_preprocess_group_success(
        self, client, mock_supabase_config, mock_requests_get, mock_requests_patch,
        sample_group_response, override_auth
    ):
        """成功触发批量预处理"""
        group_id = sample_group_response["id"]
        config_data = {"target_long_side": 2000, "grayscale": True}

        # 模拟验证请求
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [sample_group_response]
        mock_requests_get.return_value = mock_get_response

        # 模拟状态更新请求
        mock_patch_response = MagicMock()
        mock_patch_response.status_code = 200
        mock_requests_patch.return_value = mock_patch_response

        response = client.post(f"/api/groups/{group_id}/preprocess", json=config_data)

        assert response.status_code == 200
        result = response.json()
        assert "task_id" in result
        assert result["group_id"] == group_id
        assert result["status"] == "processing"

    def test_preprocess_group_not_found(
        self, client, mock_supabase_config, mock_requests_get, override_auth
    ):
        """组不存在时返回 404"""
        group_id = str(uuid4())
        config_data = {"target_long_side": 2000}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests_get.return_value = mock_response

        response = client.post(f"/api/groups/{group_id}/preprocess", json=config_data)

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
