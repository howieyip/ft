import os
import re

total_bull = 0
total_bear = 0

# 求和
def sum(name, line):
    global total_bull, total_bear
    bull_re = re.search(r'today bull: (-?\d+\.?\d*)', line)
    bear_re = re.search(r'today bear: (-?\d+\.?\d*)', line)
    if bull_re:
        bull_number = float(bull_re.group(1))
        total_bull += bull_number
    if bear_re:
        bear_number = float(bear_re.group(1))
        total_bear += bear_number
    if bull_number > 0 or bear_number > 0:
        print(f'{name}: {line}', end='')


# 遍历指定目录下的所有log文件
def stat(dir_name):
    for file in sorted(os.scandir(dir_name), key=lambda x: x.stat().st_mtime):
        if file.name.endswith('.log'):
            # 打开文件并逐行从后往前读取
            with open(file, 'r') as f:
                lines = f.readlines()[::-1]
                for line in lines:
                    # 如果找到包含的字符串，就停止并记录下文件名和行内容
                    if 'today bear' in line:
                        sum(file.name, line)
                        break

base_path = '/data/release/ft'
stat(os.path.join(base_path, '303698/logs'))
stat(os.path.join(base_path, '320451/logs'))
print(f'total_bull: {total_bull}, total_bear: {total_bear}')
