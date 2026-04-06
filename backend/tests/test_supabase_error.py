"""Tests for Supabase error handling and rollback mechanisms"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import tempfile
import os

from app.services.supabase_service import (
    SupabaseError,
    SupabaseStorageError,
    SupabaseDatabaseError,
    SupabaseConfigError,
    upload_segment_to_storage,
    download_file_from_storage,
    delete_segment_from_storage,
    list_storage_objects,
    upsert_image_record,
    insert_segment_record,
    insert_slip_metadata,
    get_slip_metadata,
    build_segments_storage_key,
)
from app.models.detection import BoundingBox


class TestSupabaseErrorClasses:
    """测试 Supabase 异常类的定义和转换"""

    def test_supabase_error_basic(self):
        """测试基础异常类"""
        error = SupabaseError("Test error message", "TEST_ERROR")
        assert error.message == "Test error message"
        assert error.error_code == "TEST_ERROR"
        response = error.to_error_response()
        assert response["error_code"] == "TEST_ERROR"
        assert "Test error message" in response["error_message"]

    def test_supabase_storage_error(self):
        """测试 Storage 异常类"""
        error = SupabaseStorageError("Storage failed", "CUSTOM_STORAGE_ERROR")
        assert error.error_code == "CUSTOM_STORAGE_ERROR"
        response = error.to_error_response()
        assert "storage" in response.get("suggested_solution", "").lower() or \
               "bucket" in response.get("suggested_solution", "").lower()

    def test_supabase_database_error(self):
        """测试数据库异常类"""
        error = SupabaseDatabaseError("DB failed", "CUSTOM_DB_ERROR")
        assert error.error_code == "CUSTOM_DB_ERROR"
        response = error.to_error_response()
        assert "数据库" in response.get("suggested_solution", "") or \
               "表" in response.get("suggested_solution", "")

    def test_supabase_config_error(self):
        """测试配置异常类"""
        error = SupabaseConfigError("Config missing")
        assert error.error_code == "SUPABASE_CONFIG_ERROR"
        response = error.to_error_response()
        assert "SUPABASE_URL" in response.get("suggested_solution", "") or \
               "SUPABASE_SERVICE_KEY" in response.get("suggested_solution", "")


class TestUploadSegmentToStorage:
    """测试 upload_segment_to_storage 函数的错误处理和回滚机制"""

    @pytest.fixture
    def temp_file(self):
        """创建临时文件用于测试"""
        fd, path = tempfile.mkstemp(suffix='.png')
        os.write(fd, b'fake_image_data')
        os.close(fd)
        yield Path(path)
        # 清理：如果文件还存在则删除
        if Path(path).exists():
            os.remove(path)

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upload_success_first_attempt(self, mock_post, mock_settings, temp_file):
        """测试第一次尝试就上传成功"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 不应该抛出异常
        upload_segment_to_storage(temp_file, "user/slip/test_0001.png")

        # 验证只调用了一次（没有重试）
        assert mock_post.call_count == 1

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upload_success_after_retry(self, mock_post, mock_settings, temp_file):
        """测试重试后上传成功（网络异常场景）"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        # 前两次抛出网络异常，第三次成功
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200

        # 使用 side_effect 混合异常和成功响应
        mock_post.side_effect = [
            Exception("Network timeout"),  # 第一次异常
            Exception("Connection reset"),  # 第二次异常
            mock_response_success  # 第三次成功
        ]

        upload_segment_to_storage(temp_file, "user/slip/test_0001.png")

        # 验证调用了 3 次
        assert mock_post.call_count == 3

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upload_failure_triggers_rollback(self, mock_post, mock_settings, temp_file):
        """测试上传失败后触发回滚（删除临时文件）"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        # 所有尝试都失败
        mock_post.side_effect = Exception("Network error")

        # 验证文件在测试前存在
        assert temp_file.exists()

        # 应该抛出 SupabaseStorageError
        with pytest.raises(SupabaseStorageError) as exc_info:
            upload_segment_to_storage(temp_file, "user/slip/test_0001.png", enable_rollback=True)

        # 验证文件被回滚删除
        assert not temp_file.exists()
        assert "重试 3 次" in str(exc_info.value.message)

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upload_failure_rollback_disabled(self, mock_post, mock_settings, temp_file):
        """测试上传失败后回滚被禁用时文件保留"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_post.side_effect = Exception("Network error")

        # 禁用回滚
        with pytest.raises(SupabaseStorageError):
            upload_segment_to_storage(temp_file, "user/slip/test_0001.png", enable_rollback=False)

        # 文件应该保留
        assert temp_file.exists()

        # 清理
        if temp_file.exists():
            os.remove(temp_file)

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upload_http_400_error(self, mock_post, mock_settings, temp_file):
        """测试 HTTP 400 错误处理"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with pytest.raises(SupabaseStorageError) as exc_info:
            upload_segment_to_storage(temp_file, "user/slip/test_0001.png")

        assert "SUPABASE_STORAGE_UPLOAD_FAILED" in str(exc_info.value.error_code)

    @patch('app.services.supabase_service.settings')
    def test_upload_config_missing(self, mock_settings, temp_file):
        """测试配置缺失时的错误处理"""
        mock_settings.supabase_url = None
        mock_settings.supabase_service_key = None

        with pytest.raises(SupabaseConfigError):
            upload_segment_to_storage(temp_file, "user/slip/test_0001.png")


