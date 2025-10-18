# 123Pan Uploader Action

[![GitHub](https://img.shields.io/github/license/baiyao105/123pan-uploader-action)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/baiyao105/123pan-uploader-action)](https://github.com/baiyao105/123pan-uploader-action/releases)

一个用于将文件上传到123Pan云盘的GitHub Action。

## 📋 输入参数

### 必需参数

| 参数          | 描述                          | 示例       |
| ------------- | ----------------------------- | ---------- |
| `auth-method` | 认证方式：`password`、`token` | `password` |
| `path`        | 要上传的文件或目录路径        | `./dist`   |

### 认证参数

#### 用户名密码认证 (auth-method: password)

| 参数       | 描述         | 必需 |
| ---------- | ------------ | ---- |
| `username` | 123Pan用户名 | ✅    |
| `password` | 123Pan密码   | ✅    |

#### Token认证 (auth-method: token)

| 参数            | 描述            | 必需 |
| --------------- | --------------- | ---- |
| `authorization` | 123Pan授权token | ✅    |

### 可选参数

| 参数                | 描述             | 默认值      | 可选值                           |
| ------------------- | ---------------- | ----------- | -------------------------------- |
| `destination`       | 目标目录名称     | `""`        | 任意字符串                       |
| `conflict-strategy` | 文件冲突处理策略 | `keep-both` | `overwrite`, `keep-both`, `skip` |
| `max-retries`       | 最大重试次数     | `3`         | 数字                             |
| `chunk-size`        | 分块大小(MB)     | `5`         | 数字                             |

## 📤 输出参数

| 参数             | 描述                             |
| ---------------- | -------------------------------- |
| `upload-status`  | 上传状态：`success` 或 `failure` |
| `uploaded-files` | 成功上传的文件列表(JSON格式)     |
| `upload-url`     | 123Pan分享链接(如果可用)         |

## 🚀 使用示例

### 基础用法 - 用户名密码认证

```yaml
name: Upload to 123Pan

on:
  push:
    branches: [ main ]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Upload files to 123Pan
      uses: baiyao105/123pan-uploader-action@v1
      with:
        auth-method: 'password'
        username: ${{ secrets.PAN123_USERNAME }}
        password: ${{ secrets.PAN123_PASSWORD }}
        path: './dist'
        destination: 'my-project-build'
        conflict-strategy: 'overwrite'
```

### Token认证

```yaml
- name: Upload with Token
  uses: baiyao105/123pan-uploader-action@v1
  with:
    auth-method: 'token'
    authorization: ${{ secrets.PAN123_TOKEN }}
    path: './release'
    destination: 'releases'
```

### 上传单个文件

```yaml
- name: Upload single file
  uses: baiyao105/123pan-uploader-action@v1
  with:
    auth-method: 'password'
    username: ${{ secrets.PAN123_USERNAME }}
    password: ${{ secrets.PAN123_PASSWORD }}
    path: './build/app.zip'
    conflict-strategy: 'keep-both'
```

### 高级配置

```yaml
- name: Upload with advanced settings
  uses: baiyao105/123pan-uploader-action@v1
  with:
    auth-method: 'password'
    username: ${{ secrets.PAN123_USERNAME }}
    password: ${{ secrets.PAN123_PASSWORD }}
    path: './large-files'
    destination: 'backup-$(date +%Y%m%d)'
    conflict-strategy: 'skip'
    max-retries: 5
    chunk-size: 10
```

### 使用输出结果

```yaml
- name: Upload files
  id: upload
  uses: baiyao105/123pan-uploader-action@v1
  with:
    auth-method: 'password'
    username: ${{ secrets.PAN123_USERNAME }}
    password: ${{ secrets.PAN123_PASSWORD }}
    path: './dist'

- name: Check upload result
  run: |
    echo "Upload status: ${{ steps.upload.outputs.upload-status }}"
    echo "Uploaded files: ${{ steps.upload.outputs.uploaded-files }}"
```

## 🔧 冲突处理策略

| 策略        | 描述                             |
| ----------- | -------------------------------- |
| `overwrite` | 覆盖已存在的同名文件             |
| `keep-both` | 保留两个文件(新文件会自动重命名) |
| `skip`      | 跳过已存在的文件                 |

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

- 参考移植于: [123pan-uploader-cli](https://github.com/OlyMarco/123pan-uploader-cli) 项目
