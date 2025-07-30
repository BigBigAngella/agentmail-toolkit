from agentmail_toolkit.openai import AgentMailToolkit
from agents import Agent, Runner, RawResponsesStreamEvent
from openai.types.responses import ResponseTextDeltaEvent
import asyncio
from openai import OpenAI
import os
from dotenv import load_dotenv
from agentmail_toolkit import Toolkit,tools

load_dotenv()

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
toolkit = Toolkit()

mail_tools = [
    tools.SendEmailTool(),
    tools.ReadInboxTool(),
    tools.SearchEmailsTool()
]

client = OpenAI(
    api_key=api_key['doubao'],
    base_url=url['doubao'],
)


agent = Agent(
    name="Email Agent",
    instructions="You are an email agent created by AgentMail that can create and manage inboxes as well as send and receive emails.",
    tools=AgentMailToolkit().get_tools(),
)


async def main():
    messages = []

    while True:
        prompt = input("\n\nUser:\n\n")
        if prompt.lower() == "q":
            break

        result = Runner.run_streamed(
            agent, messages + [{"role": "user", "content": prompt}]
        )

        print("\nAssistant:\n")

        async for event in result.stream_events():
            if isinstance(event, RawResponsesStreamEvent) and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                print(event.data.delta, end="", flush=True)

        messages = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())
