from app.services.preprocess_service import list_images_for_task, set_group_status, update_image_angle
from app.services.rotation_service import estimate_skew_angle
from app.worker import celery_app


@celery_app.task(name="preprocess.detect_angles_batch", bind=True)
def detect_angles_batch(self, group_id: str):
    images = list_images_for_task(group_id)
    total = len(images)
    if total == 0:
        set_group_status(group_id, "angle_detected")
        return {"done": 0, "total": 0}

    for index, image in enumerate(images, start=1):
        angle, confidence = estimate_skew_angle(image["storage_path"])
        update_image_angle(image["id"], angle, confidence)
        self.update_state(
            state="PROGRESS",
            meta={"done": index, "total": total},
        )

    set_group_status(group_id, "angle_detected")
    return {"done": total, "total": total}
