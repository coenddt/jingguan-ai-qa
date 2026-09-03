# artwork-first-mile - 原始作品盘点入册 CLI（两段式：scan 盘点 → apply 归位）
# 用法: server-py/.venv/Scripts/python.exe .agents/skills/artwork-first-mile/first-mile.py --params-file <json>
# scan  参数: { "action": "scan", "src": "原始作品", "out": "tmp/first-mile-scan.json" }
# apply 参数: { "action": "apply", "src": "原始作品", "plan": "tmp/first-mile-plan.json", "out": "tmp/first-mile-report.json" }
# 纯本地文件操作：不连数据库、不起服务；原图只复制不动原件
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
NAME_RE = re.compile(r'^GYY-(\d+)-(\d+)')  # GYY-01-01...
SERIES_DIR_RE = re.compile(r'^(\d+)-(.+)$')  # 01-桥下河滩
BAD_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n]')


def parse_args():
    args = sys.argv[1:]
    if '--params-file' in args:
        params = json.loads(Path(args[args.index('--params-file') + 1]).read_text(encoding='utf-8'))
    else:
        raise SystemExit('必须用 --params-file 传参（见 cli-args-rules）')
    action = params.get('action')
    src = params.get('src', '原始作品')
    deliver = params.get('deliver', '投递文件夹')
    csv_path = params.get('csv', '作品清单/作品清单.csv')
    plan = params.get('plan', '')
    out = params.get('out', '')

    def resolve(p):
        return Path(p).resolve() if Path(p).is_absolute() else (ROOT / p).resolve()

    return {
        'action': action,
        'src': resolve(src),
        'deliver': resolve(deliver),
        'csv': resolve(csv_path),
        'plan': resolve(plan) if plan else None,
        'out': resolve(out) if out else None,
    }


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def long_edge(path: Path) -> int:
    try:
        from PIL import Image
        with Image.open(path) as img:
            return max(img.width, img.height)
    except Exception:
        return 0


def iter_images(base: Path):
    if not base.exists():
        return
    for p in sorted(base.rglob('*')):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            yield p


def read_csv_state(csv_path: Path):
    """读作品清单：occupiedNos + seriesRegistry。返回 (lines_with_eol, occupied, series)"""
    occupied = set()
    series = {}  # seq(str) -> name
    lines = []
    if csv_path.exists():
        raw = csv_path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        lines = text.splitlines()
        in_series_section = False
        for ln in lines:
            if ln.startswith('### 系列登记 ###'):
                in_series_section = True
                continue
            if not ln.strip() or ln.startswith('#'):
                continue
            cells = next(csv.reader([ln]))
            if in_series_section:
                if cells[0] == '系列号':
                    continue
                if cells and cells[0].isdigit():
                    series[cells[0].zfill(2)] = cells[1]
            else:
                if cells and re.match(r'^GYY-\d+-\d+$', cells[0]):
                    occupied.add(cells[0])
    return lines, occupied, series


def scan(args):
    src, deliver = args['src'], args['deliver']
    if not src.exists():
        raise SystemExit(f'原始作品目录不存在: {src}')

    _, occupied_csv, series_csv = read_csv_state(args['csv'])

    # 投递文件夹已有内容：内容 hash + 已占编号 + 系列目录
    deliver_hashes = {}
    for p in iter_images(deliver):
        deliver_hashes.setdefault(md5_file(p), str(p.relative_to(deliver)))
    occupied_files = set()
    series_dirs = {}
    if deliver.exists():
        for d in deliver.iterdir():
            m = SERIES_DIR_RE.match(d.name)
            if d.is_dir() and m:
                series_dirs[m.group(1).zfill(2)] = m.group(2)
                for p in d.iterdir():
                    mm = NAME_RE.match(p.stem)
                    if p.is_file() and mm:
                        occupied_files.add(f'GYY-{mm.group(1).zfill(2)}-{mm.group(2).zfill(2)}')

    items, seen, duplicates, low_res, already_delivered = [], {}, [], [], []
    for p in iter_images(src):
        h = md5_file(p)
        edge = long_edge(p)
        if h in seen:
            duplicates.append({'file': str(p.relative_to(src)), 'hash': h, 'sameAs': seen[h]})
            continue
        seen[h] = str(p.relative_to(src))
        if h in deliver_hashes:
            already_delivered.append({'file': str(p.relative_to(src)), 'hash': h, 'deliveredAs': deliver_hashes[h]})
            continue
        if 0 < edge < 2000:
            low_res.append({'file': str(p.relative_to(src)), 'longEdge': edge})
        items.append({'file': str(p.relative_to(src)), 'hash': h, 'longEdge': edge, 'bytes': p.stat().st_size})

    report = {
        'src': str(src),
        'newItems': items,
        'duplicatesInBatch': duplicates,
        'alreadyDelivered': already_delivered,
        'lowRes': low_res,
        'occupiedNos': sorted(occupied_csv | occupied_files),
        'seriesRegistry': {'csv': series_csv, 'deliverDirs': series_dirs},
        'hint': 'AI 查看图片后填 plan：{series:[{seq,name}], items:[{file,seq,no,title?}]}，然后执行 apply',
    }
    write_report(args['out'], report)
    print('[first-mile] scan 完成:', json.dumps({
        '新作品图': len(items), '批内重复': len(duplicates), '已投递过': len(already_delivered),
        '低清': len(low_res), '已占编号': len(report['occupiedNos']),
    }, ensure_ascii=False))
    print(f'[first-mile] 盘点报告: {args["out"]}')


