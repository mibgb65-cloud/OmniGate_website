#!/usr/bin/env bash

USE_SUDO=0

info() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi

  fail "当前操作需要 root 或 sudo 权限。"
}

docker_cmd() {
  if [[ "${USE_SUDO}" -eq 1 ]]; then
    sudo docker "$@"
  else
    docker "$@"
  fi
}

compose_cmd() {
  if docker_cmd compose version >/dev/null 2>&1; then
    docker_cmd compose "$@"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    if [[ "${USE_SUDO}" -eq 1 ]]; then
      sudo docker-compose "$@"
    else
      docker-compose "$@"
    fi
    return
  fi

  fail "未检测到 Docker Compose。"
}

ensure_linux() {
  [[ "$(uname -s)" == "Linux" ]] || fail "该脚本仅适用于 Linux。"
}

ensure_command() {
  command -v "$1" >/dev/null 2>&1 || fail "缺少命令: $1"
}

install_docker_with_official_script() {
  if command -v curl >/dev/null 2>&1; then
    run_as_root sh -c 'curl -fsSL https://get.docker.com | sh'
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    run_as_root sh -c 'wget -qO- https://get.docker.com | sh'
    return
  fi

  fail "未检测到 curl 或 wget，无法自动安装 Docker。"
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    info "未检测到 Docker，尝试使用官方安装脚本安装。"
    install_docker_with_official_script
  fi

  if command -v systemctl >/dev/null 2>&1; then
    if ! run_as_root systemctl is-active --quiet docker; then
      info "启动 Docker 服务。"
      run_as_root systemctl enable --now docker
    fi
  fi

  if docker info >/dev/null 2>&1; then
    USE_SUDO=0
    return
  fi

  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    USE_SUDO=1
    warn "当前用户没有直接访问 Docker 的权限，本次将通过 sudo 执行。"
    warn "如果你希望后续免 sudo，执行: sudo usermod -aG docker \$USER && newgrp docker"
    return
  fi

  fail "Docker 已安装但当前用户无法访问 Docker daemon。"
}

ensure_docker_access() {
  command -v docker >/dev/null 2>&1 || fail "未检测到 Docker。请先执行部署脚本。"

  if docker info >/dev/null 2>&1; then
    USE_SUDO=0
    return
  fi

  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    USE_SUDO=1
    warn "当前用户没有直接访问 Docker 的权限，本次将通过 sudo 执行。"
    return
  fi

  fail "当前用户无法访问 Docker daemon。"
}

ensure_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    return
  fi

  [[ -f "${ENV_EXAMPLE}" ]] || fail "未找到 ${ENV_EXAMPLE}"
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  warn "已创建 ${ENV_FILE}，请先修改其中的密码和密钥后再重新运行脚本。"
  exit 1
}

