-- =============================================
-- 简牍图像数据库表结构
-- 补充原始图像、单支图像、单字图像的元数据表
-- =============================================

-- 原始图像元数据表
create table public.raw_image_metadata (
  id text not null references public.images(id) on delete cascade,
  source_file text null,
  scan_date date null,
  scanner text null,
  resolution integer null,
  color_mode text null,
  bit_depth integer null,
  file_size bigint null,
  provenance text null,
  description text null,
  tags text[] null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint raw_image_metadata_pkey primary key (id)
);

create index IF not exists idx_raw_image_metadata_created on public.raw_image_metadata using btree (created_at);
create index IF not exists idx_raw_image_metadata_tags on public.raw_image_metadata using gin (tags);


-- 单支图像元数据表
create table public.slip_image_metadata (
  id text not null references public.images(id) on delete cascade,
  original_image_id text not null references public.images(id),
  slip_number integer null,
  material text null,
  dimensions text null,
  preservation_state text null,
  writing_style text null,
  period text null,
  content_summary text null,
  has_seal boolean default false,
  seal_description text null,
  transcription text null,
  translation text null,
  annotations jsonb null,
  experts_opinion text null,
  research_notes text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint slip_image_metadata_pkey primary key (id),
  constraint slip_original_fkey foreign key (original_image_id) references public.images(id)
);

create index IF not exists idx_slip_metadata_original on public.slip_image_metadata using btree (original_image_id);
create index IF not exists idx_slip_metadata_period on public.slip_image_metadata using btree (period);


-- 单字图像元数据表
create table public.char_image_metadata (
  id text not null references public.images(id) on delete cascade,
  slip_image_id text not null references public.images(id),
  original_image_id text not null references public.images(id),
  char_position integer null,
  unicode char(1) null,
  character text null,
  variant_form text null,
  radical text null,
  stroke_count integer null,
  pinyin text null,
  meaning text null,
  reading text null,
  transcription text null,
  character_type text null,
  writing_variants jsonb null,
  position_in_slip_x numeric null,
  position_in_slip_y numeric null,
  confidence_score numeric null,
  is_uncertain boolean default false,
  expert_checked boolean default false,
  notes text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint char_image_metadata_pkey primary key (id),
  constraint char_slip_fkey foreign key (slip_image_id) references public.images(id),
  constraint char_original_fkey foreign key (original_image_id) references public.images(id)
);

create index IF not exists idx_char_metadata_slip on public.char_image_metadata using btree (slip_image_id);
create index IF not exists idx_char_metadata_unicode on public.char_image_metadata using btree (unicode);
create index IF not exists idx_char_metadata_character on public.char_image_metadata using btree ("character");


-- 视图：简牍层级结构视图
create or replace view public.image_hierarchy as
select
  i.id as image_id,
  i.image_type,
  i.filename,
  i.width,
  i.height,
  i.uploaded_at,
  i.parent_image_id,
  raw.source_file,
  raw.scan_date,
  raw.provenance as raw_provenance,
  slip.slip_number,
  slip.material,
  slip.period,
  slip.transcription as slip_transcription,
  char.char_position,
  char.character,
  char.unicode,
  char.transcription as char_transcription
from public.images i
left join public.raw_image_metadata raw on i.id = raw.id
left join public.slip_image_metadata slip on i.id = slip.id
left join public.char_image_metadata char on i.id = char.id
order by i.uploaded_at desc;


-- RLS 安全策略示例（可根据需要调整）
alter table public.raw_image_metadata enable row level security;
alter table public.slip_image_metadata enable row level security;
alter table public.char_image_metadata enable row level security;

-- 允许认证用户访问自己的数据
create policy "Users can view own raw image metadata" on public.raw_image_metadata
  for select using (auth.uid() in (
    select user_id from public.images where id = raw_image_metadata.id
  ));

create policy "Users can view own slip image metadata" on public.slip_image_metadata
  for select using (auth.uid() in (
    select user_id from public.images where id = slip_image_metadata.id
  ));

create policy "Users can view own char image metadata" on public.char_image_metadata
  for select using (auth.uid() in (
    select user_id from public.images where id = char_image_metadata.id
  ));
