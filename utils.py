import os
import re
import csv
import copy
import glob
import shutil
import warnings

import numpy as np


def make_dir(dir_path, *optional, **kwargs):
    safe = kwargs.get('safe', True)
    strict = kwargs.get('strict', False)

    dir_path = os.path.join(dir_path, *optional)
    try:
        os.makedirs(dir_path)
    except Exception, e:
        if os.path.exists(dir_path) and not safe:
            del_dir(dir_path, safe, strict)
        elif os.path.exists(dir_path) and safe and strict:
            raise e

    return dir_path


def del_dir(dir_path, *optional):
    dir_path = os.path.join(dir_path, *optional)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


def copy_dir(src_dir, dest_dir, safe=True, strict=True):
    if not os.path.exists(src_dir) and not strict:
        warnings.warn('Source directory %s does not exist.' % src_dir)
        return
    if os.path.exists(dest_dir) and not safe:
        del_dir(dest_dir)
    if not os.path.exists(os.path.split(dest_dir)[0]):
        make_dir(os.path.split(dest_dir)[0])
    shutil.copytree(src_dir, dest_dir)


def copy_file(src_file, dest_file, safe=True, strict=True):
    if not os.path.exists(src_file) and not strict:
        warnings.warn('Source file %s does not exist.' % src_file)
        return
    if os.path.exists(dest_file) and safe:
        raise Exception('Destination file %s already exists.' % dest_file)
    shutil.copyfile(src_file, dest_file)


def globing(data_dir, *args, **kwargs):
    if kwargs.get('generator', False):
        return glob.iglob(os.path.join(data_dir, *args))
    else:
        return sorted(glob.glob(os.path.join(data_dir, *args)))


def save_table(dict_obj, file_name, merge=False):
    if dict_obj is None:
        return
    mode = 'wb' if not merge else 'ab'
    with open(file_name, mode) as f:
        writer = csv.writer(f, delimiter=' ', quotechar='"')
        for key in sorted(dict_obj.keys()):
            if isinstance(dict_obj[key], list):
                writer.writerow([key] + dict_obj[key])
            else:
                writer.writerow([key, dict_obj[key]])


def get_table(file_name):
    if not os.path.exists(file_name):
        return dict()
    with open(file_name) as f:
        reader = csv.reader(f, delimiter=' ', quotechar='"')
        keys = []
        values = []
        for row in reader:
            keys.append(row[0])
            values.append(row[1])
    return dict(zip(keys, values))


def safe_name(name):
    name = re.sub('[/ \'\"!*?;(){}.]', '_', name)
    return re.sub('_+', '_', name)


def check_path(path):
    path = str(path)
    path = path.strip()
    # test separator
    if '\\' in path:
        parts = path.split('\\')
        if parts[0] == '' or ':' in parts[0]:
            parts = parts[1:]
        return os.path.join(*parts)
    # SPM8 adds the volume number at the end of the path
    if re.match('.*,\d+', path):
        return path.split(',')[0]
    return path


def check_paths(paths):
    return [check_path(path) for path in paths]


def contrasts_spec(contrasts, sessions_spec):
    new_contrasts = {}
    for k in contrasts:
        contrast = copy.deepcopy(contrasts[k])
        for i, session_spec in enumerate(sessions_spec):
            con = np.array(contrast, copy=True)
            selection = np.ones(len(con), dtype='bool')
            selection[session_spec] = False
            con[selection] = 0

            if not k.startswith('task'):
                new_k = 'task001_%s' % k
            else:
                new_k = k
            task_id, con_name = new_k.split('_', 1)
            new_k = '%s_run%03i_%s' % (task_id, i + 1, con_name)
            new_contrasts[new_k] = con.tolist()
    return new_contrasts


def add_baseline_regressor(contrasts):
    new_contrasts = {}
    for k in contrasts:
        if 'vs_baseline' in k:
            key = k.split('_vs_baseline')[0]
        else:
            key = k
        for c in contrasts[k]:
            if c is not None:
                c = copy.deepcopy(c)
                c.append(0)
            new_contrasts.setdefault(key, []).append(c)

    baseline_contrasts = {}
    for k in new_contrasts:
        task_id, run_id, _ = ('%s_' % k).split('_', 2)
        if not run_id.startswith('run'):
            key = '%s_baseline' % task_id
        else:
            key = '%s_%s_baseline' % (task_id, run_id)
        baseline_contrasts[key] = []

        for c in new_contrasts[k]:
            if c is not None and not np.all(np.array(c) == 0):
                c = [0] * len(c)
                c[-1] = 1
            baseline_contrasts[key].append(c)

    new_contrasts.update(baseline_contrasts)
    return new_contrasts
