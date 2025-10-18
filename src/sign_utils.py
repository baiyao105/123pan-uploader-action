"""
123Pan API签名生成工具
基于原项目的sign_get.py模块
"""

import random
import time
from datetime import datetime


def get_sign(e):
    """
    生成123Pan API请求签名

    Args:
        e: API路径, 如 "/b/api/file/list/new"

    Returns:
        tuple: (签名key, 签名值)
    """

    def unsigned_right_shift(n, shift):
        """无符号右移"""
        return (n % 0x100000000) >> shift

    def simulate_js_overflow(js_int, n):
        """模拟JavaScript整数溢出"""
        if js_int < 0:
            js_int = -js_int
            js_int = str(bin(js_int))[2:]
            js_int = js_int.zfill(32)
            js_int = js_int.replace("0", "2")
            js_int = js_int.replace("1", "0")
            js_int = js_int.replace("2", "1")
            js_int = int(js_int, 2) + 1
        bin_int = str(bin(js_int))[2:].zfill(32)
        if n < 0:
            n = -n
            n = str(bin(n))[2:]
            n = n.zfill(32)
            n = n.replace("0", "2")
            n = n.replace("1", "0")
            n = n.replace("2", "1")
            n = int(n, 2) + 1
        bin_n = str(bin(n))[2:].zfill(32)
        result = ""
        for i in range(0, len(bin_int)):
            temp = int(bin_n[i]) ^ int(bin_int[i])
            result = result + str(temp)
        if result[0] == "1":
            result = result.replace("0", "2")
            result = result.replace("1", "0")
            result = result.replace("2", "1")
            result = int(result, 2) + 1
            result = -result
        else:
            result = int(result, 2)
        return result

    def A(t):
        """MD5哈希生成"""
        r = t.replace("\r\n", "\n")
        a = -1

        def generate_array():
            t = []
            for e in range(256):
                n = e
                for _ in range(8):
                    if n & 1:  # 如果 n 的最低位是 1
                        n = simulate_js_overflow(3988292384, unsigned_right_shift(n, 1))
                    else:
                        n = unsigned_right_shift(n, 1)
                t.append(n)
            return t

        n = generate_array()
        for i in range(len(r)):
            a = unsigned_right_shift(a, 8) ^ n[255 & (a ^ ord(r[i]))]
        return str((simulate_js_overflow(-1, a)) & 0xFFFFFFFF)

    def generate_timestamp():
        """生成时间戳"""
        utc_offset = datetime.now().astimezone().utcoffset()
        if utc_offset is None:
            utc_offset_seconds = 0
        else:
            utc_offset_seconds = utc_offset.total_seconds()
        return round((time.time() + utc_offset_seconds + 28800) / 1)

    def adjust_timestamp(o, timestamp):
        """调整时间戳"""
        if timestamp:
            i = timestamp
            m = i
            if abs(1000 * o - 1000 * int(m)) / 1000 / 60 >= 20:
                return i
        return o

    def formatDate(t, e=None, n=8):
        """格式化日期"""
        t = int(t)  # Use the original timestamp
        t = t - 480 * 60
        r = datetime.fromtimestamp(t + 3600 * n)  # Convert to seconds and add 'n' hours
        data = {
            "y": str(r.year),
            "m": f"0{r.month}" if r.month < 10 else str(r.month),
            "d": f"0{r.day}" if r.day < 10 else str(r.day),
            "h": f"0{r.hour}" if r.hour < 10 else str(r.hour),
            "f": f"0{r.minute}" if r.minute < 10 else str(r.minute),
        }
        return data

    def generate_signature(a, o, e, n, r):
        """生成签名"""
        s = [
            "a",
            "d",
            "e",
            "f",
            "g",
            "h",
            "l",
            "m",
            "y",
            "i",
            "j",
            "n",
            "o",
            "p",
            "k",
            "q",
            "r",
            "s",
            "t",
            "u",
            "b",
            "c",
            "v",
            "w",
            "s",
            "z",
        ]
        u = formatDate(o)
        h = u["y"]
        g = u["m"]
        l = u["d"]
        c = u["h"]
        u = u["f"]
        d = f"{h}{g}{l}{c}{u}"
        f = [s[int(p)] for p in d]
        h = A("".join(f))
        g = A(f"{o}|{a}|{e}|{n}|{r}|{h}")
        return [h, f"{o}-{a}-{g}"]

    # 生成随机数和时间戳
    a = str(random.randint(0, 9999999))
    o = generate_timestamp()
    o = adjust_timestamp(o, timestamp=round(time.time()))

    n = "web"
    r = "3"
    return generate_signature(a, o, e, n, r)