load_env() {
  local line key value

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"

    [[ -z "${line//[[:space:]]/}" ]] && continue
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue

    [[ "${line}" == export\ * ]] && line="${line#export }"
    [[ "${line}" == *=* ]] || continue

    key="${line%%=*}"
    value="${line#*=}"

    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    if [[ "${value}" =~ ^\".*\"$ ]] || [[ "${value}" =~ ^\'.*\'$ ]]; then
      value="${value:1:-1}"
    fi

    export "${key}=${value}"
  done < "${ENV_FILE}"

  : "${FRONTEND_BIND_HOST:=0.0.0.0}"
  : "${FRONTEND_PORT:=80}"
  : "${FRONTEND_API_BASE_URL:=/}"
  : "${FRONTEND_TASK_LOG_WS_URL:=/ws/task-log}"
  : "${HOST_NGINX_ENABLE:=false}"
  : "${HOST_NGINX_SERVER_NAME:=_}"
  : "${HOST_NGINX_CONFIG_PATH:=/etc/nginx/conf.d/omnigate.conf}"
  : "${HOST_NGINX_CLIENT_MAX_BODY_SIZE:=20m}"
}

validate_env_secrets() {
  if grep -Eq '^POSTGRES_PASSWORD=ChangeThisPostgresPassword$' "${ENV_FILE}"; then
    fail ".env 中仍在使用默认 POSTGRES_PASSWORD，请修改后再部署。"
  fi

  if grep -Eq '^OMNIGATE_JWT_SECRET=ChangeThisJwtSecretAtLeast32Chars$' "${ENV_FILE}"; then
    fail ".env 中仍在使用默认 OMNIGATE_JWT_SECRET，请修改后再部署。"
  fi
}

validate_numeric_range() {
  local name="$1"
  local value="$2"
  local min_value="$3"
  local max_value="$4"

  [[ "${value}" =~ ^[0-9]+$ ]] || fail "${name} 必须是数字，当前值: ${value}"
  (( value >= min_value && value <= max_value )) || fail "${name} 必须在 ${min_value}-${max_value} 之间，当前值: ${value}"
}

validate_env_runtime_settings() {
  [[ -n "${POSTGRES_DB:-}" ]] || fail "POSTGRES_DB 不能为空。"
  [[ -n "${POSTGRES_USER:-}" ]] || fail "POSTGRES_USER 不能为空。"
  [[ -n "${POSTGRES_PASSWORD:-}" ]] || fail "POSTGRES_PASSWORD 不能为空。"
  [[ -n "${OMNIGATE_JWT_SECRET:-}" ]] || fail "OMNIGATE_JWT_SECRET 不能为空。"

  (( ${#OMNIGATE_JWT_SECRET} >= 32 )) || fail "OMNIGATE_JWT_SECRET 长度至少需要 32 位。"

  validate_numeric_range "FRONTEND_PORT" "${FRONTEND_PORT}" 1 65535
  validate_numeric_range "REDIS_DATABASE" "${REDIS_DATABASE:-0}" 0 99
  validate_numeric_range "WORKER_CONCURRENCY" "${WORKER_CONCURRENCY:-3}" 1 64
  validate_numeric_range "WORKER_MAX_CONCURRENCY_LIMIT" "${WORKER_MAX_CONCURRENCY_LIMIT:-10}" 1 256

  if [[ "${WORKER_CONCURRENCY:-3}" -gt "${WORKER_MAX_CONCURRENCY_LIMIT:-10}" ]]; then
    fail "WORKER_CONCURRENCY 不能大于 WORKER_MAX_CONCURRENCY_LIMIT。"
  fi

  case "${FRONTEND_API_BASE_URL}" in
    ""|"/"|"/api")
      ;;
    http://*|https://*|/*)
      warn "FRONTEND_API_BASE_URL=${FRONTEND_API_BASE_URL} 不是推荐值。通常建议使用 / 或 /api。"
      ;;
    *)
      fail "FRONTEND_API_BASE_URL 必须为空、/、/api，或以 /、http://、https:// 开头。当前值: ${FRONTEND_API_BASE_URL}"
      ;;
  esac

  case "${FRONTEND_TASK_LOG_WS_URL}" in
    ""|"/ws/task-log"|ws://*|wss://*|/*)
      ;;
    *)
      warn "FRONTEND_TASK_LOG_WS_URL=${FRONTEND_TASK_LOG_WS_URL} 看起来不是常见格式，通常建议留空、/ws/task-log、ws://... 或 wss://..."
      ;;
  esac

  if [[ "${FRONTEND_API_BASE_URL}" == "/api" ]]; then
    warn "FRONTEND_API_BASE_URL=/api 在当前前端版本仍兼容，但推荐改为 /，可减少旧构建产物出现 /api/api 路径的风险。"
  fi
}

is_true() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

validate_host_nginx_settings() {
  if ! is_true "${HOST_NGINX_ENABLE}"; then
    return
  fi

  [[ "${FRONTEND_PORT}" != "80" ]] || fail "启用宿主机 Nginx 时，FRONTEND_PORT 不能为 80。请改成例如 8088。"

  case "${FRONTEND_BIND_HOST}" in
    127.0.0.1|localhost|::1)
      ;;
    *)
      fail "启用宿主机 Nginx 时，FRONTEND_BIND_HOST 应设为 127.0.0.1，避免前端容器直接暴露公网。"
      ;;
  esac
}

