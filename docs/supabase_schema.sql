-- Supabase 数据库表结构
-- 用于存储 AI 深度研究助手的对话记录

-- 创建 conversations 表
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    user_input TEXT NOT NULL,
    assistant_output TEXT NOT NULL,
    plan TEXT,
    reflection TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);

-- 可选：启用 Row Level Security (RLS)
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- 可选：创建策略（如果需要公开访问，可以创建允许所有操作的策略）
-- CREATE POLICY "Allow all operations" ON conversations FOR ALL USING (true) WITH CHECK (true);
