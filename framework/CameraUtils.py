# Copyright 2025 Keen Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import shlex
import subprocess

from framework.Logger import logger


def set_control(device_idx, ctrl_name, ctrl_value):
    cmdline = f'v4l2-ctl --device /dev/video{device_idx} --set-ctrl={ctrl_name}={ctrl_value}'
    cmd_list = shlex.split(cmdline, posix=False)
    process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = process.communicate()
    output = output.decode('utf-8')
    status = process.returncode
    if status:
        logger.warning(
            f"set_control: Failed to set {ctrl_name}={ctrl_value} for device {device_idx}. Return code={status}."
        )


def parse_control(line):
    parts = line.split(':')
    if len(parts) < 2:
        return None

    name_part = parts[0].strip()
    control_name = name_part.split()[0]
    control_data = parts[1].strip()
    data = control_data.split()

    control = {'name': control_name}

    for d in data:
        if '=' in d:
            key, value = d.split('=')
            try:
                value = int(value)
            except ValueError:
                pass
            control[key] = value
        elif '(' in d:  # description is optional
            control['desc'] = d.strip('()')

    return control


def get_controls(device_idx):
    ctrls_dict = {}
    cmd_list = shlex.split(f'v4l2-ctl -d /dev/video{device_idx} --list-ctrls', posix=False)
    process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = process.communicate()
    output = output.decode('utf-8')
    status = process.returncode
    if status:
        logger.warning(f"get_controls: list-ctrls for device {device_idx} failed. Return code={status}.")
    else:
        for line in output.splitlines():
            ctrl = parse_control(line.strip())
            if ctrl:
                ctrls_dict[ctrl['name']] = ctrl
    return ctrls_dict


def get_index_from_model_name(model_name):
    cmd_list = shlex.split('v4l2-ctl --list-devices', posix=False)
    process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = process.communicate()
    output = output.decode('utf-8')
    status = process.returncode  # ignore unless parsing fails

    lines = output.splitlines()
    if not lines:
        if status:
            logger.warning(f"get_index_from_model_name: empty output ({status})")
        else:
            logger.warning("get_index_from_model_name: empty output")
        return -1

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if not line.startswith((" ", "\t")):
            header = line.strip()
            if model_name.lower() in header.lower():
                i += 1
                # find /dev/video* lines
                while i < len(lines) and lines[i].startswith((" ", "\t")):
                    device_line = lines[i].strip()
                    match = re.search(r'/dev/video(\d+)', device_line)
                    if match:
                        device_idx = int(match.group(1))
                        logger.debug(f"Found {model_name} at {device_line} idx {device_idx}")
                        return device_idx
                    i += 1
                logger.warning(f"get_index_from_model_name: matched header '{header}' but found no /dev/video* entries")
                return -1
        i += 1

    logger.warning(f"get_index_from_model_name: No device header matched '{model_name}'")
    return -1
