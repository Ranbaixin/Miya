async def execute(args, context=None, **kwargs) -> str:
    """子域名枚举"""
    from webnet.ToolNet.tools.security.subdomain_enum import SecuritySubdomainEnumTool

    domain = ""
    if isinstance(args, dict):
        domain = args.get("domain", "")
    elif context and hasattr(context, "get"):
        domain = context.get("domain", "")
    if kwargs:
        domain = kwargs.get("domain", domain)

    if not domain:
        return "请提供要枚举的目标域名"

    tool = SecuritySubdomainEnumTool()
    scan_args = {"domain": domain}
    if isinstance(args, dict) and args.get("deep"):
        scan_args["deep"] = True

    return await tool.execute(scan_args, context)
