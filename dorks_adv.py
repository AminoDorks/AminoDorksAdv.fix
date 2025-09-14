from asyncio import gather, run
from typing import Any, List
from aminodorksfix.asyncfix import Client, SubClient
from base64 import b64decode

print(f"""\033[0;31m
{b64decode("ICBfX19fICAgICAgICAgICAgIF8gICAgICAgICAgIF8gICAgICAgXyAgICAgICANCiB8ICBfIFwgIF9fXyAgXyBfX3wgfCBfX19fXyAgIC8gXCAgIF9ffCB8XyAgIF9fDQogfCB8IHwgfC8gXyBcfCAnX198IHwvIC8gX198IC8gXyBcIC8gX2AgXCBcIC8gLw0KIHwgfF98IHwgKF8pIHwgfCAgfCAgIDxcX18gXC8gX19fIFwgKF98IHxcIFYgLyANCiB8X19fXy8gXF9fXy98X3wgIHxffFxfXF9fXy9fLyAgIFxfXF9fLF98IFxfLyAgDQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIA==".encode()).decode()}
Telegram: @aminodorks
""")


async def login(client: Client) -> None:
    try:
        await client.login(input("[*] Email: "), input("[*] Password: "))
    except Exception as e:
        print(f"[LoginException]: {e}")
        await login(client)


async def choose_community(client: Client) -> str:
    communities = await client.sub_clients()

    for index, name in enumerate(communities.name, 1):
        print(f"{index}.{name}")

    return communities.comId[int(input("[*]Enter the community number: ")) - 1]


async def get_excluded_users(sub_client: SubClient) -> List[Any]:
    excluded_users = []

    leaders_response, curators_response, blocked_response = await gather(
        sub_client.get_all_users(type="leaders"),
        sub_client.get_all_users(type="curators"),
        sub_client.get_blocked_users(),
    )

    for user in leaders_response.json.get("userProfileList", []):
        excluded_users.append(user)

    for user in curators_response.json.get("userProfileList", []):
        excluded_users.append(user)

    for user in blocked_response.json:
        excluded_users.append(user)

    return excluded_users


async def get_users(sub_client: SubClient) -> List[List[Any]]:
    excluded_users = await get_excluded_users(sub_client)

    online_page = await sub_client.get_online_users()
    len_users_in_online = online_page.json.get("userProfileCount", 0)

    tasks = [
        sub_client.get_online_users(start=start, size=start + 100)
        for start in range(0, len_users_in_online, 100)
    ]

    online_results = await gather(*tasks)

    online_users = set()
    for response in online_results:
        for user in response.json.get("userProfileList", []):
            uid = user["uid"]
            if uid not in excluded_users:
                online_users.add(uid)

    tasks = [
        sub_client.get_all_users(type="recent", start=start, size=start + 100)
        for start in range(0, 400, 100)
    ]

    recent_results = await gather(*tasks)

    recent_users = set()
    for response in recent_results:
        for user in response.json.get("userProfileList", []):
            uid = user["uid"]
            if (
                uid not in excluded_users
                and uid not in recent_users
                and uid not in online_users
            ):
                recent_users.add(uid)

    all_users = list(online_users | recent_users)
    groups = [all_users[i: i + 99] for i in range(0, len(all_users), 99)]

    return groups


async def mass_chat_send(
    sub_client: SubClient,
    groups: List[List[Any]],
    message: str,
    title: str,
    content: str,
) -> None:
    sent_uids = set()

    for group in groups:
        blocked_now = await sub_client.get_blocker_users()
        filtered_group = [uid for uid in group if uid not in blocked_now]

        if not filtered_group:
            continue

        try:
            await sub_client.start_chat(
                userId=filtered_group,
                message=message,
                title=title,
                content=content
            )
            sent_uids.update(filtered_group)
            print(f"[+] Chat with {len(filtered_group)} users created.")

        except Exception as e:
            print(f"[❌] Failed: {e}")
            continue


async def main() -> None:
    client = Client(api_key=input("[*] API key: "), socket_enabled=False)

    await login(client)

    sub_client = SubClient(
        comId=(await choose_community(client)),
        profile=client.profile,  # pyright: ignore[reportArgumentType]
    )

    await mass_chat_send(
        sub_client=sub_client,
        groups=await get_users(sub_client),
        message=input("[*] Message: "),
        title=input("[*] Title: "),
        content=input("[*] Content: "),
    )


if __name__ == "__main__":
    run(main())
