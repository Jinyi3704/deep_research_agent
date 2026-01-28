# Supabase 数据库集成说明

本项目已集成 Supabase 数据库，用于持久化存储每次对话的数据。

## 功能特性

- ✅ 自动保存每次用户输入和助手回复
- ✅ 保存规划（plan）和反思（reflection）内容
- ✅ 支持会话 ID（session_id）关联同一会话的多轮对话
- ✅ 自动时间戳记录
- ✅ 失败时优雅降级（不影响主程序运行）

## 设置步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建数据库表

在 Supabase Dashboard 的 SQL Editor 中执行 `docs/supabase_schema.sql` 中的 SQL 脚本：

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    user_input TEXT NOT NULL,
    assistant_output TEXT NOT NULL,
    plan TEXT,
    reflection TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
```

### 3. 配置环境变量（可选）

如果你想通过环境变量配置，可以在 `.env` 文件中添加：

```env
SUPABASE_URL=
SUPABASE_API_KEY=
```

**注意**：当前代码中已经硬编码了你的 Supabase 配置，所以这一步是可选的。如果你想使用环境变量，可以修改 `src/main.py` 中的相关代码。

### 4. 运行程序

```bash
cd src
python main.py
```

程序启动时会尝试连接 Supabase，如果连接成功会在 stderr 输出：
```
✓ Supabase connection initialized
```

如果连接失败，会显示警告但程序仍可正常运行（只是不会保存到数据库）。

## 数据表结构

### conversations 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGSERIAL | 主键，自增 |
| `session_id` | TEXT | 会话 ID，用于关联同一会话的多轮对话 |
| `user_input` | TEXT | 用户输入（必填） |
| `assistant_output` | TEXT | 助手回复（必填） |
| `plan` | TEXT | 规划内容（可选） |
| `reflection` | TEXT | 反思内容（可选） |
| `created_at` | TIMESTAMP | 创建时间，自动生成 |

## 代码说明

### 核心文件

1. **`src/memory/supabase_client.py`**
   - `SupabaseClient` 类：封装 Supabase 客户端
   - `save_conversation()` 方法：保存对话到数据库

2. **`src/memory/memory_manager.py`**
   - 修改了 `MemoryManager` 类，添加了 `supabase_client` 参数
   - `add_interaction()` 方法现在会自动保存到 Supabase

3. **`src/agent/orchestrator.py`**
   - 修改了 `run()` 方法，传递 `plan` 和 `reflection` 给 MemoryManager

4. **`src/main.py`**
   - 初始化 Supabase 客户端并传递给 MemoryManager

## 查询示例

在 Supabase Dashboard 的 SQL Editor 中可以执行以下查询：

### 查看所有对话
```sql
SELECT * FROM conversations ORDER BY created_at DESC;
```

### 查看特定会话的所有对话
```sql
SELECT * FROM conversations 
WHERE session_id = 'your-session-id' 
ORDER BY created_at ASC;
```

### 统计每天的对话数量
```sql
SELECT DATE(created_at) as date, COUNT(*) as count
FROM conversations
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## 故障排除

### 问题：连接失败

**可能原因**：
1. Supabase URL 或 API Key 错误
2. 网络连接问题
3. Supabase 服务不可用

**解决方案**：
- 检查 URL 和 API Key 是否正确
- 检查网络连接
- 查看 stderr 输出的错误信息

### 问题：表不存在

**解决方案**：
- 确保已执行 `docs/supabase_schema.sql` 中的 SQL 脚本
- 在 Supabase Dashboard 中检查表是否存在

### 问题：权限错误

**解决方案**：
- 检查 API Key 是否有写入权限
- 如果启用了 RLS（Row Level Security），需要创建相应的策略

## 安全建议

1. **API Key 管理**：
   - 建议将 API Key 存储在 `.env` 文件中，不要提交到 Git
   - 使用服务角色密钥（service role key）而不是匿名密钥（anon key）以获得完整权限

2. **Row Level Security (RLS)**：
   - 如果需要在生产环境使用，建议启用 RLS 并创建适当的策略
   - 当前代码中 RLS 相关代码已注释，可根据需要启用

3. **数据隐私**：
   - 注意对话数据可能包含敏感信息
   - 确保 Supabase 项目的访问控制配置正确
