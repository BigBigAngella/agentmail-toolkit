import os
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from openai import OpenAI
from email.header import Header
import logging

# 加载环境变量
from pathlib import Path
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
env_path = current_dir / ".env"
print(f"\n[文件信息]")
print(f".env 路径: {env_path}")
print(f"文件存在: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True, verbose=True)
# 初始化 MCP 服务器
mcp = FastMCP("NewsServer")
# @mcp.tool() 是 MCP 框架的装饰器，表明这是一个 MCP 工具。之后是对这个工具功能的描述

@mcp.tool()
async def search_google_news(keyword: str) -> str: 
    """ 使用 Serper API(Google Search 封装)根据关键词搜索新闻内容，返回前5条标题、描述和链接。
        参数:    keyword (str): 关键词
        返回:    str: JSON 字符串，包含新闻标题、描述、链接
    """
    # 环境变量检查：获取并验证 SERPER_API_KEY 是否存在 
    print(f"[DEBUG] 进入工具函数 {__name__}")   
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "❌ 未配置 SERPER_API_KEY，请在 .env 文件中设置"
    # 请求配置：设置 API 请求的 URL、头部和负载    
    url = "https://google.serper.dev/news"
    headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json" }
    payload = {"q": keyword}
    # 异步请求处理：发送 POST 请求并获取响应数据    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

    # 响应验证：检查返回数据是否包含有效新闻结果    
    if "news" not in data:
        return "❌ 未获取到搜索结果"
    # 数据提取：从响应中解析前5条新闻的标题、描述和链接    
    articles = [{
                    "title": item.get("title"),
                    "desc": item.get("snippet"),
                    "url": item.get("link")
                      } for item in data["news"][:5]
    ] 
    # 文件存储：创建输出目录并生成带时间戳的 JSON 文件名    
    output_dir = "./google_news"
    os.makedirs(output_dir, exist_ok=True) 
    filename = f"google_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
 
    return (f"✅ 已获取与 [{keyword}] 相关的前5条 Google 新闻：\n"
            f"{json.dumps(articles, ensure_ascii=False, indent=2)}\n"
            f"📄 已保存到：{file_path}" )
    
# @mcp.tool() 是 MCP 框架的装饰器，标记该函数为一个可调用的工具
@mcp.tool()
async def analyze_sentiment(text: str, filename: str) -> str:
    """ 对传入的一段文本内容进行情感分析，并保存为指定名称的 Markdown 文件。
        参数:   
            text (str): 新闻描述或文本内容
            filename (str): 保存的 Markdown 文件名
        返回:   
            str: 完整文件路径（用于邮件发送）
    """
    # 初始化 OpenAI 客户端     
    openai_key = os.getenv("API_KEY")
    model = os.getenv("MODEL")
    client = OpenAI(api_key=openai_key, base_url=os.getenv("BASE_URL"))
    # 构建情感分析提示词    
    # 将用户输入的文本嵌入到预定义的提示模板中    
    prompt = f"请对以下新闻内容进行情绪倾向分析，并说明原因：\n\n{text}"
    # 调用大语言模型进行情感分析，发送单轮对话请求并获取模型生成的响应内容    
    response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                    )
    result = response.choices[0].message.content.strip()
    # 生成舆情分析报告模板    
    # 包含时间戳、原始文本和分析结果的结构化 Markdown 内容    
    markdown =f"""
# 舆情分析报告
**分析时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---
## 📥 原始文本{text}
---
## 📊 分析结果{result}"""
    # 创建报告输出目录    
    # 确保目标目录存在（如不存在则自动创建）    
    output_dir ="./sentiment_reports"
    os.makedirs(output_dir, exist_ok=True)
  
    if not filename:
        filename = f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    # 保存分析报告到文件系统   
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown)
        
    return file_path

# @mcp.tool()
# async def send_email_with_attachment(to: str, subject: str, body: str, filename: str) -> str:
#     """
#     发送带附件的邮件，支持中文编码。
    
#     参数:
#         to: 收件人邮箱地址
#         subject: 邮件标题（支持中文）
#         body: 邮件正文（支持中文）
#         filename: 保存的 Markdown 文件名（不含路径）
        
#     返回:
#         邮件发送状态说明
#     """
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger("email_sender")
    
#     try:
#         # 从环境变量获取SMTP配置信息
#         smtp_server = os.getenv("SMTP_SERVER")
#         smtp_port = int(os.getenv("SMTP_PORT", 465))
#         sender_email = os.getenv("EMAIL_USER")
#         sender_pass = os.getenv("EMAIL_PASS")
        
