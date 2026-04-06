-- 第一段：数据库重构迁移脚本
-- 执行位置：Supabase SQL Editor
-- 执行顺序：按照本文件从上到下执行

-- ============================================
-- 0. 创建 source_images 表（如果不存在）
-- ============================================
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
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_images_user_id ON source_images(user_id);

-- ============================================
-- 1. 创建 image_groups 表（图像组主表）
-- ============================================
CREATE TABLE IF NOT EXISTS image_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  source_site TEXT,          -- 出土地点
  period TEXT,               -- 时代断代
  material TEXT,             -- 材质（竹/木）
  collection TEXT,           -- 收藏机构
  excavation_year TEXT,      -- 发掘年份
  batch_no TEXT,             -- 批次编号
  status TEXT DEFAULT 'created' CHECK (status IN ('created','preprocessing','segmenting','completed','exported')),
  total_images INT DEFAULT 0,
  processed_images INT DEFAULT 0,
  thumbnail_url TEXT,
  export_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_image_groups_user_id ON image_groups(user_id);
CREATE INDEX idx_image_groups_status ON image_groups(status);

-- ============================================
-- 2. 修改 source_images 表，添加 group_id 外键
-- ============================================
ALTER TABLE source_images
ADD COLUMN IF NOT EXISTS group_id UUID REFERENCES image_groups(id) ON DELETE SET NULL;

ALTER TABLE source_images
ADD COLUMN IF NOT EXISTS group_order INT DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_source_images_group_id ON source_images(group_id);

-- ============================================
-- 3. 创建 processing_cache 表（关键缓存层）
-- ============================================
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

CREATE INDEX idx_processing_cache_source ON processing_cache(source_image_id);
CREATE INDEX idx_processing_cache_type ON processing_cache(cache_type);
CREATE INDEX idx_processing_cache_expires ON processing_cache(expires_at);

-- ============================================
-- 4. 创建 export_records 表
-- ============================================
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

CREATE INDEX idx_export_records_group_id ON export_records(group_id);
CREATE INDEX idx_export_records_user_id ON export_records(user_id);
CREATE INDEX idx_export_records_status ON export_records(status);

-- ============================================
-- 5. 为 image_groups 表启用 RLS（行级安全）
-- ============================================
ALTER TABLE image_groups ENABLE ROW LEVEL SECURITY;

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

-- ============================================
-- 6. 为 processing_cache 表启用 RLS
-- ============================================
ALTER TABLE processing_cache ENABLE ROW LEVEL SECURITY;

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

-- ============================================
-- 7. 为 export_records 表启用 RLS
-- ============================================
ALTER TABLE export_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own export records"
  ON export_records FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create export records"
  ON export_records FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ============================================
-- 迁移完成
-- ============================================
-- 验证步骤：
-- 1. 在 Supabase Studio 的 Table Editor 中查看新表
-- 2. 检查 source_images 表是否有 group_id 和 group_order 列
-- 3. 检查索引是否创建成功