configure_selinux_for_nginx_if_needed() {
  if ! is_true "${HOST_NGINX_ENABLE}"; then
    return
  fi

  if ! command -v getenforce >/dev/null 2>&1; then
    return
  fi

  if [[ "$(getenforce)" != "Enforcing" ]]; then
    return
  fi

  if ! command -v setsebool >/dev/null 2>&1; then
    warn "检测到 SELinux 为 Enforcing，但未找到 setsebool。若宿主机 Nginx 无法反代到容器，请手动执行: setsebool -P httpd_can_network_connect 1"
    return
  fi

  info "检测到 SELinux 为 Enforcing，允许宿主机 Nginx 发起网络连接。"
  run_as_root setsebool -P httpd_can_network_connect 1
}

install_nginx() {
  if command -v nginx >/dev/null 2>&1; then
    return
  fi

  info "未检测到宿主机 Nginx，开始安装。"

  if command -v apt-get >/dev/null 2>&1; then
    run_as_root apt-get update
    run_as_root apt-get install -y nginx
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    run_as_root dnf install -y nginx
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    run_as_root yum install -y nginx
    return
  fi

  if command -v zypper >/dev/null 2>&1; then
    run_as_root zypper --non-interactive install nginx
    return
  fi

  fail "未检测到支持的包管理器，无法自动安装 Nginx。"
}

write_host_nginx_config() {
  local target_dir target_file temp_file

  target_file="${HOST_NGINX_CONFIG_PATH}"
  target_dir="$(dirname "${target_file}")"
  temp_file="$(mktemp)"

  cat > "${temp_file}" <<EOF
map \$http_upgrade \$connection_upgrade {
  default upgrade;
  '' close;
}

server {
  listen 80;
  server_name ${HOST_NGINX_SERVER_NAME};

  client_max_body_size ${HOST_NGINX_CLIENT_MAX_BODY_SIZE};

  location / {
    proxy_pass http://127.0.0.1:${FRONTEND_PORT};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection \$connection_upgrade;
    proxy_read_timeout 3600;
  }
}
EOF

  run_as_root mkdir -p "${target_dir}"
  run_as_root cp "${temp_file}" "${target_file}"
  rm -f "${temp_file}"
}

configure_host_nginx_if_enabled() {
  if ! is_true "${HOST_NGINX_ENABLE}"; then
    return
  fi

  info "配置宿主机 Nginx 反向代理。"

  install_nginx
  write_host_nginx_config
  configure_selinux_for_nginx_if_needed

  run_as_root nginx -t

  if command -v systemctl >/dev/null 2>&1; then
    run_as_root systemctl enable --now nginx
    run_as_root systemctl reload nginx
  else
    run_as_root nginx -s reload || run_as_root nginx
  fi

  info "宿主机 Nginx 配置完成: ${HOST_NGINX_CONFIG_PATH}"
  info "当前代理目标: http://127.0.0.1:${FRONTEND_PORT}"
}

show_runtime_summary() {
  info "访问提示："

  if is_true "${HOST_NGINX_ENABLE}"; then
    if [[ "${HOST_NGINX_SERVER_NAME}" != "_" ]]; then
      info "前端入口: http://${HOST_NGINX_SERVER_NAME}/"
    else
      info "前端入口: http://<服务器IP>/"
    fi
  else
    case "${FRONTEND_BIND_HOST}" in
      127.0.0.1|localhost|::1)
        info "前端入口仅本机可访问: http://${FRONTEND_BIND_HOST}:${FRONTEND_PORT}/"
        ;;
      *)
        if [[ "${FRONTEND_PORT}" == "80" ]]; then
          info "前端入口: http://<服务器IP>/"
        else
          info "前端入口: http://<服务器IP>:${FRONTEND_PORT}/"
        fi
        ;;
    esac
  fi

  info "常用日志命令: docker compose logs -f frontend backend worker"
  info "常用排查命令: docker compose ps"
  warn "如果页面无法访问，优先检查安全组/防火墙、docker compose ps，以及 OPERATIONS_TROUBLESHOOTING.md"
}
