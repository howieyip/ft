import os

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
                        print(f'{file.name}: {line}', end='')
                        break

base_path = '/data/release/ft'
stat(os.path.join(base_path, '303698/logs'))
stat(os.path.join(base_path, '320451/logs'))
