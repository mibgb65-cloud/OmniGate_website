#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
ENV_EXAMPLE="${REPO_ROOT}/.env.example"

source "${SCRIPT_DIR}/lib/common.sh"

main() {
  ensure_linux
  ensure_command git
  ensure_command grep

  ensure_docker

  cd "${REPO_ROOT}"

  ensure_env_file
  load_env
  validate_env_secrets
  validate_host_nginx_settings

  info "校验 Docker Compose 配置。"
  compose_cmd config >/dev/null

  info "构建镜像。"
  compose_cmd build --pull

  info "启动容器。"
  compose_cmd up -d

  configure_host_nginx_if_enabled

  info "当前服务状态："
  compose_cmd ps

  info "部署完成。"
  info "查看日志可执行: docker compose logs -f backend"
}

main "$@"
