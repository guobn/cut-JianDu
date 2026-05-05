ALTER TABLE IF EXISTS public.image_groups
  ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'regular';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'image_groups_kind_check'
  ) THEN
    ALTER TABLE public.image_groups
      ADD CONSTRAINT image_groups_kind_check
      CHECK (kind IN ('preprocessing', 'regular'));
  END IF;
END $$;

ALTER TABLE IF EXISTS public.image_groups
  ADD COLUMN IF NOT EXISTS preprocess_status TEXT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'image_groups_preprocess_status_check'
  ) THEN
    ALTER TABLE public.image_groups
      ADD CONSTRAINT image_groups_preprocess_status_check
      CHECK (
        preprocess_status IS NULL OR
        preprocess_status IN ('draft', 'angle_detected', 'rotated', 'normalized')
      );
  END IF;
END $$;

ALTER TABLE IF EXISTS public.image_groups
  ADD COLUMN IF NOT EXISTS preprocess_params JSONB NULL;

ALTER TABLE IF EXISTS public.source_images
  ADD COLUMN IF NOT EXISTS rotation_angle DOUBLE PRECISION NULL;

ALTER TABLE IF EXISTS public.source_images
  ADD COLUMN IF NOT EXISTS rotation_confidence DOUBLE PRECISION NULL;

ALTER TABLE IF EXISTS public.source_images
  ADD COLUMN IF NOT EXISTS preprocess_skipped BOOLEAN NOT NULL DEFAULT FALSE;
