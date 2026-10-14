"""Oracle 连接串构建。

oracledb 2.5.1 的 tcp_connect_timeout 只在 thin 模式生效；thick 模式（本项目连
11g 必须使用）会忽略它，退回 Oracle Net 自己的 60 秒默认值，实测不可达主机要
挂 60.01s。只有描述符参数 CONNECT_TIMEOUT / RETRY_COUNT 能约束 thick 模式的握手，
实测 8.01s 返回 ORA-12170。两种模式的参数互不冲突，因此同时下发。
"""

import oracledb

# 单次 TCP 握手上限（秒）。生产内网握手为毫秒级，8 秒足够覆盖跨机房抖动。
CONNECT_TIMEOUT_SECONDS = 8


def build_dsn(host, port, service_name, *, connect_timeout: int = CONNECT_TIMEOUT_SECONDS) -> str:
    """构建自带网络超时守卫的 Oracle Net 描述符。

    参数值仍由 oracledb.makedsn 校验（含括号等字符会抛 DPY-2020），
    避免库配置里的 service_name 注入额外的描述符参数。
    """
    dsn = oracledb.makedsn(host, port, service_name=service_name)
    guard = f'(CONNECT_TIMEOUT={int(connect_timeout)})(RETRY_COUNT=0)'
    return dsn.replace('(DESCRIPTION=', f'(DESCRIPTION={guard}', 1)
