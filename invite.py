# invite.py
import os
import csv
import asyncio
import time
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import ImportContactsRequest
from telethon.tl.types import InputPhoneContact
from config import API_ID, API_HASH, GROUP, INVITE_LIMIT, SLEEP_TIME

# 自动创建 accounts 文件夹
if not os.path.exists("accounts"):
    os.makedirs("accounts")

# 读取电话号码
def load_numbers(filename="phones.csv"):
    if not os.path.exists(filename):
        print(f"❌ 找不到 {filename}，请放在项目目录或指定正确路径")
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [row[0].strip() for row in csv.reader(f) if row]

# 拉人函数（兼容超级群组/频道）
async def invite_users(session_name, numbers):
    client = TelegramClient(f"accounts/{session_name}", API_ID, API_HASH)
    await client.start()
    print(f"[{session_name}] 登录成功，准备拉人")

    group = await client.get_entity(GROUP)
    invited = 0

    for i, phone in enumerate(numbers):
        try:
            # 导入联系人
            contact = InputPhoneContact(client_id=i, phone=phone, first_name="User", last_name="")
            result = await client(ImportContactsRequest([contact]))
            users = result.users

            if users:
                # 使用 InviteToChannelRequest 拉人
                await client(InviteToChannelRequest(
                    channel=group,
                    users=[users[0]]  # 注意是列表
                ))
                invited += 1
                print(f"[{session_name}] 已邀请: {phone}")
                time.sleep(SLEEP_TIME)

        except errors.UserPrivacyRestrictedError:
            print(f"[{session_name}] {phone} 拒绝被拉")
        except errors.UserAlreadyParticipantError:
            print(f"[{session_name}] {phone} 已经在群里了")
        except Exception as e:
            print(f"[{session_name}] 拉人失败 {phone}: {e}")

        if invited >= INVITE_LIMIT:
            print(f"[{session_name}] 达到每日限制 {INVITE_LIMIT}")
            break

    await client.disconnect()

# 主函数
async def main():
    numbers = load_numbers()
    if not numbers:
        print("❌ 没有号码可以拉人，退出")
        return

    sessions = ["account1"]  # 可以加多个账号
    chunk_size = len(numbers) // len(sessions)

    tasks = []
    for idx, session in enumerate(sessions):
        chunk = numbers[idx*chunk_size:(idx+1)*chunk_size]
        tasks.append(invite_users(session, chunk))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
