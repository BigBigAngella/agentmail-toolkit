"""
用户client:
调用LLM:openai client
调用mcp工具服务器:mcp client
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client
from typing import List, Dict
import json
import asyncio

api_key = {
    'alibaba': 'sk-Rl3OWQuqWm',
    'doubao': '0271b1e1-713c-45a4-89db-90052b2ab5e1',
    'moonshot': 'sk-f1esStieOd8UJcIVTxNHeEDysECcaqZbMIdZxWmz5C1uYLFv'
}
url = {
    'alibaba': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'doubao': 'https://ark.cn-beijing.volces.com/api/v3',
    'moonshot': 'https://api.moonshot.cn/v1'
}

# OPENAI_API_KEY = api_key['doubao']
# OPENAI_BASE_URL = url['doubao']

class UserClient:
    def __init__(self, script = 'python/test/server.py'):
        self.mcp_client = Client(script)
        self.openai_client = OpenAI(
            api_key=api_key['doubao'],
            base_url=url['doubao']
        )
        self.messages = []
        self.model = 'ep-20241112110509-8vzsd'
        self.tools = None

    async def prepare_tools(self, ):
        async with self.mcp_client:
            tools = await self.mcp_client.list_tools()
            tools = [{
                    'type': 'function',
                    'function': {
                        'name': tool.name,
                        'description': tool.description,
                        'input_schema': tool.inputSchema,
                    }
                } for tool in tools]
            return tools
   

    # def call_mcp_tool(self, tool_name, tool_args):
    #     return self.mcp_client.call_tool(tool_name, tool_args)
    
    # def call_llm(self, prompt):
    #     return self.openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])

    async def chat(self, message:List[Dict]):
        if not self.tools:
            self.tools = await self.prepare_tools()

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=message,
            tools=self.tools,
            tool_choice='auto'
        )
        
        # if response.choices[0].finish_reason != 'tool_calls':
        #     return response.choices[0].message

        response_message = response.choices[0].message
        
        if not response_message.tool_calls:
            return response_message

    
        # 执行mcp工具
        tool_responses = []
        for tool_call in response_message.tool_calls:
            try:
                response = await self.mcp_client.call_tool(
                    tool_call.function.name, 
                    json.loads(tool_call.function.arguments)
                )
                tool_responses.append(response)
            except Exception as e:
                tool_responses.append({
                    'error': str(e),
                    'tool_name': tool_call.function.name
                })

        self.messages.append({
            "role": "assistant",
            "content": str(tool_responses)
        })

        return await self.chat(self.messages)

    async def loop(self):
        while True:
            try:
                question = input("User:")
                message = {
                    'role': 'user',
                    'content': question
                }
                self.messages.append(message)

                response = await self.chat(self.messages)

                print("AI:",response.content)

            except KeyboardInterrupt:
                print("\n退出聊天...")
                break
            except Exception as e:
                print(f"发生错误: {e}")
                self.messages = [] 


async def main():
    user_client = UserClient()
    await user_client.loop()
    

if __name__ == "__main__":
    asyncio.run(main())
    
