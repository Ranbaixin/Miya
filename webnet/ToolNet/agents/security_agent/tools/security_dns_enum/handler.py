async def execute(args, context=None, **kwargs) -> str:
    """DNS 枚举"""
    from webnet.ToolNet.tools.security.dns_enum import SecurityDNSEnumTool

    domain = ""
    if isinstance(args, dict):
        domain = args.get("domain", "")
    elif context and hasattr(context, "get"):
        domain = context.get("domain", "")
    if kwargs:
        domain = kwargs.get("domain", domain)

    if not domain:
        return "请提供要查询的域名"

    tool = SecurityDNSEnumTool()
    return await tool.execute({"domain": domain}, context)
