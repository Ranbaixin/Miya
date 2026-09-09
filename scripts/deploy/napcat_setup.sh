#!/usr/bin/env bash
# NapCat QQ 协议端安装（多镜像源自愈拉取，成功后自动启动容器）
# 用法: bash napcat_setup.sh <机器人QQ号>   （root 运行，需先完成 server_setup.sh）
set -e
QQ=${1:?usage: napcat_setup.sh <QQ号>}
LOG=/tmp/napcat_pull.log
STATUS=/tmp/napcat_status
mkdir -p /opt/napcat/app /opt/napcat/config
echo "start $(date)" > $LOG

declare -a REFS=(
  "mlikiowa/napcat-docker:latest"
  "docker.m.daocloud.io/mlikiowa/napcat-docker:latest"
  "docker.1ms.run/mlikiowa/napcat-docker:latest"
  "ghcr.io/napneko/napcat:latest"
)
OK_REF=""
for REF in "${REFS[@]}"; do
  echo "=== pulling $REF ===" >> $LOG
  for attempt in 1 2; do
    timeout 900 docker pull "$REF" >> $LOG 2>&1
    if docker images --format '{{.Repository}}:{{.Tag}}' | grep -qi "$(echo $REF | cut -d: -f1)"; then
      OK_REF="$REF"; break 2
    fi
    echo "attempt $attempt for $REF failed" >> $LOG
    sleep 5
  done
done
[ -z "$OK_REF" ] && { echo "PULL_FAILED（详见 $LOG）"; exit 1; }

docker rm -f napcat >/dev/null 2>&1 || true
docker run -d --name napcat --network host --restart always \
  -e ACCOUNT="$QQ" -e NAPCAT_UID=0 -e NAPCAT_GID=0 \
  -v /opt/napcat/app:/app/napcat -v /opt/napcat/config:/app/napcat/config \
  "$OK_REF"
sleep 20
echo "=== 登录方式二选一 ==="
echo "A) 终端扫码:  docker logs -f --tail 25 napcat   （用机器人QQ手机扫码）"
echo "B) WebUI:    WebUi Token 见 docker logs napcat | grep Token；本机 ssh -L 6099:127.0.0.1:6099 root@<IP> 后开 http://127.0.0.1:6099"
echo "=== 登录后配置反向 WS（对接弥娅）==="
echo "编辑 /opt/napcat/config/onebot11_${QQ}.json，在 network.websocketClients 加入："
echo '  {"enable":true,"url":"ws://127.0.0.1:8095/onebot/v11/ws","messagePostFormat":"array","reportSelfMessage":false,"token":"","debug":false,"heartInterval":30000,"reconnectInterval":5000}'
echo "然后 docker restart napcat；弥娅日志出现 'NapCat 已连接 (反向WS)' 即成功"
