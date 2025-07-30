"""
1. 创建fastmcp的实例
2.创建函数,发送邮件、读取邮件、搜索邮件、创建邮箱
3.@mcp.tool()装饰器
4.启动mcp服务器
"""

from fastmcp import FastMCP
from dotenv import load_dotenv
import os
from agentmail_toolkit import Toolkit,tools
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field
import requests
load_dotenv()

app = Flask(__name__)
mcp = FastMCP()

WEATHER_API_KEY = '8b9e88b9d79140a3a3563408252807'
class WeatherArgs(BaseModel):
    city: str = Field(..., description="需要查询天气的城市名称")

@mcp.tool()
def get_weather(args: WeatherArgs) -> dict:
    """获取指定城市的天气信息"""
    api_key = '8b9e88b9d79140a3a3563408252807'
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={args.city}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# @mcp.tool()
# def send_email(to: str, subject: str, body: str) -> str:
#     return f"Email sent to {to} with subject {subject} and body {body}."

# @mcp.tool()
# def read_email(email_id: str) -> str:
#     return f"Email with id {email_id} read."

# @mcp.tool()
# def search_email(query: str) -> str:
#     return f"Email with query {query} searched."

# @mcp.tool()
# def create_email_box(email_box_name: str) -> str:
#     return f"Email box with name {email_box_name} created."


if __name__ == "__main__":
    mcp.run()