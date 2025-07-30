"""
1. 创建一个fastmcp的客户端
2. 创建一个函数，用于发送邮件
3. 创建一个函数，用于读取邮件
4. 创建一个函数，用于搜索邮件
5. 创建一个函数，用于创建邮箱
6. 启动客户端
"""

from fastmcp import Client
import asyncio
async def run():
    client = Client('python/test/server.py')
    async with client:
        tools = await client.list_tools()
        for tool in tools:
            try:
                if tool.name == 'get_weather':
                    result = await client.call_tool(tool.name, {
                        "args": {"city": "Beijing"}
                    })
                    print(f"天气查询结果: {result}")
                else:
                    print(f"工具{tool.name}未实现")
            except Exception as e:
                print(f"工具调用失败: {e}")


                # elif tool.name == 'send_email':
                #     result = await client.call_tool(tool.name, {'to': 'test@test.com', 'subject': 'test', 'body': 'test'})
                #     print(f"邮件发送结果: {result}")

                # elif tool.name == 'search_email':
                #     result = await client.call_tool(tool.name, {'query': 'test'})
                #     print(f"邮件搜索结果: {result}")

                # elif tool.name == 'create_email':
                #     result = await client.call_tool(tool.name, {'to': 'test@test.com', 'subject': 'test', 'body': 'test'})
                #     print(f"邮件创建结果: {result}")

                # elif tool.name == 'delete_email':
                #     result = await client.call_tool(tool.name, {'email_id': 'test'})
                #     print(f"邮件删除结果: {result}")

                
                
            


if __name__ == "__main__":
    asyncio.run(run())

