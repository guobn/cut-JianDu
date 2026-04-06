from pathlib import Path
from typing import Tuple, List, Optional
from PIL import Image
from datetime import datetime
import io
import logging

from app.models.image import ImageInfo, ImageUploadResponse, ImageListItem
from app.utils.image_utils import ImageProcessor
from app.utils.file_utils import FileManager
from app.config import settings


class ImageService:
    """图像服务"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.upload_dir = Path(settings.upload_dir)
    
    async def save_image(
        self,
        image_id: str,
        filename: str,
        content: bytes,
        content_type: str
    ) -> ImageUploadResponse:
        """
        保存上传的图像并提取元数据
        
        Args:
            image_id: 图像ID
            filename: 文件名
            content: 文件内容
            content_type: 内容类型
            
        Returns:
            图像上传响应
        """
        # 保存文件
        saved_filename, file_path = await FileManager.save_upload_file(
            content,
            filename,
            self.upload_dir,
            generate_unique_name=False
        )
        
        # 使用image_id作为文件名
        ext = FileManager.get_file_extension(filename)
        new_filename = f"{image_id}{ext}"
        new_path = self.upload_dir / new_filename
        
        # 重命名文件
        file_path.rename(new_path)
        
        # 提取图像元数据
        image = self.image_processor.load_image(new_path)
        image_info = self.image_processor.get_image_info(image)
        
        # 获取文件大小
        file_size = FileManager.get_file_size(new_path)
        
        # 确定格式
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.tiff': 'TIFF',
            '.tif': 'TIFF',
            '.bmp': 'BMP'
        }
        image_format = format_map.get(ext, 'UNKNOWN')
        
        # 创建响应
        response = ImageUploadResponse(
            image_id=image_id,
            filename=new_filename,
            width=image_info['width'],
            height=image_info['height'],
            format=image_format,
            file_size=file_size,
            upload_time=datetime.now()
        )
        
        return response
    
    def get_image_path(self, image_id: str) -> Path:
        """
        获取图像文件路径
        
        Args:
            image_id: 图像ID
            
        Returns:
            文件路径
        """
        # 查找匹配的文件
        for ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
            file_path = self.upload_dir / f"{image_id}{ext}"
            if file_path.exists():
                return file_path
        
        raise FileNotFoundError(f"图像文件不存在: {image_id}")
    
    def load_image(self, image_id: str):
        """
        加载图像（仅从本地 upload_dir 查找）
        
        Args:
            image_id: 图像ID
            
        Returns:
            numpy数组格式的图像
        """
        file_path = self.get_image_path(image_id)
        return self.image_processor.load_image(file_path)

    def load_image_with_supabase_fallback(self, image_id: str, user_id: Optional[str] = None):
        """
        加载图像：先尝试本地，若不存在且提供 user_id 则从 Supabase Storage 下载后缓存到本地再加载。
        原图在 Storage 中的路径约定：{user_id}/img/{image_id}.{ext}
        """
        try:
            return self.load_image(image_id)
        except FileNotFoundError:
            pass
        if not user_id:
            raise FileNotFoundError(f"图像文件不存在: {image_id}（本地无缓存且未提供 user_id 无法从 Supabase 拉取）")
        exts = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
        try:
            from app.services.supabase_service import download_file_from_storage
        except Exception:
            raise FileNotFoundError(f"图像文件不存在: {image_id}")
        log = logging.getLogger(__name__)
        for ext in exts:
            storage_key = f"{user_id}/img/{image_id}{ext}"
            try:
                content = download_file_from_storage(storage_key)
            except Exception as e:
                log.debug("从 Supabase 拉取 %s 失败: %s", storage_key, e)
                continue
            if content is None:
                continue
            local_path = self.upload_dir / f"{image_id}{ext}"
            local_path.write_bytes(content)
            log.info("已从 Supabase 拉取并缓存原图: %s -> %s", storage_key, local_path)
            return self.load_image(image_id)
        raise FileNotFoundError(f"图像文件不存在: {image_id}（本地与 Supabase 均未找到）")
    
    async def list_images(self, limit: int = 50) -> List[ImageListItem]:
        """
        获取已上传的图像列表
        
        Args:
            limit: 返回的最大数量
            
        Returns:
            图像列表
        """
        images = []
        
        # 遍历上传目录
        for file_path in self.upload_dir.glob("img_*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']:
                try:
                    # 提取 image_id
                    image_id = file_path.stem
                    
                    # 加载图像获取元数据
                    image = self.image_processor.load_image(file_path)
                    image_info = self.image_processor.get_image_info(image)
                    
                    # 获取文件信息
                    file_size = FileManager.get_file_size(file_path)
                    file_stat = file_path.stat()
                    upload_time = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    # 确定格式
                    format_map = {
                        '.jpg': 'JPEG',
                        '.jpeg': 'JPEG',
                        '.png': 'PNG',
                        '.tiff': 'TIFF',
                        '.tif': 'TIFF',
                        '.bmp': 'BMP'
                    }
                    image_format = format_map.get(file_path.suffix.lower(), 'UNKNOWN')
                    
                    images.append(ImageListItem(
                        image_id=image_id,
                        filename=file_path.name,
                        width=image_info['width'],
                        height=image_info['height'],
                        format=image_format,
                        file_size=file_size,
                        upload_time=upload_time
                    ))
                except Exception as e:
                    # 跳过无法读取的文件
                    print(f"跳过文件 {file_path}: {e}")
                    continue
        
        # 按上传时间倒序排序
        images.sort(key=lambda x: x.upload_time, reverse=True)
        
        # 限制返回数量
        return images[:limit]
