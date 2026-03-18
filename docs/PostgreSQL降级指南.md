# PostgreSQL 降级操作指南

## 当前情况
- 已安装：PostgreSQL 18.3
- 安装位置：E:\date
- 目标：降级到 PostgreSQL 17 + TimescaleDB

## 手动操作步骤

### 1. 卸载 PostgreSQL 18

**方法A：使用 Windows 设置**
1. 打开"设置" → "应用" → "应用和功能"
2. 搜索 "PostgreSQL"
3. 点击 "PostgreSQL 18" → "卸载"
4. 按照向导完成卸载

**方法B：使用控制面板**
1. 打开"控制面板" → "程序和功能"
2. 找到 "PostgreSQL 18"
3. 右键 → "卸载"

**重要**：
- 卸载时会询问是否删除数据目录（E:\date\data）
- 选择"是"（因为我们要重新安装）

---

### 2. 下载 PostgreSQL 17

**下载地址**：
https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

**选择版本**：
- PostgreSQL 17.x
- Windows x86-64

**保存位置**：
- 下载到任意位置（如：下载文件夹）

---

### 3. 安装 PostgreSQL 17

**运行安装程序**：
1. 双击下载的 .exe 文件
2. 安装路径：选择 E:\date（或其他位置）
3. 组件选择：
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4
   - ✅ Command Line Tools
   - ✅ Stack Builder（重要！用于安装 TimescaleDB）
4. 数据目录：E:\date\data
5. 密码：@Cmx1454697261（或设置新密码）
6. 端口：5432（默认）
7. 区域设置：默认

**完成安装**

---

### 4. 使用 Stack Builder 安装 TimescaleDB

**安装完成后会自动弹出 Stack Builder**：

1. 选择 PostgreSQL 17 实例
2. 点击 "Next"
3. 展开 "Spatial Extensions" 或 "Add-ons, tools and utilities"
4. 找到并勾选 "TimescaleDB"
5. 点击 "Next" 开始下载和安装
6. 按照向导完成安装

**如果 Stack Builder 没有 TimescaleDB**：
- 手动下载：https://docs.timescale.com/self-hosted/latest/install/installation-windows/
- 下载适配 PostgreSQL 17 的版本
- 运行 setup.exe（以管理员身份）

---

### 5. 重启 PostgreSQL 服务

**PowerShell 命令**：
```powershell
Restart-Service postgresql-x64-17
```

或者在"服务"管理器中手动重启。

---

### 6. 验证安装

**测试 PostgreSQL 连接**：
```powershell
& "E:\date\bin\psql.exe" -U postgres -c "SELECT version();"
```

**测试 TimescaleDB 扩展**：
```powershell
& "E:\date\bin\psql.exe" -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'timescaledb';"
```

---

## 完成后通知我

安装完成后，告诉我：
1. PostgreSQL 17 是否安装成功
2. TimescaleDB 扩展是否可用
3. 我会继续帮你初始化数据库

---

## 预计时间

- 卸载 PostgreSQL 18：2-3 分钟
- 下载 PostgreSQL 17：5-10 分钟（取决于网速）
- 安装 PostgreSQL 17：5 分钟
- 安装 TimescaleDB：3-5 分钟
- **总计：15-25 分钟**
