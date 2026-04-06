/**
 * 图像组和缓存相关的 TypeScript 类型定义
 */

// ============================================
// 图像组相关类型
// ============================================

export interface ImageGroup {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  source_site?: string;
  period?: string;
  material?: string;
  collection?: string;
  excavation_year?: string;
  batch_no?: string;
  status: 'created' | 'preprocessing' | 'segmenting' | 'completed' | 'exported';
  total_images: number;
  processed_images: number;
  thumbnail_url?: string;
  export_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ImageGroupCreate {
  name: string;
  description?: string;
  source_site?: string;
  period?: string;
  material?: string;
  collection?: string;
  excavation_year?: string;
  batch_no?: string;
}

export interface ImageGroupUpdate {
  name?: string;
  description?: string;
  source_site?: string;
  period?: string;
  material?: string;
  collection?: string;
  excavation_year?: string;
  batch_no?: string;
  status?: string;
}

// ============================================
// 缓存相关类型
// ============================================

export interface ProcessingCache {
  id: string;
  source_image_id: string;
  cache_type: 'thumbnail' | 'normalized' | 'slip_detect' | 'char_detect';
  cache_url: string;
  cache_meta: Record<string, any>;
  expires_at: string;
  created_at: string;
}

export interface ProcessingCacheCreate {
  source_image_id: string;
  cache_type: 'thumbnail' | 'normalized' | 'slip_detect' | 'char_detect';
  cache_url: string;
  cache_meta?: Record<string, any>;
}

// ============================================
// 导出相关类型
// ============================================

export interface ExportRecord {
  id: string;
  group_id: string;
  user_id: string;
  export_format: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_url?: string;
  file_size_bytes?: number;
  record_count: {
    groups: number;
    slips: number;
    chars: number;
  };
  created_at: string;
  completed_at?: string;
}

export interface ExportStatus {
  export_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number; // 0-1
  file_url?: string;
  file_size?: number;
  error_message?: string;
}

// ============================================
// 批量处理配置类型
// ============================================

export interface PreprocessConfig {
  target_long_side?: number;
  keep_aspect_ratio?: boolean;
  auto_rotate?: boolean;
  fixed_rotation_angle?: number;
  grayscale?: boolean;
  clahe_enabled?: boolean;
  denoise_strength?: number;
  output_format?: 'PNG' | 'JPEG';
  overwrite_original?: boolean;
}

export interface SegmentConfig {
  model_type?: 'yolov8' | 'opencv' | 'auto';
  sahi_slice_size?: number;
  sahi_overlap_ratio?: number;
  confidence_threshold?: number;
  min_char_distance?: number;
}

export interface BatchMetadataUpdate {
  fields: Record<string, any>;
  target_level: 'slip' | 'char';
}

// ============================================
// 进度相关类型
// ============================================

export interface ProcessProgress {
  total: number;
  completed: number;
  current_file?: string;
  status: string;
  error?: string;
}

// ============================================
// 导出配置类型
// ============================================

export interface ExportConfig {
  export_format: 'multimodal_json';
  include_group_metadata: boolean;
  include_images: boolean;
  include_slips: boolean;
  include_chars: boolean;
  include_metadata: boolean;
  include_original_images: boolean;
  image_encoding: 'base64' | 'url';
}

// ============================================
// 导出数据结构
// ============================================

export interface ExportData {
  export_version: string;
  export_time: string;
  group: {
    id: string;
    name: string;
    metadata: Record<string, any>;
    images: Array<{
      id: string;
      filename: string;
      url: string;
      slips: Array<{
        id: string;
        slip_no: string;
        bbox: [number, number, number, number];
        image_base64?: string;
        metadata: Record<string, any>;
        characters: Array<{
          id: string;
          position: { row: number; col: number };
          image_base64?: string;
          metadata: Record<string, any>;
        }>;
      }>;
    }>;
  };
}
