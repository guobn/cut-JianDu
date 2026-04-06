import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import aiofiles


class FileManager:
    """文件管理工具类"""
    
    @staticmethod
    def generate_unique_id(prefix: str = "") -> str:
        """
        生成唯一ID
        
        Args:
            prefix: ID前缀
            
        Returns:
            唯一ID字符串
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        
        if prefix:
            return f"{prefix}_{timestamp}_{unique_id}"
        return f"{timestamp}_{unique_id}"
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            扩展名（小写，包含点）
        """
        return Path(filename).suffix.lower()
    
    @staticmethod
    def is_valid_image_format(filename: str) -> bool:
        """
        检查是否为有效的图像格式
        
        Args:
            filename: 文件名
            
        Returns:
            是否有效
        """
        valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
        ext = FileManager.get_file_extension(filename)
        return ext in valid_extensions
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """
        获取安全的文件名（移除特殊字符）
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        # 保留扩展名
        path = Path(filename)
        name = path.stem
        ext = path.suffix
        
        # 移除或替换特殊字符
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
        
        return f"{safe_name}{ext}"
    
    @staticmethod
    def ensure_directory(directory: Path) -> None:
        """
        确保目录存在
        
        Args:
            directory: 目录路径
        """
        directory.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    async def save_upload_file(
        file_content: bytes,
        filename: str,
        save_dir: Path,
        generate_unique_name: bool = True
    ) -> Tuple[str, Path]:
        """
        保存上传的文件
        
        Args:
            file_content: 文件内容
            filename: 原始文件名
            save_dir: 保存目录
            generate_unique_name: 是否生成唯一文件名
            
        Returns:
            (文件名, 完整路径)
        """
        # 确保目录存在
        FileManager.ensure_directory(save_dir)
        
        # 生成文件名
        if generate_unique_name:
            ext = FileManager.get_file_extension(filename)
            unique_name = f"{FileManager.generate_unique_id('img')}{ext}"
        else:
            unique_name = FileManager.get_safe_filename(filename)
        
        # 保存文件
        file_path = save_dir / unique_name
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return unique_name, file_path
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        return file_path.stat().st_size
    
    @staticmethod
    def delete_file(file_path: Path) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def cleanup_temp_files(temp_dir: Path, max_age_hours: int = 24) -> int:
        """
        清理临时文件
        
        Args:
            temp_dir: 临时文件目录
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            删除的文件数量
        """
        if not temp_dir.exists():
            return 0
        
        deleted_count = 0
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    if FileManager.delete_file(file_path):
                        deleted_count += 1
        
        return deleted_count
