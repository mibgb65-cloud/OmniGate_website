#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

source "${SCRIPT_DIR}/lib/common.sh"

ensure_git_repo() {
  command -v git >/dev/null 2>&1 || fail "未检测到 git。"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "当前目录不是 Git 仓库。"
}

show_git_context() {
  local branch commit

  branch="$(git rev-parse --abbrev-ref HEAD)"
  commit="$(git rev-parse --short HEAD)"
  info "当前分支: ${branch}"
  info "当前代码版本: ${commit}"

  if [[ -n "$(git status --porcelain)" ]]; then
    warn "检测到未提交的本地改动。git pull 可能失败，或你的本地改动会影响部署结果。"
  fi
}

git_update() {
  info "获取远端最新代码。"
  git fetch --all --prune

  info "拉取当前分支最新提交。"
  git pull --ff-only
}

main() {
  ensure_linux
  ensure_docker_access

  cd "${REPO_ROOT}"

  [[ -f "${ENV_FILE}" ]] || fail "未找到 ${ENV_FILE}，请先执行部署脚本。"
  load_env
  validate_host_nginx_settings

  ensure_git_repo
  show_git_context
  git_update

  info "校验 Docker Compose 配置。"
  compose_cmd config >/dev/null

  info "重建应用镜像。"
  compose_cmd build frontend backend worker

  info "更新应用容器。"
  compose_cmd up -d frontend backend worker

  configure_host_nginx_if_enabled

  info "当前服务状态："
  compose_cmd ps

  info "更新完成。"
}

main "$@"
