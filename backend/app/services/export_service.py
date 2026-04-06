"""
导出服务 - MSJ + COCO 格式导出
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from app.config import settings
from app.services.supabase_service import (
    _auth_headers,
    _require_supabase_config,
    download_file_from_storage,
)


class ExportService:
    """MSJ 和 COCO 格式导出服务"""

    def __init__(self):
        self.base_url = settings.supabase_url.rstrip("/") if settings.supabase_url else ""
        self.headers = _auth_headers()
        self.result_dir = Path(settings.result_dir)

    def _query_image_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """查询图像组元数据"""
        url = f"{self.base_url}/rest/v1/image_groups"
        params = {"id": f"eq.{group_id}"}
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code >= 400 or not resp.json():
            return None
        return resp.json()[0]

    def _query_source_images(self, group_id: str) -> List[Dict[str, Any]]:
        """查询组内所有源图像"""
        url = f"{self.base_url}/rest/v1/source_images"
        params = {"group_id": f"eq.{group_id}"}
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code >= 400:
            return []
        return resp.json() or []

    def _query_slips(self, source_image_id: str) -> List[Dict[str, Any]]:
        """查询源图像的所有单支（slip）"""
        url = f"{self.base_url}/rest/v1/segments"
        params = {
            "source_image_id": f"eq.{source_image_id}",
            "segment_type": "eq.slip",
            "order": "segment_index.asc"
        }
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code >= 400:
            return []
        return resp.json() or []

    def _query_chars(self, slip_id: str) -> List[Dict[str, Any]]:
        """查询单支下的所有单字（char）"""
        url = f"{self.base_url}/rest/v1/segments"
        params = {
            "parent_segment_id": f"eq.{slip_id}",
            "segment_type": "eq.char",
            "order": "segment_index.asc"
        }
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code >= 400:
            return []
        return resp.json() or []

    def _query_slip_metadata(self, image_id: str) -> Optional[Dict[str, Any]]:
        """查询单支元数据"""
        url = f"{self.base_url}/rest/v1/slip_image_metadata"
        params = {"image_id": f"eq.{image_id}"}
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code >= 400 or not resp.json():
            return None
        return resp.json()[0]

    def _copy_segment_image(self, storage_path: str, dest_dir: Path) -> Optional[str]:
        """从 Supabase Storage 复制图片到本地输出目录"""
        if not storage_path:
            return None
        try:
            content = download_file_from_storage(storage_path)
            if content is None:
                return None
            filename = Path(storage_path).name
            dest_path = dest_dir / filename
            dest_path.write_bytes(content)
            return str(dest_path)
        except Exception:
            return None

    def _build_bbox(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """从数据库行构建 bbox"""
        return {
            "x": row.get("bbox_x", 0),
            "y": row.get("bbox_y", 0),
            "width": row.get("bbox_width", 0),
            "height": row.get("bbox_height", 0),
        }

    def _build_image_size(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """从数据库行构建 image_size"""
        return {
            "width": row.get("width", 0),
            "height": row.get("height", 0),
        }

    def _get_processing_config(self) -> Dict[str, Any]:
        """获取处理配置"""
        return {
            "slip_detection": {
                "model": settings.yolov11_finetuned_model_path or "yolov11-finetuned",
                "confidence_threshold": settings.yolov11_finetuned_conf_threshold,
                "nms_threshold": settings.sahi_nms_threshold,
                "sahi_slice_size": settings.sahi_slice_size,
                "sahi_overlap_ratio": settings.sahi_overlap_ratio,
            },
            "char_detection": {
                "model": settings.char_torchscript_model_path or "opencv",
                "confidence_threshold": settings.char_conf_threshold,
                "min_char_distance": 5,
            },
        }

    def export_group_as_msj(
        self,
        group_id: str,
        include_images: bool = False,
    ) -> Dict[str, Any]:
        """
        导出图像组为 Multimodal Structured JSON (MSJ) 格式。

        Returns:
            dict: 包含 export_url, record_count, file_size 的字典
        """
        _require_supabase_config()

        # 1. 查询图像组元数据
        group = self._query_image_group(group_id)
        if not group:
            raise ValueError(f"图像组不存在: {group_id}")

        # 2. 查询源图像
        source_images = self._query_source_images(group_id)

        # 3. 构建 MSJ 数据结构
        exported_at = datetime.now().isoformat() + "Z"
        total_slips = 0
        total_chars = 0

        source_images_data = []
        for img in source_images:
            img_id = img.get("id")
            slips = self._query_slips(img_id)

            slips_data = []
            for slip in slips:
                slip_id = slip.get("id")
                chars = self._query_chars(slip_id)
                total_slips += 1
                total_chars += len(chars)

                # 获取单支元数据
                slip_meta = self._query_slip_metadata(img_id)

                chars_data = []
                for char in chars:
                    char_storage_path = char.get("storage_path")
                    char_local_path = None
                    if include_images and char_storage_path:
                        img_dir = self.result_dir / "exports" / group_id / "images"
                        char_local_path = self._copy_segment_image(char_storage_path, img_dir)

                    chars_data.append({
                        "id": char.get("id"),
                        "segment_index": char.get("segment_index", 0),
                        "storage_path": char_local_path or char_storage_path,
                        "bbox": self._build_bbox(char),
                        "image_size": self._build_image_size(char),
                        "validated": char.get("validated", False),
                        "metadata": {
                            "title": char.get("title") or "",
                            "content_description": char.get("content_description") or "",
                        },
                    })

                slip_storage_path = slip.get("storage_path")
                slip_local_path = None
                if include_images and slip_storage_path:
                    img_dir = self.result_dir / "exports" / group_id / "images"
                    slip_local_path = self._copy_segment_image(slip_storage_path, img_dir)

                slips_data.append({
                    "id": slip_id,
                    "segment_index": slip.get("segment_index", 0),
                    "storage_path": slip_local_path or slip_storage_path,
                    "bbox": self._build_bbox(slip),
                    "image_size": self._build_image_size(slip),
                    "validated": slip.get("validated", False),
                    "metadata": {
                        "slip_number": slip_meta.get("slip_number", "") if slip_meta else "",
                        "material": slip_meta.get("material", "") if slip_meta else "",
                        "dimensions": slip_meta.get("dimensions", "") if slip_meta else "",
                        "preservation_state": slip_meta.get("preservation_state", "") if slip_meta else "",
                    },
                    "characters": chars_data,
                })

            source_images_data.append({
                "id": img_id,
                "original_filename": img.get("filename", ""),
                "storage_path": img.get("file_url", ""),
                "width": img.get("width", 0),
                "height": img.get("height", 0),
                "format": img.get("format", "UNKNOWN"),
                "slips": slips_data,
            })

        # 构建 dataset.json
        dataset = {
            "dataset_version": "1.0",
            "exported_at": exported_at,
            "image_group": {
                "id": group_id,
                "name": group.get("name", ""),
                "description": group.get("description", ""),
                "source_site": group.get("source_site", ""),
                "period": group.get("period", ""),
                "material": group.get("material", ""),
                "collection": group.get("collection", ""),
                "excavation_year": group.get("excavation_year", ""),
                "batch_no": group.get("batch_no", ""),
            },
            "source_images": source_images_data,
            "processing_config": self._get_processing_config(),
            "statistics": {
                "total_source_images": len(source_images),
                "total_slips": total_slips,
                "total_characters": total_chars,
            },
        }

        # 6. 保存 dataset.json
        output_dir = self.result_dir / "exports" / group_id
        output_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = output_dir / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        # 计算文件大小
        file_size = dataset_path.stat().st_size

        # 构建导出 URL（相对路径）
        export_url = f"/results/exports/{group_id}/dataset.json"

        # 8. 更新 export_records 表
        self._update_export_record(
            group_id=group_id,
            export_format="msj",
            status="completed",
            file_url=export_url,
            file_size_bytes=file_size,
            record_count={
                "groups": 1,
                "source_images": len(source_images),
                "slips": total_slips,
                "chars": total_chars,
            },
        )

        return {
            "export_url": export_url,
            "record_count": {
                "groups": 1,
                "source_images": len(source_images),
                "slips": total_slips,
                "chars": total_chars,
            },
            "file_size": file_size,
        }

    def export_group_as_coco(self, group_id: str) -> Dict[str, Any]:
        """
        导出图像组为 COCO 格式。

        Returns:
            dict: 包含 export_url, record_count, file_size 的字典
        """
        _require_supabase_config()

        # 1. 查询图像组元数据
        group = self._query_image_group(group_id)
        if not group:
            raise ValueError(f"图像组不存在: {group_id}")

        # 2. 查询源图像
        source_images = self._query_source_images(group_id)

        # 3. 构建 COCO 数据结构
        exported_at = datetime.now().isoformat() + "Z"
        total_slips = 0
        total_chars = 0

        images = []
        categories = [
            {"id": 0, "name": "slip", "supercategory": "bamboo_wood"},
            {"id": 1, "name": "char", "supercategory": "bamboo_wood"},
        ]
        annotations = []

        annotation_id = 1
        image_id_counter = 1

        for img in source_images:
            img_id = img.get("id")
            slips = self._query_slips(img_id)

            # COCO images 数组
            images.append({
                "id": image_id_counter,
                "file_name": img.get("filename", ""),
                "width": img.get("width", 0),
                "height": img.get("height", 0),
                "source_image_id": img_id,
            })

            current_image_id = image_id_counter
            image_id_counter += 1

            for slip in slips:
                slip_id = slip.get("id")
                chars = self._query_chars(slip_id)
                total_slips += 1

                slip_width = slip.get("width", 0)
                slip_height = slip.get("height", 0)
                bbox_x = slip.get("bbox_x", 0)
                bbox_y = slip.get("bbox_y", 0)
                area = slip_width * slip_height

                # COCO annotations for slip
                annotations.append({
                    "id": annotation_id,
                    "image_id": current_image_id,
                    "category_id": 0,  # slip
                    "bbox": [bbox_x, bbox_y, slip_width, slip_height],
                    "area": area,
                    "iscrowd": 0,
                    "segmentation": [],
                })
                annotation_id += 1

                # Characters under this slip
                for char in chars:
                    total_chars += 1
                    char_width = char.get("width", 0)
                    char_height = char.get("height", 0)
                    char_bbox_x = char.get("bbox_x", 0)
                    char_bbox_y = char.get("bbox_y", 0)
                    char_area = char_width * char_height

                    annotations.append({
                        "id": annotation_id,
                        "image_id": current_image_id,
                        "category_id": 1,  # char
                        "bbox": [char_bbox_x, char_bbox_y, char_width, char_height],
                        "area": char_area,
                        "iscrowd": 0,
                        "segmentation": [],
                    })
                    annotation_id += 1

        coco_dataset = {
            "info": {
                "description": group.get("description", ""),
                "version": "1.0",
                "year": datetime.now().year,
                "date_created": exported_at,
            },
            "licenses": [],
            "images": images,
            "categories": categories,
            "annotations": annotations,
        }

        # 保存 coco.json
        output_dir = self.result_dir / "exports" / group_id
        output_dir.mkdir(parents=True, exist_ok=True)
        coco_path = output_dir / "coco.json"
        with open(coco_path, "w", encoding="utf-8") as f:
            json.dump(coco_dataset, f, ensure_ascii=False, indent=2)

        # 计算文件大小
        file_size = coco_path.stat().st_size

        # 构建导出 URL
        export_url = f"/results/exports/{group_id}/coco.json"

        # 更新 export_records 表
        self._update_export_record(
            group_id=group_id,
            export_format="coco",
            status="completed",
            file_url=export_url,
            file_size_bytes=file_size,
            record_count={
                "groups": 1,
                "source_images": len(source_images),
                "slips": total_slips,
                "chars": total_chars,
            },
        )

        return {
            "export_url": export_url,
            "record_count": {
                "groups": 1,
                "source_images": len(source_images),
                "slips": total_slips,
                "chars": total_chars,
            },
            "file_size": file_size,
        }

    def _update_export_record(
        self,
        group_id: str,
        export_format: str,
        status: str,
        file_url: Optional[str],
        file_size_bytes: int,
        record_count: Dict[str, int],
    ) -> None:
        """更新 export_records 表"""
        url = f"{self.base_url}/rest/v1/export_records"
        headers = self.headers.copy()
        headers["Prefer"] = "return=representation"

        # 查找该组最新的 pending 状态的导出记录
        params = {
            "group_id": f"eq.{group_id}",
            "status": "eq.pending",
            "export_format": f"eq.{export_format}",
            "order": "created_at.desc",
            "limit": "1",
        }

        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code >= 400 or not resp.json():
            # 如果没有 pending 记录，尝试创建一个新记录
            row = {
                "group_id": group_id,
                "export_format": export_format,
                "status": status,
                "file_url": file_url,
                "file_size_bytes": file_size_bytes,
                "record_count": record_count,
                "completed_at": datetime.now().isoformat() + "Z",
            }
            requests.post(url, headers=headers, json=row)
            return

        export_record = resp.json()[0]
        record_id = export_record.get("id")

        # 更新记录
        update_url = f"{self.base_url}/rest/v1/export_records"
        update_params = {"id": f"eq.{record_id}"}
        update_data = {
            "status": status,
            "file_url": file_url,
            "file_size_bytes": file_size_bytes,
            "record_count": record_count,
            "completed_at": datetime.now().isoformat() + "Z",
        }
        requests.patch(update_url, headers=headers, params=update_params, json=update_data)
