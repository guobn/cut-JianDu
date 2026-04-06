"""诊断单支检测框过滤问题"""
import cv2
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# 模拟 _detect_single_slips_yolo 的过滤逻辑
def diagnose_box_filtering(image_path: str):
    """诊断框过滤过程"""
    from ultralytics import YOLO
    from app.config import settings

    # 加载图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法加载图像：{image_path}")
        return

    h, w = image.shape[:2]
    print(f"\n=== 图像信息 ===")
    print(f"路径：{image_path}")
    print(f"尺寸：{w} x {h}")

    # 加载模型
    model_path = getattr(settings, "yolov8_slip_model_path", None)
    if not model_path:
        print("模型路径未配置")
        return

    p = Path(model_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / model_path

    if not p.exists():
        print(f"模型文件不存在：{p}")
        return

    model = YOLO(str(p))
    print(f"模型已加载：{p}")

    # 获取配置
    conf_threshold = getattr(settings, "yolov8_slip_conf_threshold", 0.25)
    slip_class_id = getattr(settings, "yolov8_slip_class_id", 0)

    print(f"\n=== 配置参数 ===")
    print(f"conf_threshold: {conf_threshold}")
    print(f"slip_class_id: {slip_class_id}")

    # YOLO 预测
    print(f"\n=== YOLO 预测 ===")
    results = model.predict(source=image, conf=conf_threshold, verbose=False)

    if not results or len(results) == 0:
        print("无推理结果")
        return

    boxes_out = results[0].boxes
    if boxes_out is None or len(boxes_out) == 0:
        print("无检测框")
        return

    xyxy = boxes_out.xyxy.cpu().numpy()
    conf = boxes_out.conf.cpu().numpy()
    cls = boxes_out.cls.cpu().numpy()

    print(f"原始检测框数：{len(xyxy)}")

    # 统计各类别数量
    raw_by_class = {}
    for c in cls:
        c = int(c)
        raw_by_class[c] = raw_by_class.get(c, 0) + 1
    print(f"各类别分布：{raw_by_class}")

    # 确定使用类别
    use_class_id = slip_class_id
    if raw_by_class.get(slip_class_id, 0) == 0 and raw_by_class:
        use_class_id = max(raw_by_class, key=raw_by_class.get)
        print(f"类别{slip_class_id}无框，自动改用类别：{use_class_id}")

    # 过滤参数
    ar_min = 0.02
    ar_max = 0.6
    min_w = 50
    min_h = 200
    margin = 5

    print(f"\n=== 过滤条件 ===")
    print(f"长宽比范围：[{ar_min}, {ar_max}]")
    print(f"最小尺寸：{min_w} x {min_h}")
    print(f"边界 margin: {margin}")
    print(f"使用类别：{use_class_id}")

    # 逐个框诊断
    print(f"\n=== 框过滤详情 ===")
    kept_boxes = []
    for i in range(len(xyxy)):
        x1, y1, x2, y2 = xyxy[i]
        box_w = x2 - x1
        box_h = y2 - y1
        aspect_ratio = box_w / box_h if box_h > 0 else 0
        confidence = conf[i]
        box_cls = int(cls[i])

        reasons = []
        filtered = False

        # 类别过滤
        if box_cls != use_class_id:
            reasons.append(f"类别不匹配 ({box_cls} != {use_class_id})")
            filtered = True

        # 长宽比过滤
        if not (ar_min <= aspect_ratio <= ar_max):
            reasons.append(f"长宽比超出范围 ({aspect_ratio:.3f})")
            filtered = True

        # 尺寸过滤
        if box_w < min_w or box_h < min_h:
            reasons.append(f"尺寸太小 ({box_w:.1f}x{box_h:.1f})")
            filtered = True

        # 边界过滤
        if x1 < margin or y1 < margin or x2 > w - margin or y2 > h - margin:
            reasons.append(f"超出边界 (x1={x1:.1f}, y1={y1:.1f}, x2={x2:.1f}, y2={y2:.1f})")
            filtered = True

        status = "❌ 过滤" if filtered else "✅ 保留"
        print(f"框{i+1}: {status}")
        print(f"  坐标：({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
        print(f"  尺寸：{box_w:.1f} x {box_h:.1f}")
        print(f"  长宽比：{aspect_ratio:.4f}")
        print(f"  置信度：{confidence:.3f}")
        print(f"  类别：{box_cls}")
        if reasons:
            print(f"  过滤原因：{'; '.join(reasons)}")
        print()

        if not filtered:
            kept_boxes.append((x1, y1, box_w, box_h, confidence))

    print(f"\n=== 总结 ===")
    print(f"原始框数：{len(xyxy)}")
    print(f"保留框数：{len(kept_boxes)}")
    print(f"过滤率：{(len(xyxy) - len(kept_boxes)) / len(xyxy) * 100:.1f}%")

    if len(kept_boxes) == 0:
        print("\n⚠️  所有框都被过滤了！")
        print("建议:")
        print("  1. 调低 conf_threshold")
        print("  2. 放宽长宽比范围 (ar_min, ar_max)")
        print("  3. 降低最小尺寸要求 (min_w, min_h)")
        print("  4. 检查类别配置是否正确")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 默认使用测试图像
        image_path = "D:/project/gratuate/backend/tests/test_data/test_slip_image.jpg"

    diagnose_box_filtering(image_path)
