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
