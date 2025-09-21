import os
import csv
import asyncio
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from config import API_IDS, API_HASHS, SESSION_FILES, GROUP, INVITE_LIMIT, SLEEP_TIME

PHONES_FILE = "phones.csv"
INVITED_FILE = "invited.csv"

# 自动创建 accounts 文件夹
if not os.path.exists("accounts"):
    os.makedirs("accounts")

# 读取电话号码
def load_numbers(filename=PHONES_FILE):
    if not os.path.exists(filename):
        print(f"❌ 找不到 {filename}，请放在项目目录或指定正确路径")
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [row[0].strip() for row in csv.reader(f) if row]

# 保存号码回 phones.csv（只保留未拉过的）
def save_numbers(numbers, filename=PHONES_FILE):
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for num in numbers:
            writer.writerow([num])

# 记录拉人结果（成功/失败都写）
def save_invited(phone, status):
    # 如果文件不存在，写表头
    write_header = not os.path.exists(INVITED_FILE)
    with open(INVITED_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["phone", "status"])
        writer.writerow([phone, status])

# 拉人函数
async def invite_users(api_id, api_hash, session_name, numbers):
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print(f"[{session_name}] 登录成功，准备拉人")

    group = await client.get_entity(GROUP)
    invited = 0
    remaining_numbers = numbers.copy()

    for i, phone in enumerate(numbers):
        try:
            contact = InputPhoneContact(client_id=i, phone=phone, first_name="User", last_name="")
            result = await client(ImportContactsRequest([contact]))
            users = result.users

            if users:
                await client(InviteToChannelRequest(
                    channel=group,
                    users=[users[0]]
                ))
                invited += 1
                print(f"[{session_name}] ✅ 已邀请: {phone}")
                save_invited(phone, "成功")
                remaining_numbers.remove(phone)  # 成功就从列表删掉
            else:
                save_invited(phone, "❌ 用户不存在")
                remaining_numbers.remove(phone)

        except errors.UserPrivacyRestrictedError:
            print(f"[{session_name}] ⚠️ {phone} 拒绝被拉")
            save_invited(phone, "拒绝被拉")
            remaining_numbers.remove(phone)
        except errors.UserAlreadyParticipantError:
            print(f"[{session_name}] ⚠️ {phone} 已经在群里了")
            save_invited(phone, "已在群里")
            remaining_numbers.remove(phone)
        except errors.FloodWaitError as e:
            print(f"[{session_name}] ⏸️ FloodWait，需要等待 {e.seconds} 秒 (号码保留)")
            save_invited(phone, f"FloodWait {e.seconds}s")
            break  # FloodWait 不删除号码，直接退出
        except Exception as e:
            print(f"[{session_name}] ❌ 拉人失败 {phone}: {e}")
            save_invited(phone, f"失败: {e}")
            remaining_numbers.remove(phone)

        # 每次循环都更新 phones.csv
        save_numbers(remaining_numbers)

        if invited >= INVITE_LIMIT:
            print(f"[{session_name}] ⏸️ 达到每日限制 {INVITE_LIMIT}")
            break

        await asyncio.sleep(SLEEP_TIME)

    await client.disconnect()
    print(f"[{session_name}] 完成任务，共邀请 {invited} 人")

# 主函数
async def main():
    numbers = load_numbers()
    if not numbers:
        print("❌ 没有号码可以拉人，退出")
        return

    print("\n=== 账号列表 ===")
    for i, session in enumerate(SESSION_FILES, start=1):
        print(f"{i}. {session}")
    print("all. 使用所有账号")

    choice = input("请选择要使用的账号编号 (输入数字 或 all): ").strip()

    tasks = []
    if choice.lower() == "all":
        total_accounts = len(API_IDS)
        chunk_size = len(numbers) // total_accounts + 1

        for idx in range(total_accounts):
            api_id = API_IDS[idx]
            api_hash = API_HASHS[idx]
            session = SESSION_FILES[idx]
            chunk = numbers[idx*chunk_size:(idx+1)*chunk_size]
            if chunk:
                tasks.append(invite_users(api_id, api_hash, session, chunk))

    else:
        try:
            idx = int(choice) - 1
            api_id = API_IDS[idx]
            api_hash = API_HASHS[idx]
            session = SESSION_FILES[idx]
            tasks.append(invite_users(api_id, api_hash, session, numbers))
        except Exception:
            print("❌ 输入错误，退出")
            return

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
