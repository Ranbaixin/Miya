
import sys
f = open(r"D:\AI_MIYA_Facyory\MIYA\Miya\core\web_api\__init__.py", "r", encoding="utf-8")
content = f.read()
f.close()
target = chr(34) + chr(92) + "n" + chr(34) + "))" + chr(92) + "n" + chr(32)*4 + "@self.router.get(" + chr(34) + "/health" + chr(34) + "))"
print("Read OK, finding target...")
pos = content.find(target)
print("Target at:", pos)
