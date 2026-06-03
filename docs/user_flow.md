# 生模系统用户流程

## 1. 配置模型

用户进入 `/settings`，查看当前 provider。点击“测试连接”后：

- 如果缺少 API key，页面提示应设置哪个环境变量；
- 如果 provider 可用，显示连接成功；
- 如果 API 返回错误，显示原始错误摘要。

## 2. 上传单篇论文

用户进入 `/papers/upload`，选择 PDF。系统保存：

```text
workspace/runs/<job_id>/source.pdf
workspace/runs/<job_id>/original_filename.txt
```

同时在 SQLite 中记录 job：`pending / uploaded`。

## 3. 运行流水线

任务页点击运行后：

```text
parse -> evidence -> teach_me -> render
```

每一步失败都更新 job 状态为 `failed`，并显示错误。成功时生成：

```text
parsed_document.json
evidence.json
cards/json/*.json
cards/html/*.html
```

## 4. 阅读卡片

用户进入 `/cards/<job_id>` 查看卡片列表。每张卡保留：

- 30 秒看懂；
- 5 分钟讲懂；
- 深挖推导；
- evidence；
- 复述题；
- 隔天复习题；
- 导师/审稿人追问。

## 5. 搜索方向

用户进入 `/search?query=...`。系统只调用 `paper-search-mcp`。如果未安装，页面显示日志提示，不自研 crawler。

