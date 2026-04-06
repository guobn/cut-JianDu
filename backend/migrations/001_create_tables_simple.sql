-- 简化版迁移脚本 - 直接在 Supabase SQL Editor 执行

-- 1. 创建 source_images 表
CREATE TABLE IF NOT EXISTS source_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  original_filename TEXT,
  file_size BIGINT,
  width INT,
  height INT,
  format TEXT,
  preprocessed_url TEXT,
  group_id UUID,
  group_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. 创建 image_groups 表
CREATE TABLE IF NOT EXISTS image_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  source_site TEXT,
  period TEXT,
  material TEXT,
  collection TEXT,
  excavation_year TEXT,
  batch_no TEXT,
  status TEXT DEFAULT 'created' CHECK (status IN ('created','preprocessing','segmenting','completed','exported')),
  total_images INT DEFAULT 0,
  processed_images INT DEFAULT 0,
  thumbnail_url TEXT,
  export_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. 添加外键约束
ALTER TABLE source_images
ADD CONSTRAINT fk_source_images_group_id
FOREIGN KEY (group_id) REFERENCES image_groups(id) ON DELETE SET NULL;

-- 4. 创建 processing_cache 表
CREATE TABLE IF NOT EXISTS processing_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_image_id UUID NOT NULL REFERENCES source_images(id) ON DELETE CASCADE,
  cache_type TEXT NOT NULL CHECK (cache_type IN ('thumbnail','normalized','slip_detect','char_detect')),
  cache_url TEXT NOT NULL,
  cache_meta JSONB DEFAULT '{}',
  expires_at TIMESTAMPTZ DEFAULT (now() + interval '7 days'),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(source_image_id, cache_type)
);

-- 5. 创建 export_records 表
CREATE TABLE IF NOT EXISTS export_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES image_groups(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  export_format TEXT DEFAULT 'multimodal_json',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
  file_url TEXT,
  file_size_bytes BIGINT,
  record_count JSONB DEFAULT '{"groups":0,"slips":0,"chars":0}',
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- 6. 创建索引
CREATE INDEX IF NOT EXISTS idx_source_images_user_id ON source_images(user_id);
CREATE INDEX IF NOT EXISTS idx_source_images_group_id ON source_images(group_id);
CREATE INDEX IF NOT EXISTS idx_image_groups_user_id ON image_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_image_groups_status ON image_groups(status);
CREATE INDEX IF NOT EXISTS idx_processing_cache_source ON processing_cache(source_image_id);
CREATE INDEX IF NOT EXISTS idx_processing_cache_type ON processing_cache(cache_type);
CREATE INDEX IF NOT EXISTS idx_processing_cache_expires ON processing_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_export_records_group_id ON export_records(group_id);
CREATE INDEX IF NOT EXISTS idx_export_records_user_id ON export_records(user_id);
CREATE INDEX IF NOT EXISTS idx_export_records_status ON export_records(status);

-- 7. 启用 RLS
ALTER TABLE image_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE export_records ENABLE ROW LEVEL SECURITY;

-- 8. RLS 策略 - image_groups
CREATE POLICY "Users can view their own image groups"
  ON image_groups FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create image groups"
  ON image_groups FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own image groups"
  ON image_groups FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own image groups"
  ON image_groups FOR DELETE
  USING (auth.uid() = user_id);

-- 9. RLS 策略 - processing_cache
CREATE POLICY "Users can view cache for their images"
  ON processing_cache FOR SELECT
  USING (
    source_image_id IN (
      SELECT id FROM source_images
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create cache for their images"
  ON processing_cache FOR INSERT
  WITH CHECK (
    source_image_id IN (
      SELECT id FROM source_images
      WHERE user_id = auth.uid()
    )
  );

-- 10. RLS 策略 - export_records
CREATE POLICY "Users can view their own export records"
  ON export_records FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create export records"
  ON export_records FOR INSERT
  WITH CHECK (auth.uid() = user_id);
