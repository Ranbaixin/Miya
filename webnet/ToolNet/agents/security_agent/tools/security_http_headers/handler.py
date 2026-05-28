async def execute(args, context=None, **kwargs) -> str:
    """HTTP头安全分析"""
    from webnet.ToolNet.tools.security.http_headers import SecurityHTTPHeadersTool

    url = ""
    if isinstance(args, dict):
        url = args.get("url", "")
    elif context and hasattr(context, "get"):
        url = context.get("url", "")
    if kwargs:
        url = kwargs.get("url", url)

    if not url:
        return "请提供要分析的 URL"

    tool = SecurityHTTPHeadersTool()
    return await tool.execute({"url": url}, context)