def sanitize_title(t: str) -> str:
    return BAD_FILENAME_CHARS.sub('', (t or '').strip())


def apply(args):
    src, deliver = args['src'], args['deliver']
    if not args['plan'] or not args['plan'].exists():
        raise SystemExit('apply 需要 plan 文件（--params-file 的 plan 字段）')
    plan = json.loads(args['plan'].read_text(encoding='utf-8'))
    plan_series = plan.get('series') or []
    plan_items = plan.get('items') or []
    if not plan_items:
        raise SystemExit('plan.items 为空，无需执行')

    lines, occupied, series_registry = read_csv_state(args['csv'])
    # 投递文件夹现存编号也视为已占
    if deliver.exists():
        for d in deliver.iterdir():
            if d.is_dir():
                for p in d.iterdir():
                    mm = NAME_RE.match(p.stem)
                    if p.is_file() and mm:
                        occupied.add(f'GYY-{mm.group(1).zfill(2)}-{mm.group(2).zfill(2)}')

    # 系列目录名解析（plan.series + CSV 登记合并）；plan 新系列待写入 CSV 登记区
    _, _, csv_series_only = read_csv_state(args['csv'])
    new_series_rows = []
    for s in plan_series:
        seq = str(s['seq']).zfill(2)
        name = sanitize_title(s['name'])
        if seq not in series_registry:
            series_registry[seq] = name
        if seq not in csv_series_only and all(r[0] != seq for r in new_series_rows):
            new_series_rows.append((seq, name))

    copied, skipped = [], []
    csv_rows = []
    for it in plan_items:
        file_rel, seq, no, title = it['file'], it['seq'], it['no'], sanitize_title(it.get('title', ''))
        src_file = src / file_rel
        if not src_file.exists():
            skipped.append({'file': file_rel, 'reason': '源文件不存在'})
            continue
        seq2 = str(seq).zfill(2)
        no2 = str(no).zfill(2)
        artwork_no = f'GYY-{seq2}-{no2}'
        if artwork_no in occupied:
            skipped.append({'file': file_rel, 'reason': f'{artwork_no} 已被占用'})
            continue
        series_name = series_registry.get(seq2)
        if not series_name:
            skipped.append({'file': file_rel, 'reason': f'系列 {seq2} 未在 plan.series 或作品清单登记'})
            continue

        target_dir = deliver / f'{seq2}-{series_name}'
        target_name = f'{artwork_no}_{title}{src_file.suffix}' if title else f'{artwork_no}{src_file.suffix}'
        target = target_dir / target_name
        if target.exists():
            skipped.append({'file': file_rel, 'reason': f'目标已存在: {target_name}'})
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        # 原图只复制不移动
        target.write_bytes(src_file.read_bytes())
        occupied.add(artwork_no)
        copied.append({'from': file_rel, 'to': f'{seq2}-{series_name}/{target_name}'})

        # CSV 行（占位列：作品ID,系列号,系列名,标题,...,状态；标题为暂拟）
        buf = io.StringIO()
        csv.writer(buf).writerow([artwork_no, seq2, series_name, title or '（待命名）'] + [''] * 8 + ['待归档'])
        csv_rows.append(buf.getvalue().rstrip('\r\n'))

    # 写 CSV：数据行插到 "### 系列登记 ###" 之前；新系列追加到系列登记区末尾
    csv_added = 0
    if csv_rows or new_series_rows:
        out_lines = list(lines)
        marker_idx = next((i for i, ln in enumerate(out_lines) if ln.startswith('### 系列登记 ###')), None)
        if csv_rows:
            insert_at = marker_idx if marker_idx is not None else len(out_lines)
            while insert_at > 0 and not out_lines[insert_at - 1].strip():
                insert_at -= 1
            out_lines[insert_at:insert_at] = csv_rows
            csv_added = len(csv_rows)
            marker_idx = next((i for i, ln in enumerate(out_lines) if ln.startswith('### 系列登记 ###')), None)
        for seq2, name in new_series_rows:
            out_lines.append(f'{seq2},{name}')
        raw = args['csv'].read_bytes() if args['csv'].exists() else b''
        bom = raw.startswith(b'\xef\xbb\xbf')
        args['csv'].write_text('\n'.join(out_lines) + '\n', encoding='utf-8-sig' if bom else 'utf-8')

    report = {'copied': copied, 'skipped': skipped, 'csvAdded': csv_added, 'newSeries': [list(s) for s in new_series_rows]}
    write_report(args['out'], report)
    print('[first-mile] apply 完成:', json.dumps({
        '已归位': len(copied), '跳过': len(skipped), '清单新增行': csv_added, '新登记系列': len(new_series_rows),
    }, ensure_ascii=False))
    print(f'[first-mile] 归位报告: {args["out"]}')
    print('[first-mile] 下一步：gallery-ingest 扫描投递文件夹落库')


def write_report(out, report):
    if not out:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        a = parse_args()
        if a['action'] == 'scan':
            scan(a)
        elif a['action'] == 'apply':
            apply(a)
        else:
            raise SystemExit(f'未知 action: {a["action"]}（可选 scan/apply）')
    except SystemExit:
        raise
    except Exception as e:
        print(f'[first-mile] 失败: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
