async def execute(args, context=None, **kwargs) -> str:
    """漏洞查询"""
    from webnet.ToolNet.tools.security.vuln_lookup import SecurityVulnLookupTool

    cve = ""
    keyword = ""
    if isinstance(args, dict):
        cve = args.get("cve", "")
        keyword = args.get("keyword", "")
    elif context and hasattr(context, "get"):
        cve = context.get("cve", "")
        keyword = context.get("keyword", "")
    if kwargs:
        cve = kwargs.get("cve", cve)
        keyword = kwargs.get("keyword", keyword)

    if not cve and not keyword:
        return "请提供 CVE 编号或搜索关键词"

    tool = SecurityVulnLookupTool()
    query_args = {}
    if cve:
        query_args["cve"] = cve
    if keyword:
        query_args["keyword"] = keyword

    return await tool.execute(query_args, context)
