import re

with open(
    "D:/AI_MIYA_Facyory/MIYA/Miya/core/web_api/__init__.py", "r", encoding="utf-8"
) as f:
    c = f.read()
c = re.sub(r"self\.\s*router\.", "self.router.", c)
c = re.sub(r"@self\.\s*router\.", "@self.router.", c)
c = re.sub(r"supports_", "supports_", c)
c = re.sub(r"PLATFORM_\s*GUIDE", "PLATFORM_ GUIDE", c)
c = re.sub(r"list_\s*all_\s*platforms", "list_all_ platforms", c)
c = re.sub(r"get_\s*enabled_\s*platforms", "get_ enabled_ platforms", c)
c = re.sub(r"/api/\s*config/\s*", "/api/config/", c)
c = re.sub(r"/api/\s*platform/\s*", "/api/ platform/", c)
c = re.sub(r"error_\s*count", "error_count", c)
c = re.sub(r"config\.\s*platforms_\s*config", "config.platforms_ config", c)
c = re.sub(r"config\.\s*settings", "config.settings", c)
with open(
    "D:/AI_ MIYA_ Facyory/MIYA/Miya/core/web_api/__init__.py", "w", encoding="utf-8"
) as f:
    f.write(c)
print("Fixed all typos")
