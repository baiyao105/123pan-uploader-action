"""
123Pan文件上传器
支持单文件和目录上传, 包含进度显示和冲突处理
"""

import hashlib
import os
import time
from typing import Any, Dict, Optional

from loguru import logger


class ProgressBar:
    """进度条"""

    def __init__(self, total: int, desc: str = "进度", unit: str = "B", unit_scale: bool = True):
        self.total = total
        self.desc = desc
        self.unit = unit
        self.unit_scale = unit_scale
        self.current = 0
        self.start_time = time.time()
        self.last_update = 0

    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        current_time = time.time()
        if current_time - self.last_update < 0.5 and self.current < self.total:
            return
        self.last_update = current_time
        self._display_progress()

    def _display_progress(self):
        """显示进度信息"""
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        elapsed = time.time() - self.start_time
        if self.unit_scale and self.unit == "B":
            current_size = self._format_size(self.current)
            total_size = self._format_size(self.total)
            size_info = f"{current_size}/{total_size}"
        else:
            size_info = f"{self.current}/{self.total} {self.unit}"
        speed = self.current / elapsed if elapsed > 0 else 0
        speed_str = (
            self._format_size(speed) + "/s" if self.unit_scale and self.unit == "B" else f"{speed:.1f} {self.unit}/s"
        )
        if speed > 0 and self.current < self.total:
            eta = (self.total - self.current) / speed
            eta_str = self._format_time(eta)
        else:
            eta_str = "00:00"
        bar_length = 30
        filled_length = int(bar_length * percentage / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        if percentage == 100:
            color = "\033[32m"  # 绿色
            status = "✅"
        elif percentage >= 50:
            color = "\033[33m"  # 黄色
            status = "🔄"
        else:
            color = "\033[36m"  # 青色
            status = "⏳"
        reset_color = "\033[0m"
        print(
            f"{color}{status} {self.desc}: {bar} {percentage:6.1f}% | {size_info} | {speed_str} | ETA: {eta_str}{reset_color}"
        )

    def _format_size(self, size: float) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{int(seconds):02d}s"
        elif seconds < 3600:
            return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours:02d}:{minutes:02d}:00"

    def close(self):
        """关闭进度条"""
        if self.current >= self.total:
            print(f"\033[32m✅ {self.desc}: 完成! 总用时: {self._format_time(time.time() - self.start_time)}\033[0m")
        else:
            print(f"\033[31m❌ {self.desc}: 中断\033[0m")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Pan123Uploader:
    """123Pan文件上传器"""

    def __init__(self, client, chunk_size: int = 10 * 1024 * 1024, max_retries: int = 3):
        self.client = client
        self.uploaded_files = []
        self.chunk_size = chunk_size  # 分块大小, 默认10MB
        self.max_retries = max_retries  # 最大重试次数

    def upload_file(self, local_path: str, remote_dir: str = "/", conflict_strategy: str = "skip") -> bool:
        """
        上传单个文件

        Args:
            local_path: 本地文件路径
            remote_dir: 远程目录路径
            conflict_strategy: 冲突处理策略 (skip/overwrite/keep_both)

        Returns:
            bool: 上传是否成功
        """
        if not os.path.isfile(local_path):
            logger.error(f"❌ 文件不存在: {local_path}")
            return False

        filename = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)

        logger.debug(f"📁 准备上传文件: {filename} ({self._format_size(file_size)})")

        try:
            remote_dir_result = self._ensure_remote_dir(remote_dir)
            if not remote_dir_result:
                return False
            remote_dir = remote_dir_result
            if not self._handle_file_conflict(filename, remote_dir, conflict_strategy):
                return False
            logger.debug("🔍 计算文件MD5...")
            file_md5 = self._calculate_file_md5(local_path)
            if self._try_instant_upload(local_path, filename, file_size, file_md5, 0):  # 传递正确的参数
                logger.success(f"⚡ 秒传成功: {filename}")
                self.uploaded_files.append(filename)
                return True
            return self._upload_file_chunks(local_path, filename, file_size, file_md5, remote_dir)

        except Exception as e:
            logger.exception(f"❌ 上传失败: {filename} - {e!s}")
            return False

    def upload_directory(
        self, local_dir: str, remote_dir: str = "/", conflict_strategy: str = "skip"
    ) -> Dict[str, Any]:
        """
        上传整个目录

        Args:
            local_dir: 本地目录路径
            remote_dir: 远程目录路径
            conflict_strategy: 冲突处理策略

        Returns:
            dict: 上传结果统计
        """
        if not os.path.isdir(local_dir):
            logger.error(f"❌ 目录不存在: {local_dir}")
            return {"success": 0, "failed": 0, "skipped": 0}

        results = {"success": 0, "failed": 0, "skipped": 0}
        for root, _dirs, files in os.walk(local_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(root, local_dir)
                target_dir = remote_dir if rel_path == "." else os.path.join(remote_dir, rel_path).replace("\\", "/")
                if self.upload_file(local_file_path, target_dir, conflict_strategy):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    logger.error(f"❌ 上传失败: {file}")

        total = results["success"] + results["failed"] + results["skipped"]
        logger.success(
            f"📊 上传完成: 成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}, 总计 {total}"
        )

        return results

    def _upload_file_chunks(
        self, local_path: str, filename: str, file_size: int, file_md5: str, remote_dir: str
    ) -> bool:
        """执行分块上传"""

        upload_info = self._request_upload(filename, file_size, file_md5, remote_dir)
        if not upload_info:
            return False
        if upload_info.get("reuse", False):
            logger.success(f"✅ 文件已存在, 秒传成功: {filename}")
            self.uploaded_files.append(filename)
            return True
        chunk_size = 1024 * 1024 * 5  # 5MB per chunk
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        with ProgressBar(total=file_size, desc=f"上传 {filename}", unit="B", unit_scale=True) as pbar, \
             open(local_path, "rb") as f:
            for chunk_index in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                if not self._upload_chunk(upload_info, chunk_data, chunk_index):
                    logger.error(f"❌ 分块上传失败: {filename} (chunk {chunk_index + 1}/{total_chunks})")
                    return False

                pbar.update(len(chunk_data))

        if self._complete_upload(upload_info):
            logger.success(f"✅ 上传成功: {filename}")
            self.uploaded_files.append(filename)
            return True
        else:
            logger.error(f"❌ 完成上传失败: {filename}")
            return False

    def _handle_file_conflict(self, filename: str, remote_dir: str, strategy: str) -> bool:
        """处理文件冲突"""
        dir_info = self.client.get_directory_info(remote_dir)
        if not dir_info:
            return True
        existing_file = None
        for item in dir_info.get("InfoList", []):
            if item.get("FileName") == filename and item.get("Type") == 0:  # 0表示文件
                existing_file = item
                break
        if not existing_file:
            return True  # 没有冲突

        if strategy == "skip":
            logger.info(f"⏭️  跳过已存在的文件: {filename}")
            return False
        elif strategy == "overwrite":
            logger.info(f"🔄 覆盖已存在的文件: {filename}")
            # 删除已存在的文件
            if self.client.delete_file(existing_file):
                logger.success(f"✅ 删除旧文件成功: {filename}")
                return True
            else:
                logger.error(f"❌ 删除旧文件失败: {filename}")
                return False
        elif strategy == "keep_both":
            logger.info(f"📝 保留两个版本: {filename}")
            return True

        return True

    def _ensure_remote_dir(self, remote_dir: str) -> Optional[str]:
        """确保远程目录存在"""
        if remote_dir == "/" or not remote_dir:
            return "/"

        # 清理路径格式
        remote_dir = remote_dir.replace("\\", "/")
        if not remote_dir.startswith("/"):
            remote_dir = "/" + remote_dir
        if remote_dir.endswith("/") and remote_dir != "/":
            remote_dir = remote_dir[:-1]

        # 获取目录ID
        dir_id = self.client.get_directory_id(remote_dir)
        if dir_id is not None:
            return remote_dir

        # 目录不存在, 需要创建
        # 提取目录名(去掉前面的斜杠)
        dirname = remote_dir.lstrip("/")
        logger.debug(f"📁 创建远程目录: {dirname}")

        created_id = self.client.create_directory(dirname, 0)
        if created_id:
            logger.success(f"✅ 目录创建成功: {dirname}")
            return remote_dir
        else:
            logger.error(f"❌ 目录创建失败: {dirname}")
            return None

    def _calculate_file_md5(self, file_path: str) -> str:
        """计算文件MD5值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _try_instant_upload(
        self, file_path: str, file_name: str, file_size: int, md5_hash: str, parent_id: int
    ) -> bool:
        """
        尝试秒传文件

        Args:
            file_path: 文件路径
            file_name: 文件名
            file_size: 文件大小
            md5_hash: 文件MD5值
            parent_id: 父目录ID

        Returns:
            bool: 秒传成功返回True, 否则返回False
        """
        try:
            upload_request = {
                "driveId": 0,
                "etag": md5_hash,
                "fileName": file_name,
                "parentFileId": parent_id,
                "size": file_size,
                "type": 0,
                "duplicate": 0,  # 初始不允许重复
            }
            response = self.client.request_upload(upload_request)
            if response.get("code") == 0:
                reuse = response.get("data", {}).get("Reuse")
                if reuse:
                    logger.success(f"✅ 秒传成功: {file_name}")
                    return True
                else:
                    logger.warning(f"⚠️ 需要正常上传: {file_name}")
                    return False
            else:
                logger.error(f"❌ 秒传检查失败: {response}")
                return False

        except Exception as e:
            logger.exception(f"❌ 秒传检查异常: {e!s}")
            return False

    def _request_upload(self, filename: str, file_size: int, file_md5: str, remote_dir: str) -> Optional[Dict]:
        """
        请求上传, 获取上传信息

        Args:
            filename: 文件名
            file_size: 文件大小
            file_md5: 文件MD5值
            remote_dir: 远程目录路径

        Returns:
            dict: 上传信息, 包含bucket、key、uploadId等
        """
        try:
            parent_id = self.client.get_directory_id(remote_dir)
            if parent_id is None:
                logger.error(f"❌ 无法获取目录ID: {remote_dir}")
                return None
            upload_request = {
                "driveId": 0,
                "etag": file_md5,
                "fileName": filename,
                "parentFileId": parent_id,
                "size": file_size,
                "type": 0,
                "duplicate": 0,  # 不允许重复
            }

            response = self.client.request_upload(upload_request)
            if response.get("code") == 0:
                data = response.get("data", {})
                if data.get("Reuse"):
                    return {"reuse": True}
                upload_info = {
                    "reuse": False,
                    "bucket": data.get("Bucket"),
                    "storage_node": data.get("StorageNode"),
                    "key": data.get("Key"),
                    "upload_id": data.get("UploadId"),
                    "file_id": data.get("FileId"),
                }
                logger.success(f"🔄 获取上传信息成功: {filename}")
                logger.debug(f"📋 上传信息详情: {upload_info}")
                return upload_info

            elif response.get("code") == 5060:
                logger.warning(f"⚠️ 检测到重复文件: {filename}")
                return None
            else:
                logger.error(f"❌ 上传请求失败: {response}")
                return None

        except Exception as e:
            logger.exception(f"❌ 上传请求异常: {e!s}")
            return None

    def _upload_chunk(self, upload_info: Dict, chunk_data: bytes, chunk_index: int) -> bool:
        """
        上传文件分块

        Args:
            upload_info: 上传信息, 包含bucket、key、uploadId等
            chunk_data: 分块数据
            chunk_index: 分块索引(从0开始)

        Returns:
            bool: 上传成功返回True, 否则返回False
        """
        try:
            # 分块编号从1开始
            part_number = chunk_index + 1
            get_link_data = {
                "bucket": upload_info["bucket"],
                "key": upload_info["key"],
                "partNumberEnd": part_number + 1,
                "partNumberStart": part_number,
                "uploadId": upload_info["upload_id"],
                "StorageNode": upload_info["storage_node"],
            }

            # print(f"🔗 获取分块{part_number}上传链接请求数据: {get_link_data}")
            response = self.client.get_upload_parts_batch(get_link_data)
            # print(f"🔗 获取分块{part_number}上传链接API响应: {response}")
            if response.get("code") != 0:
                logger.error(f"❌ 获取分块上传链接失败: {response}")
                return False
            presigned_urls = response.get("data", {}).get("presignedUrls", {})
            upload_url = presigned_urls.get(str(part_number))
            # print(f"🔗 分块{part_number}预签名URL: {upload_url}")
            if not upload_url:
                logger.error(f"❌ 未获取到分块{part_number}的上传链接")
                return False
            upload_response = self.client.upload_chunk_data(upload_url, chunk_data)

            if upload_response:
                logger.success(f"✅ 分块{part_number}上传成功")
                return True
            else:
                logger.error(f"❌ 分块{part_number}上传失败")
                return False

        except Exception as e:
            logger.exception(f"❌ 分块上传异常: {e!s}")
            return False

    def _complete_upload(self, upload_info: Dict) -> bool:
        """
        完成上传流程

        Args:
            upload_info: 上传信息, 包含bucket、key、uploadId、fileId等

        Returns:
            bool: 完成上传成功返回True, 否则返回False
        """
        try:
            list_parts_data = {
                "bucket": upload_info["bucket"],
                "key": upload_info["key"],
                "uploadId": upload_info["upload_id"],
                "storageNode": upload_info["storage_node"],
            }
            self.client.list_upload_parts(list_parts_data)
            complete_multipart_data = {
                "bucket": upload_info["bucket"],
                "key": upload_info["key"],
                "uploadId": upload_info["upload_id"],
                "storageNode": upload_info["storage_node"],
            }
            self.client.complete_multipart_upload(complete_multipart_data)
            close_session_data = {"fileId": upload_info["file_id"]}
            close_response = self.client.complete_upload(close_session_data)
            if close_response.get("code") == 0:
                return True
            else:
                logger.error(f"❌ 完成上传失败: {close_response}")
                return False

        except Exception as e:
            logger.exception(f"❌ 完成上传异常: {e!s}")
            return False

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        size_float = float(size)  # 转换为float进行计算
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f}{unit}"
            size_float /= 1024.0
        return f"{size_float:.1f}PB"
