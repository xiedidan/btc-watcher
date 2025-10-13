# BTC Watcher 虚拟环境使用指南
# Virtual Environment Usage Guide

## 📦 虚拟环境说明

为了避免污染系统Python环境，BTC Watcher项目使用虚拟环境进行开发和测试。

---

## 🚀 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python3 -m venv venv
```

### 2. 激活虚拟环境

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 3. 安装依赖

```bash
# 安装主要依赖
pip install -r requirements.txt

# 安装测试依赖
pip install -r requirements-test.txt
```

### 4. 运行测试

```bash
# 在虚拟环境中运行测试
python -m pytest tests/unit/ -v
```

### 5. 退出虚拟环境

```bash
deactivate
```

---

## 🎯 使用脚本（推荐）

我们提供了自动管理虚拟环境的脚本：

```bash
# 自动创建venv、安装依赖、运行测试
./scripts/run_unit_tests.sh
```

脚本会自动：
- ✅ 检查并创建虚拟环境
- ✅ 激活虚拟环境
- ✅ 安装所有依赖
- ✅ 运行测试
- ✅ 生成覆盖率报告

---

## 📝 虚拟环境结构

```
backend/
├── venv/                    # 虚拟环境目录（已添加到.gitignore）
│   ├── bin/                 # 可执行文件
│   ├── lib/                 # Python库
│   └── include/             # 头文件
├── requirements.txt         # 主要依赖
├── requirements-test.txt    # 测试依赖
└── tests/                   # 测试文件
```

---

## 💡 常用命令

### 检查虚拟环境

```bash
# 检查是否在虚拟环境中
which python

# 查看已安装的包
pip list

# 查看Python版本
python --version
```

### 更新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt -r requirements-test.txt
```

### 冻结依赖

```bash
# 导出当前环境的依赖
pip freeze > requirements-freeze.txt
```

---

## 🔒 .gitignore配置

虚拟环境目录已添加到.gitignore:

```
# Python虚拟环境
venv/
env/
.venv/
ENV/
```

---

## 🧪 测试最佳实践

### 1. 始终在虚拟环境中测试

```bash
source venv/bin/activate
python -m pytest tests/unit/ -v
```

### 2. 清理环境

```bash
# 删除虚拟环境重新开始
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
```

### 3. 使用不同Python版本

```bash
# 使用Python 3.11
python3.11 -m venv venv311
source venv311/bin/activate

# 使用Python 3.12
python3.12 -m venv venv312
source venv312/bin/activate
```

---

## 🐳 Docker环境

对于生产环境，推荐使用Docker:

```bash
# Docker中已经是隔离环境，不需要venv
docker-compose up -d

# 进入容器
docker exec -it btc-watcher-api bash
```

---

## ⚠️ 注意事项

1. **不要提交venv到Git**
   - venv目录已在.gitignore中
   - 只提交requirements.txt

2. **定期更新依赖**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **保持依赖文件最新**
   ```bash
   pip freeze > requirements.txt
   ```

4. **使用相同的Python版本**
   - 开发: Python 3.11+
   - 生产: Python 3.11（Docker）

---

## 🔧 故障排查

### 问题1: 虚拟环境激活失败

```bash
# 确保有执行权限
chmod +x venv/bin/activate

# 使用绝对路径
source /path/to/venv/bin/activate
```

### 问题2: 依赖安装失败

```bash
# 升级pip
pip install --upgrade pip setuptools wheel

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

### 问题3: 找不到模块

```bash
# 确保在虚拟环境中
which python  # 应该指向venv/bin/python

# 重新安装依赖
pip install -r requirements.txt
```

---

## 📚 相关命令

### Makefile集成

```makefile
# 在Makefile中使用虚拟环境
test-unit:
    @./scripts/run_unit_tests.sh

test-unit-manual:
    @cd backend && source venv/bin/activate && python -m pytest tests/unit/ -v
```

### CI/CD集成

```yaml
# GitHub Actions
- name: Setup Python
  uses: actions/setup-python@v2
  with:
    python-version: '3.11'

- name: Create venv and install dependencies
  run: |
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -r requirements-test.txt

- name: Run tests
  run: |
    source venv/bin/activate
    pytest tests/unit/ -v
```

---

## ✅ 检查清单

使用虚拟环境前：
- [ ] 已创建虚拟环境
- [ ] 已激活虚拟环境
- [ ] 已安装所有依赖
- [ ] 确认Python版本正确

运行测试前：
- [ ] 虚拟环境已激活
- [ ] 依赖已安装
- [ ] 位于正确的目录

提交代码前：
- [ ] venv已在.gitignore中
- [ ] requirements.txt已更新
- [ ] 测试在虚拟环境中通过

---

**虚拟环境版本**: Python 3.11+
**最后更新**: 2025-10-11
