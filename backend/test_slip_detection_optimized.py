"""测试优化后的单支检测效果"""
import sys
import cv2
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.segmentation_service import SegmentationService
from app.models.detection import DetectionParameters


def test_slip_detection(image_path: str):
    """测试单支检测"""
    print(f"\n{'='*60}")
    print(f"测试图像: {image_path}")
    print(f"{'='*60}\n")

    # 加载图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法加载图像: {image_path}")
        return

    h, w = image.shape[:2]
    print(f"图像尺寸: {w} x {h}")

    # 创建服务实例
    service = SegmentationService()

    # 设置检测参数
    params = DetectionParameters(
        min_width=10,   # 降低最小宽度
        min_height=30,  # 降低最小高度
        max_width=w,
        max_height=h,
    )

    # 执行单支检测
    print("\n开始单支检测...")
    try:
        result = service.detect_single_slips(image, params)

        print(f"\n✅ 检测完成!")
        print(f"检测到 {len(result.bounding_boxes)} 个单支")

        if result.bounding_boxes:
            print(f"\n单支详情:")
            for i, bbox in enumerate(result.bounding_boxes, 1):
                print(f"  {i}. 位置: ({bbox.x}, {bbox.y}), "
                      f"尺寸: {bbox.width}x{bbox.height}, "
                      f"置信度: {bbox.confidence:.3f}")

            # 可视化结果
            vis_image = image.copy()
            for bbox in result.bounding_boxes:
                cv2.rectangle(
                    vis_image,
                    (bbox.x, bbox.y),
                    (bbox.x + bbox.width, bbox.y + bbox.height),
                    (0, 255, 0),
                    2
                )
                # 添加置信度标签
                label = f"{bbox.confidence:.2f}"
                cv2.putText(
                    vis_image,
                    label,
                    (bbox.x, bbox.y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )

            # 保存结果
            output_path = Path(image_path).parent / f"{Path(image_path).stem}_detected.jpg"
            cv2.imwrite(str(output_path), vis_image)
            print(f"\n可视化结果已保存到: {output_path}")
        else:
            print("\n⚠️  未检测到任何单支")
            print("建议:")
            print("  1. 检查图像质量")
            print("  2. 确认模型文件路径正确")
            print("  3. 查看日志了解过滤详情")

    except Exception as e:
        print(f"\n❌ 检测失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("用法: python test_slip_detection_optimized.py <图像路径>")
        print("\n示例:")
        print("  python test_slip_detection_optimized.py test_image.jpg")
        sys.exit(1)

    test_slip_detection(image_path)
