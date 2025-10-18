"""
123Pan-sign
"""

import hashlib
import json
from typing import Dict, List, Optional

import requests
from loguru import logger
from sign_utils import get_sign


class Pan123Client:
    """123Pan云盘客户端"""

    def __init__(self):
        self.authorization = ""
        self.parent_file_id = 0
        self.session = requests.Session()
        self.base_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "app-version": "3",
            "platform": "web",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Referer": "https://www.123pan.com/",
        }

    def login_with_password(self, username: str, password: str) -> bool:
        """
        使用用户名密码登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            bool: 登录是否成功
        """
        try:
            logger.debug("🔐 正在登录(账号-密码)..")
            login_data = {"passport": username, "password": password, "remember": True}
            sign = get_sign("/b/api/user/sign_in")
            response = self.session.post(
                "https://www.123pan.com/b/api/user/sign_in",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(login_data),
            )
            result = response.json()

            if result.get("code") == 200:
                self.authorization = result["data"]["token"]
                self._update_headers()
                logger.success("✅ 登录成功!")
                return True
            else:
                logger.error(f"❌ 登录失败({result.get('code')}): {result.get('message', '未知错误')}")
                return False

        except Exception as e:
            logger.exception(f"❌ 登录过程中发生错误: {e!s}")
            return False

    def login_with_token(self, authorization: str) -> bool:
        """
        使用Token接口登录

        Args:
            authorization: Token授权token

        Returns:
            bool: 登录是否成功
        """
        try:
            logger.debug("🔐 正在验证(token)...")
            self.authorization = authorization
            if self._verify_token():
                logger.success("✅ Token验证成功!")
                return True
            else:
                logger.error("❌ Token验证失败")
                return False

        except Exception as e:
            logger.exception(f"❌ Token验证过程中发生错误: {e!s}")
            return False

    def _update_headers(self):
        """更新请求头中的Authorization"""
        self.base_headers["Authorization"] = f"Bearer {self.authorization}"

    def _verify_token(self) -> bool:
        """验证token有效性"""
        try:
            sign = get_sign("/b/api/file/list/new")
            response = self.session.get(
                "https://www.123pan.com/b/api/file/list/new",
                headers=self.base_headers,
                params={
                    sign[0]: sign[1],
                    "driveId": 0,
                    "limit": 1,
                    "next": "",
                    "orderBy": "file_id",
                    "orderDirection": "desc",
                    "parentFileId": 0,
                    "trashed": False,
                },
            )

            result = response.json()
            return result.get("code") == 0

        except Exception:
            return False

    def get_directory_info(self, parent_id: int = 0) -> Optional[List[Dict]]:
        """
        获取目录信息

        Args:
            parent_id: 父目录ID, 0为根目录

        Returns:
            目录文件列表
        """
        try:
            sign = get_sign("/b/api/file/list/new")
            response = self.session.get(
                "https://www.123pan.com/b/api/file/list/new",
                headers=self.base_headers,
                params={
                    sign[0]: sign[1],
                    "driveId": 0,
                    "limit": 100,
                    "next": "",
                    "orderBy": "file_id",
                    "orderDirection": "desc",
                    "parentFileId": parent_id,
                    "trashed": False,
                },
            )

            result = response.json()
            if result.get("code") == 0:
                return result["data"]["InfoList"]
            return None

        except Exception as e:
            logger.exception(f"❌ 获取目录信息失败: {e!s}")
            return None

    def create_directory(self, dirname: str, parent_id: int = 0) -> Optional[int]:
        """
        创建目录

        Args:
            dirname: 目录名
            parent_id: 父目录ID

        Returns:
            新创建目录的ID, 失败返回None
        """
        try:
            # 检查目录是否已存在
            existing_files = self.get_directory_info(parent_id)
            if existing_files:
                for file_info in existing_files:
                    if file_info["FileName"] == dirname and file_info["Type"] == 1:
                        logger.debug(f"📁 目录 '{dirname}' 已存在, 使用现有目录")
                        return file_info["FileId"]
            create_data = {
                "driveId": 0,
                "etag": "",
                "fileName": dirname,
                "parentFileId": parent_id,
                "size": 0,
                "type": 1,
                "duplicate": 0,
            }

            sign = get_sign("/b/api/file/upload_request")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/upload_request",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(create_data),
            )

            result = response.json()
            if result.get("code") == 0:
                file_id = result["data"]["FileId"]
                logger.success(f"📁 成功创建目录: {dirname} (ID: {file_id})")
                return file_id
            else:
                logger.error(f"❌ 创建目录失败: {result.get('message', '未知错误')}")
                return None

        except Exception as e:
            logger.exception(f"❌ 创建目录过程中发生错误: {e!s}")
            return None

    def compute_file_md5(self, file_path: str) -> str:
        """计算文件MD5值"""
        with open(file_path, "rb") as f:
            md5 = hashlib.md5()
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                md5.update(chunk)
            return md5.hexdigest()

    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def delete_file(self, file_info: Dict) -> bool:
        """
        删除文件

        Args:
            file_info: 文件信息字典, 包含FileId

        Returns:
            bool: 删除是否成功
        """
        try:
            delete_data = {
                "driveId": 0,
                "fileTrashInfoList": [file_info],
                "operation": True,  # True表示删除, False表示恢复
            }
            response = self.session.post(
                "https://www.123pan.com/a/api/file/trash", headers=self.base_headers, data=json.dumps(delete_data)
            )
            result = response.json()
            if result.get("code") == 0:
                return True
            else:
                logger.error(f"❌ 删除文件失败: {result.get('message', '未知错误')}")
                return False

        except Exception as e:
            logger.exception(f"❌ 删除文件异常: {e}")
            return False

    def get_directory_id(self, path: str) -> Optional[int]:
        """
        根据路径获取目录ID

        Args:
            path: 目录路径, 如 "/" 或 "/folder" 或 "/folder/subfolder"

        Returns:
            目录ID, 失败返回None
        """
        if path == "/" or not path:
            return 0  # 根目录ID为0

        path = path.strip("/")
        if not path:
            return 0
        path_parts = path.split("/")
        current_parent_id = 0  # 从根目录开始
        for dir_name in path_parts:
            if not dir_name:  # 跳过空字符串
                continue
            dir_info = self.get_directory_info(current_parent_id)
            if not dir_info:
                logger.error(f"❌ 无法获取目录信息: parent_id={current_parent_id}")
                return None
            found_dir = None
            for item in dir_info:
                if item.get("FileName") == dir_name and item.get("Type") == 1:  # Type=1表示目录
                    found_dir = item
                    break
            if found_dir:
                current_parent_id = found_dir["FileId"]
                logger.debug(f"📁 找到目录: {dir_name} (ID: {current_parent_id})")
            else:
                logger.debug(f"📁 目录不存在, 创建: {dir_name}")
                new_dir_id = self.create_directory(dir_name, current_parent_id)
                if new_dir_id:
                    current_parent_id = new_dir_id
                else:
                    logger.error(f"❌ 创建目录失败: {dir_name}")
                    return None

        return current_parent_id

    def request_upload(self, upload_data: Dict) -> Dict:
        """
        请求上传文件

        Args:
            upload_data: 上传请求数据

        Returns:
            API响应结果
        """
        try:
            sign = get_sign("/b/api/file/upload_request")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/upload_request",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(upload_data),
            )
            return response.json()
        except Exception as e:
            logger.exception(f"❌ 上传请求异常: {e}")
            return {"code": -1, "message": str(e)}

    def get_upload_parts_batch(self, parts_data: Dict) -> Dict:
        """
        获取分块上传链接

        Args:
            parts_data: 分块请求数据

        Returns:
            API响应结果
        """
        try:
            # 使用正确的API endpoint
            sign = get_sign("/b/api/file/s3_repare_upload_parts_batch")
            headers = self.base_headers.copy()
            headers["Content-Type"] = "application/json"
            # logger.info(f"🔗 请求参数: {parts_data}")
            # logger.info(f"🔗 签名参数: {sign}")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/s3_repare_upload_parts_batch",
                headers=headers,
                params={sign[0]: sign[1]},
                data=json.dumps(parts_data),
            )
            result = response.json()
            # logger.info(f"🔗 分块上传链接API完整响应: {result}")
            return result
        except Exception as e:
            logger.exception(f"❌ 获取上传链接异常: {e}")
            return {"code": -1, "message": str(e)}

    def upload_chunk_data(self, upload_url: str, chunk_data: bytes) -> bool:
        """
        上传分块数据到S3

        Args:
            upload_url: 预签名上传URL
            chunk_data: 分块数据

        Returns:
            上传是否成功
        """
        try:
            response = self.session.put(upload_url, data=chunk_data)
            return response.status_code == 200
        except Exception as e:
            logger.exception(f"❌ 上传分块数据异常: {e}")
            return False

    def list_upload_parts(self, list_data: Dict) -> Dict:
        """
        列出已上传的分块

        Args:
            list_data: 列表请求数据

        Returns:
            API响应结果
        """
        try:
            sign = get_sign("/b/api/file/s3_list_upload_parts")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/s3_list_upload_parts",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(list_data),
            )
            return response.json()
        except Exception as e:
            logger.exception(f"❌ 列出分块异常: {e}")
            return {"code": -1, "message": str(e)}

    def complete_multipart_upload(self, complete_data: Dict) -> Dict:
        """
        完成多部分上传

        Args:
            complete_data: 完成上传数据

        Returns:
            API响应结果
        """
        try:
            sign = get_sign("/b/api/file/s3_complete_multipart_upload")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/s3_complete_multipart_upload",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(complete_data),
            )
            return response.json()
        except Exception as e:
            logger.exception(f"❌ 完成多部分上传异常: {e}")
            return {"code": -1, "message": str(e)}

    def complete_upload(self, complete_data: Dict) -> Dict:
        """
        完成上传会话

        Args:
            complete_data: 完成数据, 包含fileId

        Returns:
            API响应结果
        """
        try:
            sign = get_sign("/b/api/file/upload_complete")
            response = self.session.post(
                "https://www.123pan.com/b/api/file/upload_complete",
                headers=self.base_headers,
                params={sign[0]: sign[1]},
                data=json.dumps(complete_data),
            )
            return response.json()
        except Exception as e:
            logger.exception(f"❌ 完成上传会话异常: {e}")
            return {"code": -1, "message": str(e)}