class TestDownloadFileFromStorage:
    """测试 download_file_from_storage 函数的错误处理"""

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_download_success_authenticated(self, mock_get, mock_settings):
        """测试通过 authenticated 端点成功下载"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'file_content'
        mock_get.return_value = mock_response

        result = download_file_from_storage("user/slip/test_0001.png")

        assert result == b'file_content'
        # 只调用 authenticated 端点
        assert mock_get.call_count == 1

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_download_success_fallback_to_public(self, mock_get, mock_settings):
        """测试 authenticated 失败后备降到 public 端点"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        # 第一次 authenticated 返回 404
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404

        # 第二次 public 返回 200
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.content = b'public_file_content'

        mock_get.side_effect = [mock_response_404, mock_response_200]

        result = download_file_from_storage("user/slip/test_0001.png")

        assert result == b'public_file_content'
        assert mock_get.call_count == 2

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_download_file_not_found(self, mock_get, mock_settings):
        """测试文件不存在返回 None"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        # 两个端点都返回 404
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        mock_get.return_value = mock_response_404

        result = download_file_from_storage("nonexistent.png")

        assert result is None

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_download_http_error(self, mock_get, mock_settings):
        """测试 HTTP 错误处理"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_get.return_value = mock_response

        with pytest.raises(SupabaseStorageError) as exc_info:
            download_file_from_storage("user/slip/test_0001.png")

        assert "SUPABASE_STORAGE_DOWNLOAD_FAILED" in str(exc_info.value.error_code)


class TestDeleteSegmentFromStorage:
    """测试 delete_segment_from_storage 函数的错误处理"""

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.delete')
    def test_delete_success(self, mock_delete, mock_settings):
        """测试成功删除"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 不应该抛出异常
        delete_segment_from_storage("user/slip/test_0001.png")

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.delete')
    def test_delete_404_is_ok(self, mock_delete, mock_settings):
        """测试删除不存在的文件视为成功"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_delete.return_value = mock_response

        # 404 不应该抛出异常
        delete_segment_from_storage("nonexistent.png")

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.delete')
    def test_delete_http_error(self, mock_delete, mock_settings):
        """测试 HTTP 错误处理"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_delete.return_value = mock_response

        with pytest.raises(SupabaseStorageError) as exc_info:
            delete_segment_from_storage("user/slip/test_0001.png")

        assert "SUPABASE_STORAGE_DELETE_FAILED" in str(exc_info.value.error_code)


class TestListStorageObjects:
    """测试 list_storage_objects 函数的错误处理"""

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_list_success(self, mock_post, mock_settings):
        """测试成功列出对象"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "file1.png"}, {"name": "file2.png"}]
        mock_post.return_value = mock_response

        result = list_storage_objects("user/slip/", limit=10)

        assert len(result) == 2
        assert result[0]["name"] == "file1.png"

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_list_empty_result(self, mock_post, mock_settings):
        """测试空结果"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = None
        mock_post.return_value = mock_response

        result = list_storage_objects("empty/prefix/")

        assert result == []

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_list_http_error(self, mock_post, mock_settings):
        """测试 HTTP 错误处理"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"
        mock_settings.supabase_segments_bucket = "segments"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_post.return_value = mock_response

        with pytest.raises(SupabaseStorageError) as exc_info:
            list_storage_objects("user/slip/")

        assert "SUPABASE_STORAGE_LIST_FAILED" in str(exc_info.value.error_code)


