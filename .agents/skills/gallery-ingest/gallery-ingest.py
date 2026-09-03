# gallery-ingest - 投递文件夹扫描落库 CLI（Python 版）
# 用法: server-py/.venv/Scripts/python.exe gallery-ingest.py --params-file <json>
#       或 --dir <投递文件夹> --out <报告路径>
# 参数: { "dir": "投递文件夹", "out": "tmp/ingest-report.json" }
import asyncio
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = Path(__file__).resolve().parent

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
NAME_RE = re.compile(r'^GYY-(\d+)-(\d+)(?:_(.+))?$')  # GYY-01-01_标题


# ── 参数解析 ──
def parse_args():
    args = sys.argv[1:]
    dir_arg = None
    out = None

    def read_params_file(path):
        return json.loads(Path(path).read_text(encoding='utf-8'))

    if '--params-file' in args:
        params = read_params_file(args[args.index('--params-file') + 1])
        dir_arg = params.get('dir')
        out = params.get('out')
    if '--dir' in args:
        dir_arg = args[args.index('--dir') + 1]
    if '--out' in args:
        out = args[args.index('--out') + 1]
    if not dir_arg:
        dir_arg = '投递文件夹'
    if not out:
        out = 'tmp/ingest-report.json'
    return (ROOT / dir_arg).resolve(), (ROOT / out).resolve()


# ── .env 手工解析（skill 目录优先，fallback server-py/.env、server/.env） ──
def load_env():
    for p in (SKILL_DIR / '.env', ROOT / 'server-py' / '.env', ROOT / 'server' / '.env'):
        if not p.exists():
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            m = re.match(r'^\s*([A-Z_]+)\s*=\s*(.+?)\s*$', line)
            if m and not os.environ.get(m.group(1)):
                os.environ[m.group(1)] = m.group(2).strip('"\'')
        break


