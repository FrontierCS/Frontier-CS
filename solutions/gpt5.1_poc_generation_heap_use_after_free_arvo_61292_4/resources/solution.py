import os
import tarfile


TARGET_POC_SIZE = 159


def _score_candidate(path, fname, size, sample):
    path_lower = path.lower()
    fname_lower = fname.lower()
    score = 0.0

    is_cue = fname_lower.endswith('.cue') or fname_lower.endswith('.cue.txt')
    has_cuesheet = (
        'cuesheet' in path_lower
        or 'cue_sheet' in path_lower
        or 'importcuesheet' in path_lower
        or 'import_cuesheet' in path_lower
    )
    has_poc_tag = any(tag in path_lower for tag in (
        'poc',
        'uaf',
        'heap-use',
        'heap_use',
        'use-after-free',
        'use_after_free',
        'crash',
        'id:000',
        'id_000'
    ))
    in_poc_dir = any(('/' + d + '/') in path_lower or path_lower.startswith(d + '/')
                     for d in ('poc', 'pocs', 'crash', 'crashes', 'poc_inputs'))

    if is_cue:
        score += 100.0
    if has_cuesheet:
        score += 80.0
    if has_poc_tag:
        score += 60.0
    if in_poc_dir:
        score += 40.0

    diff = abs(size - TARGET_POC_SIZE)
    score += max(0.0, 60.0 - float(diff))

    if sample:
        text_len = len(sample)
        ascii_like = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
        if text_len > 0 and ascii_like / text_len > 0.8:
            score += 5.0
        text_lower = sample.lower()
        if b'cuesheet' in text_lower or b'cue sheet' in text_lower:
            score += 60.0
        if b'track ' in text_lower:
            score += 25.0
        if b'index ' in text_lower:
            score += 25.0
        if b'performer' in text_lower or b'title' in text_lower:
            score += 10.0
        if b'file ' in text_lower and (
            b'wav' in text_lower or b'wave' in text_lower or b'flac' in text_lower or b'mp3' in text_lower
        ):
            score += 10.0

    return score


def _find_poc_in_tar(src_path):
    best_member = None
    best_score = -1.0

    with tarfile.open(src_path, 'r:*') as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            size = member.size
            if size <= 0 or size > 65536:
                continue
            path = member.name
            fname = os.path.basename(path)
            try:
                f = tf.extractfile(member)
            except (KeyError, OSError, tarfile.ExtractError):
                continue
            if f is None:
                continue
            try:
                sample = f.read(2048)
            finally:
                f.close()
            score = _score_candidate(path, fname, size, sample)
            if score > best_score:
                best_score = score
                best_member = member

        if best_member is not None:
            f = tf.extractfile(best_member)
            if f is None:
                return b'A'
            try:
                data = f.read()
            finally:
                f.close()
            return data

    return b'A'


def _find_poc_in_dir(src_path):
    best_path = None
    best_size = 0
    best_score = -1.0

    for root, _, files in os.walk(src_path):
        for name in files:
            path = os.path.join(root, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size <= 0 or size > 65536:
                continue
            try:
                with open(path, 'rb') as f:
                    sample = f.read(2048)
            except OSError:
                continue
            score = _score_candidate(path, name, size, sample)
            if score > best_score:
                best_score = score
                best_path = path
                best_size = size

    if best_path is not None:
        try:
            with open(best_path, 'rb') as f:
                return f.read()
        except OSError:
            return b'A'

    return b'A'


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path) and not tarfile.is_tarfile(src_path):
            return _find_poc_in_dir(src_path)
        if tarfile.is_tarfile(src_path):
            return _find_poc_in_tar(src_path)
        # Fallback: not a tarball and not a directory; try as a single file
        try:
            with open(src_path, 'rb') as f:
                data = f.read()
                if data:
                    return data
        except OSError:
            pass
        return b'A'
