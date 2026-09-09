#!/usr/bin/env python3
"""pypi-publisher — PyPI 包发布与版本管理 CLI

参数一律从 stdin 读单个 JSON 对象：
  {"cmd": "build",   "pkg_dir": "packages/mongo-store-py"}
  {"cmd": "publish", "pkg_dir": "packages/mongo-store-py"}
  {"cmd": "check",   "package": "mongo-store"}
  {"cmd": "bump",    "pkg_dir": "packages/mongo-store-py", "part": "patch|minor|major"}
  {"cmd": "release", "pkg_dir": "packages/mongo-store-py", "part": "patch"}   # bump+build+publish 一条龙

token 从本脚本同目录 .env 的 PYPI_TOKEN 读取，严禁写入代码/文档/命令行。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
PYPI_UPLOAD_URL = 'https://upload.pypi.org/legacy/'
PYPI_JSON_API = 'https://pypi.org/pypi/{package}/json'


def load_token() -> str:
    env_file = SKILL_DIR / '.env'
    if not env_file.exists():
        sys.exit(f'[pypi-publisher] 缺少 {env_file}，无法读取 PYPI_TOKEN')
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('PYPI_TOKEN='):
            return line.split('=', 1)[1].strip()
    sys.exit('[pypi-publisher] .env 中未找到 PYPI_TOKEN')


def read_stdin_json() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit('[pypi-publisher] stdin 为空：请传入 JSON 参数，如 {"cmd":"check","package":"mongo-store"}')
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f'[pypi-publisher] stdin JSON 解析失败: {e}\n原文: {raw[:200]}')


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print(f'>>> {" ".join(cmd)}')
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(f'[pypi-publisher] 命令失败(exit {r.returncode}): {cmd[0]}')
    return r


def read_version(pyproject: Path) -> str:
    text = pyproject.read_text(encoding='utf-8')
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        sys.exit(f'[pypi-publisher] {pyproject} 中未找到 version 字段')
    return m.group(1)


def write_version(pyproject: Path, new_version: str) -> None:
    text = pyproject.read_text(encoding='utf-8')
    text = re.sub(r'^(version\s*=\s*)["\'][^"\']+["\']',
                  lambda m: f'{m.group(1)}"{new_version}"', text, count=1, flags=re.M)
    pyproject.write_text(text, encoding='utf-8')


def bump_version(version: str, part: str) -> str:
    nums = [int(x) for x in version.split('.')]
    while len(nums) < 3:
        nums.append(0)
    idx = {'major': 0, 'minor': 1, 'patch': 2}.get(part)
    if idx is None:
        sys.exit(f'[pypi-publisher] part 仅支持 patch|minor|major，收到: {part}')
    nums[idx] += 1
    for i in range(idx + 1, 3):
        nums[i] = 0
    return '.'.join(str(n) for n in nums)


def cmd_build(pkg_dir: Path) -> None:
    run([sys.executable, '-m', 'pip', 'show', 'build'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run([sys.executable, '-m', 'build', '--wheel', str(pkg_dir)])
    dist = pkg_dir / 'dist'
    wheels = sorted(dist.glob('*.whl'))
    print(f'[pypi-publisher] 构建完成: {wheels[-1] if wheels else "（无产物？）"}')


def cmd_publish(pkg_dir: Path, token: str) -> None:
    dist = pkg_dir / 'dist'
    wheels = sorted(dist.glob('*.whl'))
    if not wheels:
        sys.exit(f'[pypi-publisher] {dist} 下没有 .whl，先执行 build')
    import os
    env = os.environ.copy()
    env['TWINE_USERNAME'] = '__token__'
    env['TWINE_PASSWORD'] = token          # token 走环境变量，不进命令行/日志
    run([sys.executable, '-m', 'twine', 'upload', '--non-interactive',
         '--repository-url', PYPI_UPLOAD_URL, str(wheels[-1])], env=env)
    print(f'[pypi-publisher] 已发布: {wheels[-1].name}（PyPI 审核同步约 1~2 分钟）')


def cmd_check(package: str) -> None:
    import urllib.error
    import urllib.request
    url = PYPI_JSON_API.format(package=package)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.load(resp)
        versions = sorted(data['releases'].keys())
        print(f'[pypi-publisher] {package} 已存在于 PyPI，版本: {versions}')
        print(f'[pypi-publisher] 最新: {data["info"]["version"]}')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f'[pypi-publisher] {package} 未被占用（PyPI 404）——包名可用')
        else:
            print(f'[pypi-publisher] {package} 查询失败(HTTP {e.code})')
    except Exception as e:  # noqa: BLE001
        print(f'[pypi-publisher] {package} 查询失败({e.__class__.__name__})——404 视为包名可用')


def main() -> None:
    args = read_stdin_json()
    cmd = args.get('cmd')
    token = load_token()

    if cmd == 'build':
        cmd_build(Path(args['pkg_dir']))
    elif cmd == 'publish':
        cmd_publish(Path(args['pkg_dir']), token)
    elif cmd == 'bump':
        pkg_dir = Path(args['pkg_dir'])
        pyproject = pkg_dir / 'pyproject.toml'
        old = read_version(pyproject)
        new = bump_version(old, args.get('part', 'patch'))
        write_version(pyproject, new)
        print(f'[pypi-publisher] 版本 {old} → {new}')
    elif cmd == 'check':
        cmd_check(args['package'])
    elif cmd == 'release':
        pkg_dir = Path(args['pkg_dir'])
        pyproject = pkg_dir / 'pyproject.toml'
        old = read_version(pyproject)
        new = bump_version(old, args.get('part', 'patch'))
        write_version(pyproject, new)
        print(f'[pypi-publisher] 版本 {old} → {new}')
        cmd_build(pkg_dir)
        cmd_publish(pkg_dir, token)
    else:
        sys.exit(f'[pypi-publisher] 未知 cmd: {cmd}（支持 build/publish/check/bump/release）')


if __name__ == '__main__':
    main()