#         # 验证关键配置
#         if not all([smtp_server, sender_email, sender_pass]):
#             missing = [k for k, v in zip(["SMTP_SERVER", "EMAIL_USER", "EMAIL_PASS"], 
#                                        [smtp_server, sender_email, sender_pass]) if not v]
#             return f"❌ 缺少环境变量配置: {', '.join(missing)}"
        
#         # 检查附件文件是否存在
#         reports_dir = "./sentiment_reports"
#         full_path = Path(reports_dir) / filename
        
#         if not full_path.exists():
#             return f"❌ 附件路径无效，未找到文件: {full_path}"
        
#         # 创建邮件对象并设置基本信息
#         msg = EmailMessage()
        
#         # 使用Header处理中文主题
#         msg["Subject"] = Header(subject, 'utf-8').encode()
#         msg["From"] = sender_email
#         msg["To"] = to
        
#         # 设置正文编码为UTF-8
#         msg.set_content(body, charset='utf-8')
        
#         # 读取并添加附件
#         try:
#             with open(full_path, "rb") as f:
#                 file_data = f.read()
#                 file_name = full_path.name
                
#                 # 使用Header处理中文文件名
#                 encoded_filename = Header(file_name, 'utf-8').encode()
                
#                 msg.add_attachment(
#                     file_data,
#                     maintype="text",
#                     subtype="markdown",  # 更精确的MIME类型
#                     filename=encoded_filename
#                 )
                
#                 logger.info(f"✅ 成功添加附件: {file_name} ({len(file_data)}字节)")
                
#         except Exception as e:
#             logger.error(f"❌ 附件读取失败: {str(e)}")
#             return f"❌ 附件处理失败: {str(e)}"
        
#         # 通过SMTP服务器发送邮件
#         try:
#             logger.info(f"🔄 正在连接SMTP服务器: {smtp_server}:{smtp_port}")
            
#             # 根据端口选择SSL或TLS
#             if smtp_port == 465:
#                 with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
#                     logger.info("🔐 使用SSL加密连接")
#                     server.login(sender_email, sender_pass)
#                     server.send_message(msg)
#             else:
#                 with smtplib.SMTP(smtp_server, smtp_port) as server:
#                     server.starttls()  # 启用TLS加密
#                     logger.info("🔐 使用TLS加密连接")
#                     server.login(sender_email, sender_pass)
#                     server.send_message(msg)
            
#             logger.info(f"✅ 邮件已成功发送给 {to}")
#             return f"✅ 邮件已成功发送给 {to} | 附件: {filename}"
            
#         except smtplib.SMTPException as e:
#             logger.error(f"❌ SMTP协议错误: {str(e)}")
#             return f"❌ 邮件发送失败(SMTP): {str(e)}"
            
#         except Exception as e:
#             logger.error(f"❌ 发送过程中发生未知错误: {str(e)}")
#             return f"❌ 邮件发送失败: {str(e)}"
            
#     except Exception as e:
#         logger.exception("🔥 邮件发送过程中发生严重错误")
#         return f"❌ 邮件发送失败: {str(e)}"

@mcp.tool()
async def send_email_with_attachment(to: str, subject: str, body: str, filename: str) -> str:
    """
    发送带附件的邮件。
    参数:
        to: 收件人邮箱地址
        subject: 邮件标题
        body: 邮件正文
        filename: 保存的 Markdown 文件名
    返回:
        邮件发送状态说明 """
    # 从环境变量获取SMTP配置信息    
    smtp_server = os.getenv("SMTP_SERVER") # 例如 smtp.qq.com    
    smtp_port = int(os.getenv("SMTP_PORT",465))
    sender_email = os.getenv("EMAIL_USER")
    sender_pass = os.getenv("EMAIL_PASS")
    # 检查附件文件是否存在    
    full_path = os.path.abspath(os.path.join("./sentiment_reports", filename))
    if not os.path.exists(full_path):
        return f"❌ 附件路径无效，未找到文件: {full_path}"
    # 创建邮件对象并设置基本信息    
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to 
    msg.set_content(body)
    # 读取并添加附件    
    try:
        with open(full_path, "rb") as f:            
            file_data = f.read()            
            file_name = os.path.basename(full_path)            
            msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)    
    except Exception as e:        
        return f"❌ 附件读取失败: {str(e)}"    
    # 通过SMTP服务器发送邮件    
    try:        
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:            
            server.login(sender_email, sender_pass)            
            server.send_message(msg)        
            return f"✅ 邮件已成功发送给 {to}，附件路径: {full_path}"    
    except Exception as e:        
        return f"❌ 邮件发送失败: {str(e)}"
    
if __name__ == "__main__":    
    mcp.run(transport='stdio')