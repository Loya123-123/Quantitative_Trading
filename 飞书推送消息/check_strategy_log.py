import os
import re
import json
import requests
from datetime import datetime, timedelta
import glob

# 飞书机器人配置
CONFIG_FILE = "/Users/jianzhong/ProjectCode/Quantitative_Trading/飞书推送消息/配置信息.json"
log_dir = "/Users/jianzhong/ProjectCode/Quantitative_Trading/log"

def load_config():
    """加载飞书机器人配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("配置文件未找到")
        return None
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return None


def get_access_token(app_id, app_secret):
    """获取访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    params = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    response = requests.post(url, params=params)
    result = response.json()
    if result.get("code") == 0:
        return result.get("tenant_access_token")
    else:
        print(f"获取访问令牌失败: {result}")
        return None


def send_feishu_message(access_token, receive_id_type, receive_id, message):
    """发送飞书消息"""
    import json
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    # 飞书API要求content字段是JSON字符串，如 '{"text":"test content"}'
    content_str = json.dumps({"text": message}, ensure_ascii=False)
    body = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": content_str  # content字段必须是JSON字符串格式
    }
    try:
        response = requests.post(url=url, headers=headers, json=body)  # 使用json参数自动处理序列化
        response_json = response.json()
        if response_json.get("code") == 0:
            print("消息发送成功")
            return True
        else:
            print(f"消息发送失败: {response_json}")
            return False
    except Exception as e:
        print(f"发送消息时出错: {e}")
        return False


def check_log_file_exists(account_id=None):
    """检查日志文件是否存在（只检查今天的日志）"""

    today = datetime.now().date()
    current_hour = datetime.now().hour
    # current_hour = 19
    # 如果指定了账户ID，则查找特定账户的日志文件
    if account_id:
        pattern = os.path.join(log_dir, f"datalog-{account_id}-*.log")
    else:
        pattern = os.path.join(log_dir, "datalog-*.log")
    
    log_files = glob.glob(pattern)

    if not log_files:
        return None

    # 过滤出今天的日志文件
    today_logs = []
    for log_file in log_files:
        basename = os.path.basename(log_file)
        # 提取时间部分：datalog-<account_id>-YYYYMMDDHH.log
        parts = basename.split('-')
        if len(parts) >= 3:  # 新格式
            time_part = parts[2].split('.')[0]  # 提取时间部分 YYYYMMDDHH
            try:
                # 从时间字符串中提取年月日部分 (YYYYMMDD) 和小时部分 (HH)
                date_part = time_part[:8]
                hour_part = int(time_part[8:10])  # 提取小时部分
                file_date = datetime.strptime(date_part, "%Y%m%d").date()
                
                if file_date == today:
                    # 根据当前小时和文件小时部分来决定是否添加到today_logs
                    if current_hour < 19:
                        # 如果当前时间小于19点，选择小时部分小于19的文件
                        if hour_part < 19:
                            today_logs.append(log_file)
                    else:
                        # 如果当前时间大于等于19点，选择小时部分大于等于19的文件
                        if hour_part >= 19:
                            today_logs.append(log_file)
            except ValueError:
                continue

    if not today_logs:
        return None

    # 返回按修改时间最新的日志文件
    latest_log = max(today_logs, key=os.path.getmtime)
    return latest_log


def check_first_lines_for_account(log_file, expected_account_id):
    """检查日志文件前15行是否包含指定的账户ID"""
    try:
        # 尝试不同的编码方式打开文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        lines = []

        for encoding in encodings:
            try:
                with open(log_file, 'r', encoding=encoding) as f:
                    lines = []
                    for i, line in enumerate(f):
                        lines.append(line)
                        if i >= 14:  # 读取前15行
                            break
                break  # 成功读取，跳出循环
            except UnicodeDecodeError:
                continue

        if not lines:  # 如果所有编码都失败
            print(f"无法使用常见编码读取文件 {log_file}")
            return False

        # 检查是否包含指定的账户ID
        for line in lines:
            if expected_account_id in line:
                return True
        return False
    except Exception as e:
        print(f"读取日志文件前15行时出错: {e}")
        return False


