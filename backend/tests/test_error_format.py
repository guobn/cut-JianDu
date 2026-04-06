"""
错误响应格式统一化测试

验证所有 API 端点在错误情况下是否使用标准 ErrorResponse 格式：
{
    "status": "error",
    "error_code": "...",
    "error_message": "...",
    "suggested_solution": "..."
}
"""
import pytest
import inspect
from unittest.mock import patch, MagicMock


def is_standard_error_response(detail):
    """检查 detail 是否为标准错误响应格式"""
    if isinstance(detail, dict):
        required_keys = {"error_code", "error_message", "suggested_solution"}
        return required_keys.issubset(detail.keys())
    return False


def check_file_for_standard_format(file_path):
    """检查文件中的 HTTPException 是否使用标准格式"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有 raise HTTPException 语句
    issues = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        if 'raise HTTPException' in line:
            # 检查这一行及后续几行是否包含 detail
            context = ''.join(lines[i-1:min(i+5, len(lines))])

            if 'detail=' in context:
                # 检查是否使用标准格式
                if 'error_code' not in context:
                    # 检查是否是简单字符串
                    if 'detail=f"' in context or 'detail="' in context or "detail='" in context:
                        issues.append((i, line.strip()))

    return issues


# ============================================
# 静态分析测试
# ============================================

class TestStaticAnalysis:
    """静态分析测试 - 验证代码中所有 HTTPException 使用标准格式"""

    def test_cache_uses_standard_error_format(self):
        """测试 cache.py 所有错误响应使用标准格式"""
        from app.api import cache
        file_path = inspect.getfile(cache)
        issues = check_file_for_standard_format(file_path)
        assert len(issues) == 0, f"cache.py 中存在非标准错误格式：{issues}"

    def test_metadata_uses_standard_error_format(self):
        """测试 metadata.py 所有错误响应使用标准格式"""
        from app.api import metadata
        file_path = inspect.getfile(metadata)
        issues = check_file_for_standard_format(file_path)
        assert len(issues) == 0, f"metadata.py 中存在非标准错误格式：{issues}"

    def test_test_api_uses_standard_error_format(self):
        """测试 test.py 所有错误响应使用标准格式"""
        from app.api import test
        file_path = inspect.getfile(test)
        issues = check_file_for_standard_format(file_path)
        assert len(issues) == 0, f"test.py 中存在非标准错误格式：{issues}"


# ============================================
# 工具函数测试
# ============================================

class TestErrorResponseFormat:
    """测试错误响应格式辅助函数"""

    def test_error_response_helper(self):
        """测试 error_response 辅助函数是否生成标准格式"""
        from app.models.response import error_response

        result = error_response(
            error_code="TEST_ERROR",
            error_message="测试错误信息",
            suggested_solution="请重试"
        )

        assert result["status"] == "error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["error_message"] == "测试错误信息"
        assert result["suggested_solution"] == "请重试"

    def test_error_response_default_solution(self):
        """测试 error_response 默认 suggested_solution"""
        from app.models.response import error_response

        result = error_response(
            error_code="TEST_ERROR",
            error_message="测试错误信息"
        )

        assert result["suggested_solution"] == "请稍后重试"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