# ── 图片处理（Pillow）：original 原样 + watermark(1280)/thumb(480) 压缩 ──
def process_image(src: Path, ext: str):
    from PIL import Image, ImageOps

    def to_jpeg_bytes(img, width, quality):
        if img.width > width:
            ratio = width / img.width
            img = img.resize((width, round(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert('RGB').save(buf, 'JPEG', quality=quality)
        return buf.getvalue()

    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        long_edge = max(img.width, img.height)
        buf_watermark = to_jpeg_bytes(img, 1280, 80)
        buf_thumb = to_jpeg_bytes(img, 480, 75)

    buf_original = src.read_bytes()
    return buf_original, buf_watermark, buf_thumb, long_edge


def compress_scene(src: Path) -> bytes:
    """实景照压缩：仅详情页展示，压为长边 1280 的 JPEG，避免原图（数 MB）直出拖慢加载"""
    from PIL import Image, ImageOps

    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        if img.width > 1280:
            ratio = 1280 / img.width
            img = img.resize((1280, round(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert('RGB').save(buf, 'JPEG', quality=80)
        return buf.getvalue()


def parse_series_dir_name(name: str):
    m = re.match(r'^(\d+)-(.+)$', name)
    if not m:
        return None
    return {'seq': int(m.group(1)), 'name': m.group(2)}


async def main():
    from pymongo import AsyncMongoClient

    sys.path.insert(0, str(ROOT / 'server-py'))
    from db.store import init, store  # noqa: E402  （导入即注册全部 schema）

    from utils.file_store import save_image  # noqa: E402

    dir_path, out = parse_args()
    load_env()
    if not dir_path.exists():
        print(f'[ingest] 投递文件夹不存在: {dir_path}', file=sys.stderr)
        sys.exit(1)

    uri = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/family-gallery'
    client = AsyncMongoClient(uri)
    db = client.get_default_database()
    if db is None:
        print('[ingest] MONGODB_URI 未包含库名（应为 mongodb://host/family-gallery）', file=sys.stderr)
        sys.exit(1)
    await init(db)

    report = {
        'scannedSeries': 0, 'totalImages': 0, 'inserted': 0, 'skippedDuplicate': 0,
        'sceneAttached': 0,
        'missing': {'noText': [], 'pendingTitle': [], 'lowRes': [], 'docx': [], 'noArtwork': []},
        'series': [],
    }

    series_dirs = sorted(d for d in dir_path.iterdir() if d.is_dir())
    for sd in series_dirs:
        parsed = parse_series_dir_name(sd.name)
        if not parsed:
            report['missing']['pendingTitle'].append(
                f'[系列目录名不规范] {sd.name}（应为 "系列号-系列名"，如 01-桥下河滩）')
            continue
        report['scannedSeries'] += 1

        # Series upsert（按 seq）
        series = await store.query_one('Series($condition:@c0) { _id, seq, name }', {'c0': {'seq': parsed['seq']}})
        if not series:
            series = await store.insert('Series', {'seq': parsed['seq'], 'name': parsed['name']})
        elif series['name'] != parsed['name']:
            await store.update('Series', {'_id': series['_id']}, {'name': parsed['name']})

        # 扫描作品文件
        files = [f.name for f in sd.iterdir() if f.is_file()]
        images = [f for f in files if Path(f).suffix.lower() in IMG_EXTS]
        report['totalImages'] += len(images)

        for img in images:
            base = Path(img).stem
            ext = Path(img).suffix.lower()
            is_scene = base.endswith('_实景')
            stem = base[:-3] if is_scene else base
            m = NAME_RE.match(stem)
            artwork_no = f"GYY-{m.group(1)}-{m.group(2)}" if m else ''
            title_from_name = m.group(3) if m and m.group(3) and not is_scene else ''
            src_abs = sd / img
            rel_source = f'{sd.name}/{img}'

            # 实景照：挂到对应作品的 images.scene，不单独成作品
            if is_scene:
                if not artwork_no:
                    report['missing']['pendingTitle'].append(
                        f'{sd.name}/{img}（实景照命名不符 GYY-系列-序号_实景）')
                    continue
                art = await store.query_one('Artwork($condition:@c0) { _id, images }', {'c0': {'artworkNo': artwork_no}})
                if not art:
                    report['missing']['noArtwork'].append(
                        f'{sd.name}/{img}（找不到对应作品 {artwork_no}，请先投递该作品图）')
                    continue
                if art.get('images') and art['images'].get('scene'):
                    report['skippedDuplicate'] += 1
                    continue
                scene_url = save_image('scene', compress_scene(src_abs), '.jpg')
                await store.update('Artwork', {'_id': art['_id']}, {'images.scene': scene_url})
                report['sceneAttached'] += 1
                continue

            # 同名文字想法（txt 原样照录；docx 提示转存）
            txt_path = sd / f'{stem}.txt'
            story_text = txt_path.read_text(encoding='utf-8').strip() if txt_path.exists() else ''
            if not txt_path.exists() and f'{stem}.docx' in files:
                report['missing']['docx'].append(f'{sd.name}/{stem}.docx（docx 暂不解析，请另存为同名 txt）')

            # 去重：有编号按编号；无编号按投递源文件路径
            dedup_cond = {'artworkNo': artwork_no} if artwork_no else {'sourceFiles.image': rel_source}
            if await store.exists('Artwork', dedup_cond):
                report['skippedDuplicate'] += 1
                continue

            # 图片处理：original 原样拷贝 + watermark/thumb 压缩
            buf_original, buf_watermark, buf_thumb, long_edge = process_image(src_abs, ext)
            if 0 < long_edge < 2000:
                report['missing']['lowRes'].append(f'{sd.name}/{img}（长边 {long_edge}px < 2000，建议重拍或扫描）')
            images2 = {
                'original': save_image('original', buf_original, ext),
                'watermark': save_image('watermark', buf_watermark, '.jpg'),
                'thumb': save_image('thumb', buf_thumb, '.jpg'),
            }

            # 落库
            doc = {
                'artworkNo': artwork_no,
                'title': title_from_name,
                'seriesId': series['_id'],
                'storyText': story_text,
                'storySource': 'self',
                'status': 'pending_title' if not artwork_no or not title_from_name else 'ingested',
                'images': images2,
                'sourceFiles': {
                    'image': rel_source,
                    'text': f'{sd.name}/{stem}.txt' if txt_path.exists() else '',
                },
            }
            await store.insert('Artwork', doc)
            report['inserted'] += 1
            if doc['status'] == 'pending_title':
                report['missing']['pendingTitle'].append(f'{sd.name}/{img}（命名不符 GYY-系列-序号_标题）')
            if not story_text:
                report['missing']['noText'].append(f'{sd.name}/{stem}（缺同名 txt 文字想法）')

    await client.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('[ingest] 完成:', json.dumps({
        '系列数': report['scannedSeries'],
        '图片数': report['totalImages'],
        '入库': report['inserted'],
        '重复跳过': report['skippedDuplicate'],
        '实景挂载': report['sceneAttached'],
        '待命名': len(report['missing']['pendingTitle']),
        '缺文字': len(report['missing']['noText']),
        '低清': len(report['missing']['lowRes']),
        'docx待转': len(report['missing']['docx']),
        '实景无对应作品': len(report['missing']['noArtwork']),
    }, ensure_ascii=False))
    print(f'[ingest] 检验报告: {out}')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        asyncio.run(main())
    except Exception as e:
        print(f'[ingest] 失败: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