def check_last_lines_for_errors(log_file):
    """检查日志文件最后200行的执行情况和异常"""
    try:
        # 尝试不同的编码方式打开文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        lines = []

        for encoding in encodings:
            try:
                with open(log_file, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                break  # 成功读取，跳出循环
            except UnicodeDecodeError:
                continue

        if not lines:  # 如果所有编码都失败
            print(f"无法使用常见编码读取文件 {log_file}")
            return False, [f"无法使用常见编码读取文件 {log_file}"]

        # 获取最后200行
        last_lines = lines[-200:] if len(lines) > 200 else lines

        # 寻找最近一次完整执行过程
        start_indices = []
        end_indices = []

        for i, line in enumerate(last_lines):
            if "[处理函数] 开始执行handlebar函数" in line:
                start_indices.append(i)
            elif "[处理函数] handlebar函数执行完成" in line:
                end_indices.append(i)

        # 找到最近一次完整的执行过程
        latest_execution_start = -1
        latest_execution_end = -1

        for start_idx in reversed(start_indices):
            # 找到这个开始之后的第一次结束
            for end_idx in end_indices:
                if end_idx > start_idx:
                    latest_execution_start = start_idx
                    latest_execution_end = end_idx
                    break
            if latest_execution_start != -1:
                break

        if latest_execution_start == -1 or latest_execution_end == -1:
            # 没有找到完整的执行过程，直接在整个检查范围内查找异常
            error_lines = []
            for line in last_lines:
                if "异常处理" in line:
                    error_lines.append(line.strip())

            if error_lines:
                return True, error_lines
            else:
                return False, ["未找到完整的执行过程，但也没有发现异常"]

        # 提取完整执行过程中的内容
        execution_lines = last_lines[latest_execution_start:latest_execution_end + 1]

        # 检查这段执行过程中是否有异常
        error_lines = []
        for line in execution_lines:
            if "异常处理" in line:
                error_lines.append(line.strip())

        # 如果没有在完整执行过程中找到异常，也检查整个最后200行是否有异常
        if not error_lines:
            for line in last_lines:
                if "异常处理" in line and line.strip() not in [el.strip() for el in error_lines]:
                    # 确保不重复添加
                    line_stripped = line.strip()
                    if line_stripped not in [el.strip() for el in error_lines]:
                        error_lines.append(line_stripped)

        return len(error_lines) > 0, error_lines

    except Exception as e:
        print(f"读取日志文件最后200行时出错: {e}")
        return False, [f"读取日志文件时出错: {e}"]


def main():
    """主函数"""
    print("开始检查策略日志...")

    # 加载配置
    config = load_config()
    if not config:
        print("无法加载配置文件，退出")
        return

    # 获取访问令牌
    notification_config = config.get("策略通知", {})
    access_token = get_access_token(notification_config["app_id"], notification_config["app_secret"])
    if not access_token:
        print("无法获取访问令牌，退出")
        return

    # 从配置中获取账户ID字典和飞书通知配置
    account_mapping = config.get("account_id", {})
    notification_config = config.get("策略通知", {})
    
    if not account_mapping:
        print("配置文件中未找到账户ID字典，退出")
        return

    # 遍历每个账户进行检查
    for account_id, account_name in account_mapping.items():
        print(f"\n开始检查账户 {account_name} (ID: {account_id}) 的日志...")
        
        # 检查日志文件是否存在
        latest_log_file = check_log_file_exists(account_id)

        if not latest_log_file:
            # 日志文件不存在，发送预警
            message = f"警告: 账户 {account_name} (ID: {account_id}) 的日志文件不存在！策略可能未运行。时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            print(message)
            send_feishu_message(access_token, notification_config["receive_id_type"], notification_config["receive_id"], message)
            continue

        print(f"找到日志文件: {latest_log_file}")

        # 检查前15行是否包含账户ID
        has_account = check_first_lines_for_account(latest_log_file, account_id)

        if not has_account:
            # 没有找到账户ID，发送预警
            message = f"警告: 在日志中未找到账户ID {account_id}，策略可能运行异常！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 日志文件: {os.path.basename(latest_log_file)}"
            print(message)
            send_feishu_message(access_token, notification_config["receive_id_type"], notification_config["receive_id"], message)
            continue
        else:
            print(f"在日志中找到账户ID {account_id}，策略运行正常")

        # 检查最后200行是否有异常
        has_error, error_messages = check_last_lines_for_errors(latest_log_file)

        if has_error:
            # 发现异常，发送预警
            error_text = "\n".join(error_messages[:5])  # 只显示前5条错误
            message = f"警报: 账户 {account_name} (ID: {account_id}) 在策略日志中发现异常！\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n日志文件: {os.path.basename(latest_log_file)}\n异常内容:\n{error_text}"
            print(message)
            send_feishu_message(access_token, notification_config["receive_id_type"], notification_config["receive_id"], message)
        else:
            # 没有异常，发送正常通知
            message = f"账户 {account_name} (ID: {account_id}) 策略运行正常 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 日志文件: {os.path.basename(latest_log_file)}"
            print(message)
            send_feishu_message(access_token, notification_config["receive_id_type"], notification_config["receive_id"], message)

    print("\n所有账户检查完成")


if __name__ == "__main__":
    main()
