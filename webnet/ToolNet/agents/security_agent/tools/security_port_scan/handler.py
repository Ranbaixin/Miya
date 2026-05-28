async def execute(args, context=None, **kwargs) -> str:
    """端口扫描"""
    from webnet.ToolNet.tools.security.port_scanner import SecurityPortScanTool

    target = ""
    if isinstance(args, dict):
        target = args.get("target", "")
        ports = args.get("ports", None)
    elif context and hasattr(context, "get"):
        target = context.get("target", "")
    if kwargs:
        target = kwargs.get("target", target)

    if not target:
        return "请提供要扫描的目标主机或IP地址"

    tool = SecurityPortScanTool()
    scan_args = {"target": target}
    if isinstance(args, dict) and args.get("ports"):
        scan_args["ports"] = args["ports"]

    return await tool.execute(scan_args, context)
