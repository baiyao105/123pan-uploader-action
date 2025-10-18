#!/usr/bin/env python3
"""
GitHub Action for uploading files to 123Pan cloud storage
"""

import json
import os
import sys

from loguru import logger
from pan123_client import Pan123Client
from uploader import Pan123Uploader


def get_env_input(name: str, required: bool = True, default: str = "") -> str:
    """获取环境变量输入"""
    env_name = f"INPUT_{name.upper().replace('-', '_')}"
    value = os.environ.get(env_name, default)

    if required and not value:
        raise ValueError(f"Required input '{name}' is missing")

    return value


def set_output(name: str, value: str):
    """设置GitHub Action输出"""
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"::set-output name={name}::{value}")


def setup_logger():
    """配置loguru日志格式"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="[{level}] {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        colorize=True,
    )


def main():
    """主函数"""
    try:
        setup_logger()
        auth_method = get_env_input("auth-method")
        upload_path = get_env_input("path")
        destination = get_env_input("destination", required=False)
        conflict_strategy = get_env_input("conflict-strategy", required=False, default="keep-both")
        max_retries = int(get_env_input("max-retries", required=False, default="3"))
        chunk_size = int(get_env_input("chunk-size", required=False, default="5"))
        valid_strategies = ["overwrite", "keep-both", "skip"]
        if conflict_strategy not in valid_strategies:
            raise ValueError(f"Invalid conflict-strategy. Must be one of: {', '.join(valid_strategies)}")
        if not os.path.exists(upload_path):
            raise ValueError(f"Upload path does not exist: {upload_path}")
        client = Pan123Client()

        if auth_method == "password":
            username = get_env_input("username")
            password = get_env_input("password")
            if not client.login_with_password(username, password):
                raise Exception("Password authentication failed")
        elif auth_method == "token":
            authorization = get_env_input("authorization")
            if not client.login_with_token(authorization):
                raise Exception("Token authentication failed")
        else:
            raise ValueError(f"Invalid auth-method: {auth_method}. Must be 'password' or 'token'")

        uploader = Pan123Uploader(client, chunk_size, max_retries)
        success = False
        parent_id = 0  # 根目录
        if destination:
            # 清理目录名, 移除不允许的字符
            clean_dirname = destination.strip("/\\").replace("/", "_").replace("\\", "_")
            parent_id = client.create_directory(clean_dirname, 0)
            if not parent_id:
                raise Exception(f"Failed to create destination directory: {clean_dirname}")
            remote_dir = f"/{clean_dirname}"  # 将目录ID转换为路径
        else:
            remote_dir = "/"  # 根目录

        if os.path.isfile(upload_path):
            logger.info(f"📤 上传文件: {upload_path}")
            success = uploader.upload_file(upload_path, remote_dir, conflict_strategy)
        elif os.path.isdir(upload_path):
            logger.info(f"📁 上传目录: {upload_path}")
            success = uploader.upload_directory(upload_path, remote_dir, conflict_strategy)
        else:
            raise ValueError(f"Invalid path type: {upload_path}")

        if success:
            set_output("upload-status", "success")
            set_output("uploaded-files", json.dumps(uploader.uploaded_files))
            logger.success("✅ 上传完成!")
            if uploader.uploaded_files:
                logger.info("📋 上传文件列表:")
                for i, filename in enumerate(uploader.uploaded_files, 1):
                    logger.info(f"  {i}. {filename}")
        else:
            set_output("upload-status", "failure")
            set_output("uploaded-files", "[]")
            logger.error("❌ 上传失败!")
            sys.exit(1)

    except Exception as e:
        logger.exception(f"❌ 执行失败: {e!s}")
        set_output("upload-status", "failure")
        set_output("uploaded-files", "[]")
        sys.exit(1)


if __name__ == "__main__":
    main()
