async def execute(args, context=None, **kwargs) -> str:
    """SSL 证书检查"""
    from webnet.ToolNet.tools.security.ssl_cert import SecuritySSLCertTool

    hostname = ""
    if isinstance(args, dict):
        hostname = args.get("hostname", "")
    elif context and hasattr(context, "get"):
        hostname = context.get("hostname", "")
    if kwargs:
        hostname = kwargs.get("hostname", hostname)

    if not hostname:
        return "请提供要检查的域名"

    tool = SecuritySSLCertTool()
    return await tool.execute({"hostname": hostname}, context)
