import asyncio
import os
import  json
from  typing  import  Optional,  List
from  contextlib  import  AsyncExitStack
from  datetime  import  datetime
import  re
from  openai  import  OpenAI
from  mcp  import  ClientSession, StdioServerParameters
from  mcp.client.stdio  import  stdio_client
from pathlib import Path
import sys
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
env_path = current_dir / ".env"
# print(f"\n[文件信息]")
# print(f".env 路径: {env_path}")
# print(f"文件存在: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True, verbose=True)

class  MCPClient:       
    def  __init__(self):                   
        """初始化类实例并配置API连接                                     
        该构造函数执行以下关键操作：                  
        1. 初始化异步上下文管理器栈                  
        2. 从环境变量加载API配置参数                  
        3. 验证必要的API密钥是否存在                  
        4. 创建OpenAI客户端实例                  
        5. 初始化会话状态                                     
        属性说明：                  
        self.exit_stack: 管理异步上下文资源的退出栈                  
        self.openai_api_key: 从环境变量加载的API密钥                  
        self.base_url: API服务的基础URL地址                  
        self.model: 使用的AI模型名称                  
        self.client: 配置好的OpenAI客户端实例                  
        self.session: 存储异步HTTP会话的容器（初始为空）                  
        """                   
        # 初始化异步资源管理栈                  
        self.exit_stack = AsyncExitStack()                                      
        # 从环境变量加载API配置                  
        self.openai_api_key = os.getenv("API_KEY")                  
        self.base_url = os.getenv("BASE_URL")                  
        self.model = os.getenv("MODEL")                                      
        # 关键参数验证：API密钥缺失时抛出异常                   
        if  not  self.openai_api_key:                         
            raise  ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置 API_KEY")                                      
        # 创建配置好的API客户端                  
        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)                                      
        # 初始化会话容器（后续建立连接时填充）                  
        self.session:  Optional[ClientSession] =  None

    async def connect_to_server(self, server_script_path:  str):                   
        """                  
        连接到指定脚本路径的服务器进程                         
        该方法会启动一个子进程运行指定的服务器脚本，并通过标准输入输出与服务器建立通信连接，                  
        初始化客户端会话，并获取服务器支持的工具列表。                         
        参数:                        
        server_script_path (str): 服务器脚本文件路径，必须是.py或.js扩展名                         
        返回:                        
        None: 此方法没有直接返回值，但会初始化以下成员属性:                              
        self.stdio: 服务器进程的标准输入输出流                              
        self.write: 向服务器写入数据的函数                              
        self.session: 与服务器通信的客户端会话对象                         
        异常:                        
        ValueError: 当脚本扩展名不是.py或.js时抛出                  
        """                   
        # 验证服务器脚本文件扩展名                  
        is_python = server_script_path.endswith('.py')                  
        is_js = server_script_path.endswith('.js')                   
        if  not  (is_python  or  is_js):                         
            raise  ValueError("服务器脚本必须是 .py 或 .js 文件")                          
        # 根据文件类型确定启动命令                   
        # 根据您的环境修改这个路径
        # server_path = Path(server_script_path)                  
        # python_executable =  "/Users/caojihong/anaconda3/envs/mcp_new/bin/python"      
        python_executable = sys.executable              
        command = python_executable                          
        # 配置服务器进程参数                  
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)    
    #     server_params = StdioServerParameters(
    #     command=command,
    #     args=[str(server_path)],
    #     env=os.environ.copy()  # 复制当前环境变量
    # )                      
        # 启动服务器进程并建立标准IO通信                  
        stdio_transport =  await  self.exit_stack.enter_async_context(stdio_client(server_params))                          
        # 解构通信通道对象                  
        self.stdio, self.write = stdio_transport                          
        # 创建并初始化客户端会话                  
        self.session =  await  self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        print("开始初始化会话...")
        try:
            await asyncio.wait_for(self.session.initialize(), timeout=10.0)
        except asyncio.TimeoutError:
            print("❌ 会话初始化超时")
            raise 
        print("✅ 会话初始化成功")

        # 获取并打印服务器支持的工具列表                  
        response =  await  self.session.list_tools()                  
        tools = response.tools                   
        print("\n已连接到服务器，支持以下工具:", [tool.name  for  tool  in  tools])       
        
    async def process_query(self, query:  str) ->  str:                   
        """                  
        处理用户查询的主函数，执行完整的情感分析流程。                         
        该函数执行以下关键步骤：                  
        1. 准备工具列表并生成报告文件名                  
        2. 规划工具调用链                  
        3. 执行工具链并收集结果                 
        4. 生成最终回复并保存对话记录                         
        参数:                        
            query: 用户输入的查询字符串                         
        返回值:                        
            str: 模型生成的最终回复文本                  
        """       
        print(f"[DEBUG] 收到查询: {query}")            
        # 准备初始消息和获取工具列表                  
        messages = [{"role":  "user",  "content": query}]                  
        response =  await  self.session.list_tools()                          
        # 构建可用工具列表，提取工具元数据                  
        available_tools = [                        
            {                               
                "type":  "function",                               
                "function": {                                     
                    "name": tool.name,                                     
                    "description": tool.description,                                     
                    "input_schema": tool.inputSchema                              
                    }                        
            }  for  tool  in  response.tools                  
            ]                          
        # 提取查询关键词并生成安全的报告文件名                  
        keyword_match = re.search(r'(关于|分析|查询|搜索|查看)([^的\s，。、？\n]+)', query)
        keyword = keyword_match.group(2)  if  keyword_match  else  "分析对象"   
        safe_keyword = re.sub(r'[\\/:*?"<>|]',  '', keyword)[:20]                  
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')                  
        md_filename =  f"sentiment_{safe_keyword}_{timestamp}.md"                  
        md_path = os.path.join("./sentiment_reports", md_filename)                          
        # 更新查询内容，注入文件名参数供后续工具使用                  
        query = query.strip() +  f" [md_filename={md_filename}] [md_path={md_path}]"                  
        messages = [{"role":  "user",  "content": query}]                          
        # 获取工具调用计划                  
        tool_plan =  await  self.plan_tool_usage(query, available_tools)                         
        tool_outputs = {}                  
        messages = [{"role":  "user",  "content": query}]                          
        # 按计划执行工具链                   
        for  step  in  tool_plan:                       
            tool_name = step["name"]                        
            tool_args = step["arguments"]                                
            # 解析工具参数中的变量引用                         
            for  key, val  in  tool_args.items():                               
                if  isinstance(val,  str)  and  val.startswith("{{")  and  val.endswith("}}"):                                    
                    ref_key = val.strip("{} ")                                    
                    resolved_val = tool_outputs.get(ref_key, val)                                    
                    tool_args[key] = resolved_val                                
            # 为特定工具注入默认文件参数                         
            if  tool_name ==  "analyze_sentiment"  and  "filename"  not  in  tool_args:                              
                tool_args["filename"] = md_filename                         
            if  tool_name ==  "send_email_with_attachment"  and  "attachment_path"  not  in  tool_args:                              
                tool_args["attachment_path"] = md_path                                
            
            # 调用工具并存储输出                        
            result = await self.session.call_tool(tool_name, tool_args)                        
            tool_outputs[tool_name] = result.content[0].text                        
            messages.append({                               
                "role":  "tool",                               
                "tool_call_id": tool_name,                               
                "content": result.content[0].text                        
                })                          
            
        # 使用完整对话上下文生成最终回复                  
        final_response = self.client.chat.completions.create(                        
            model=self.model,                        
            messages=messages                  
            )                  
        final_output = final_response.choices[0].message.content                          
        
        # 定义文件名清理函数                   
        def  clean_filename(text:  str) ->  str:                        
            text = text.strip()                        
            text = re.sub(r'[\\/:*?\"<>|]',  '', text)                         
            return  text[:50]                          
        
        # 准备对话记录存储路径                  
        safe_filename = clean_filename(query)                  
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')                  
        filename =  f"{safe_filename}_{timestamp}.txt"                  
        output_dir =  "./llm_outputs"                  
        os.makedirs(output_dir, exist_ok=True)                  
        file_path = os.path.join(output_dir, filename)                          
        
        # 持久化存储对话记录                   
        with  open(file_path,  "w", encoding="utf-8")  as  f:                        
            f.write(f"🗣 用户提问：{query}\n\n")                        
            f.write(f"🤖 模型回复：\n{final_output}\n")                          
            print(f"📄 对话记录已保存为：{file_path}")                          
        return  final_output       
    
    async  def  chat_loop(self):                   
        """                  
        主聊天循环函数，用于处理用户交互。                         
        此函数实现了一个持续运行的异步聊天循环，主要功能包括：                  
        1. 显示初始提示信息                  
        2. 循环接收用户输入                  
        3. 处理退出指令                  
        4. 异步处理用户查询并显示AI响应                  
        5. 捕获并显示运行过程中的异常                         
        循环将持续运行，直到用户输入'quit'退出指令。                  
        """                          
        # 初始化提示信息                   
        print("\n🤖 MCP 客户端已启动！输入 'quit' 退出")                          
        # 进入主循环中等待用户输入                   
        while  True:                         
            try:                               
                # 获取用户输入并移除首尾空格                              
                query =  input("\n你: ").strip()                                                              
                
                # 检测退出指令                               
                if  query.lower() ==  'quit':                                     
                    break                                      
                # 处理用户查询并获取AI响应                              
                response =  await  self.process_query(query)                                                              
                # 打印AI回复                               
                print(f"\n🤖 AI:  {response}")                                
                # 异常处理模块                         
            except  Exception  as  e:                               
                print(f"\n⚠️ 发生错误:  {str(e)}")       
                
    
    async def plan_tool_usage(self, query:  str, tools:  List[dict]) ->  List[dict]:                   
        """                  
        根据用户查询规划工具调用链                                     
        此函数通过大模型分析用户请求，生成结构化工具调用计划。将可用工具列表转换为提示词，                  
        要求模型返回JSON格式的调用计划，支持多步骤调用（通过{{上一步工具名}}占位符实现）。                         
        Args:                        
            query: 用户自然语言请求文本                        
            tools: 可用工具定义列表，每个工具需包含'function'字典（含'name'和'description'字段）                         
        Returns:                        
            工具调用计划列表，每个元素包含:                              
            name: 工具名称字符串                              
            arguments: 工具参数字典                        
            解析失败时返回空列表                  
        """                                      
        # 打印工具定义用于调试                   
        print("\n📤 提交给大模型的工具定义:")                   
        print(json.dumps(tools, ensure_ascii=False, indent=2))                                      
        # 构造工具描述文本列表                  
        tool_list_text =  "\n".join([                         
            f"-  {tool['function']['name']}:  {tool['function']['description']}"                         
            for  tool  in  tools                 
            ])                                     
        # 构建系统提示词：包含工具列表和输出格式要求                  
        system_prompt = {                         
            "role":  "system",                        
            "content": (                               
                "你是一个智能任务规划助手，用户会给出一句自然语言请求。\n"                               
                "你只能从以下工具中选择（严格使用工具名称）：\n"                               
                f"{tool_list_text}\n"                               
                "如果多个工具需要串联，后续步骤中可以使用 {{上一步工具名}} 占位。\n"                               
                "返回格式：JSON 数组，每个对象包含 name 和 arguments 字段。\n"                               
                "不要返回自然语言，不要使用未列出的工具名。"                        
                )                  
            }                          
        # 构造对话上下文（系统提示+用户查询）                  
        planning_messages = [                        
            system_prompt,                        
            {"role":  "user",  "content": query}                  
            ]                          
        
        # 调用大模型获取规划结果（禁止模型直接调用工具）                  
        response = self.client.chat.completions.create(                        
            model=self.model,                        
            messages=planning_messages,                        
            tools=tools,                        
            tool_choice="none"                  
            )                          
        # 提取模型返回内容并清理JSON格式                  
        content = response.choices[0].message.content.strip()                   
        match  = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)                   
        if  match:                        
            json_text =  match.group(1)                   
        else:                        
            json_text = content                          
            
        # 解析JSON并返回调用计划                   
        try:                        
            plan = json.loads(json_text)                         
            return  plan  if  isinstance(plan,  list)  else  []                   
        except  Exception  as  e:                        
            print(f"❌ 工具调用链规划失败:  {e}\n原始返回:  {content}")                         
            return  []       
        
    async def cleanup(self):                   
        """                  
        异步执行资源清理操作。    

        该方法使用异步上下文管理栈(exit_stack)来统一管理所有需要清理的资源。                  
        调用栈的异步关闭方法(aclose)会按照后进先出顺序关闭栈中所有资源。                         
        参数：                        
            无（除实例自身self外）                         
        返回值：                        
            无                  
        """                  
        await  self.exit_stack.aclose()
        
async  def  main():      
    server_script_path =  "mcp-project1/server_local.py"     
    client = MCPClient()       
    try:   
        print("正在连接服务器...")         
        await  client.connect_to_server(server_script_path) 
        print("✅ 连接成功，开始聊天循环") 
        loop = asyncio.get_running_loop()
        print(f"✅ 事件循环状态: {loop.is_running()}")           
        await  client.chat_loop()   
    except Exception as e:
        print(f"🔥 主循环崩溃: {repr(e)}")
        import traceback
        traceback.print_exc()   
    finally:
        print("正在清理资源...")             
        await  client.cleanup()
            
if  __name__ ==  "__main__":      
    asyncio.run(main())
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # try:
    #     loop.run_until_complete(main())
    # finally:
    #     loop.close()