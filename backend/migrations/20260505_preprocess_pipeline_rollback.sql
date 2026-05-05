ALTER TABLE IF EXISTS public.source_images
  DROP COLUMN IF EXISTS preprocess_skipped;

ALTER TABLE IF EXISTS public.source_images
  DROP COLUMN IF EXISTS rotation_confidence;

ALTER TABLE IF EXISTS public.source_images
  DROP COLUMN IF EXISTS rotation_angle;

ALTER TABLE IF EXISTS public.image_groups
  DROP CONSTRAINT IF EXISTS image_groups_preprocess_status_check;

ALTER TABLE IF EXISTS public.image_groups
  DROP COLUMN IF EXISTS preprocess_params;

ALTER TABLE IF EXISTS public.image_groups
  DROP COLUMN IF EXISTS preprocess_status;

ALTER TABLE IF EXISTS public.image_groups
  DROP CONSTRAINT IF EXISTS image_groups_kind_check;

ALTER TABLE IF EXISTS public.image_groups
  DROP COLUMN IF EXISTS kind;