class TestDatabaseOperations:
    """测试数据库操作函数的错误处理"""

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upsert_image_record_success(self, mock_post, mock_settings):
        """测试成功 upsert 图像记录"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 不应该抛出异常
        upsert_image_record(
            image_id="test_id",
            image_path=Path("/path/to/image.jpg"),
            width=1000,
            height=800
        )

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_upsert_image_record_failure(self, mock_post, mock_settings):
        """测试 upsert 失败"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with pytest.raises(SupabaseDatabaseError) as exc_info:
            upsert_image_record(
                image_id="test_id",
                image_path=Path("/path/to/image.jpg"),
                width=1000,
                height=800
            )

        assert "SUPABASE_DATABASE_UPSERT_FAILED" in str(exc_info.value.error_code)

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_insert_segment_record_success(self, mock_post, mock_settings):
        """测试成功插入 segment 记录"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "segment_index": 0}]
        mock_post.return_value = mock_response

        bbox = BoundingBox(id="bbox_1", x=10, y=10, width=100, height=100, order=1)
        result = insert_segment_record(
            image_id="test_id",
            bbox=bbox,
            segment_index=0,
            segment_type="slip",
            storage_key="user/slip/test_0001.png",
            region_width=100,
            region_height=100
        )

        assert result["id"] == 1

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_insert_segment_record_empty_response(self, mock_post, mock_settings):
        """测试插入成功但返回空数据"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_post.return_value = mock_response

        bbox = BoundingBox(id="bbox_1", x=10, y=10, width=100, height=100, order=1)

        with pytest.raises(SupabaseDatabaseError) as exc_info:
            insert_segment_record(
                image_id="test_id",
                bbox=bbox,
                segment_index=0,
                segment_type="slip",
                storage_key="user/slip/test_0001.png",
                region_width=100,
                region_height=100
            )

        assert "返回数据为空" in str(exc_info.value.message)

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.post')
    def test_insert_slip_metadata_success(self, mock_post, mock_settings):
        """测试成功插入 slip 元数据"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "slip_number": "SLIP001"}]
        mock_post.return_value = mock_response

        result = insert_slip_metadata(
            image_id="test_id",
            slip_number="SLIP001",
            user_id="user123"
        )

        assert result["slip_number"] == "SLIP001"

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_get_slip_metadata_success(self, mock_get, mock_settings):
        """测试成功获取 slip 元数据"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "slip_number": "SLIP001"}]
        mock_get.return_value = mock_response

        result = get_slip_metadata("test_id")

        assert result is not None
        assert result["slip_number"] == "SLIP001"

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_get_slip_metadata_not_found(self, mock_get, mock_settings):
        """测试查询结果为空"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = get_slip_metadata("nonexistent_id")

        assert result is None

    @patch('app.services.supabase_service.settings')
    @patch('app.services.supabase_service.requests.get')
    def test_get_slip_metadata_http_error(self, mock_get, mock_settings):
        """测试查询 HTTP 错误"""
        mock_settings.supabase_url = "https://test.supabase.co"
        mock_settings.supabase_service_key = "test_key"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_get.return_value = mock_response

        with pytest.raises(SupabaseDatabaseError) as exc_info:
            get_slip_metadata("test_id")

        assert "SUPABASE_DATABASE_QUERY_FAILED" in str(exc_info.value.error_code)


class TestBuildSegmentsStorageKey:
    """测试 build_segments_storage_key 函数（纯函数，无需 mock）"""

    def test_build_key_slip_with_slip_number(self):
        """测试 slip 类型带 slip_number 的 key 生成"""
        key = build_segments_storage_key(
            image_id="img123",
            segment_type="slip",
            segment_index=5,
            slip_number="SLIP001",
            user_id="user456"
        )
        assert key == "user456/slip/SLIP001_slip_0005.png"

    def test_build_key_char_with_slip_number(self):
        """测试 char 类型带 slip_number 的 key 生成"""
        key = build_segments_storage_key(
            image_id="img123",
            segment_type="char",
            segment_index=3,
            slip_number="SLIP001",
            user_id="user456"
        )
        assert key == "user456/char/SLIP001_char_0003.png"

    def test_build_key_without_slip_number(self):
        """测试不带 slip_number 回退到 image_id"""
        key = build_segments_storage_key(
            image_id="img123",
            segment_type="slip",
            segment_index=0,
            user_id="anonymous"
        )
        assert "slip_img123_0000.png" in key

    def test_build_key_custom_format(self):
        """测试自定义输出格式"""
        key = build_segments_storage_key(
            image_id="img123",
            segment_type="slip",
            segment_index=1,
            output_format="jpg",
            slip_number="SLIP001",
            user_id="user456"
        )
        assert key.endswith(".jpg")
