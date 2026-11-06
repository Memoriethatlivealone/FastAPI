from fastapi import FastAPI,Path,Query

# 创建 FastAPI 应用实例，整个 Web 服务的入口
app = FastAPI()


# 注册 GET 路由：访问根路径 "/" 时执行该函数
# 返回值会自动序列化成 JSON 响应
@app.get("/")
async def read_root():
    return {"Hello": "World1231412"}


# 路径参数写法：{name} 是占位符，会作为参数传给函数
# 访问 /hello/ldd 时，name 的值就是 "ldd"
@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello, {name}!"}


# 访问/hello 响应结果msg：你好 fastapi
@app.get("/hello")
# 异步函数
async def say_hello_fastapi():
    return {"msg": "你好 fastapi"}

# 练习/user/hello/带参数
@app.get("/user/hello/{name}")
async def user_hello(name: str):
    return {"msg": f"{name}正在学习fastapi"}

# 有关参数的练习
# 访问 /user/hello?name=ldd 时，name 的值就是 "ldd"
@app.get("/book/{bookid}")
async def user_hello_query(bookid: int):
    return {"msg": f"book{bookid}正在被看"}

@app.get("/user/{id}/{name}")
async def user_info(id: int=Path(..., gt=0,lt=100), description="书籍id,1-100"):
    return {"id": id}

# 需求：查找书籍的作者，路径参数，长度范围2-10
@app.get("/author/{name}")
async def book_author(name: str = Path(..., min_length=2, max_length=10, description="作者名称，长度范围2-10")):
    return {"author": name}

# 请求体参数 post put
from pydantic import BaseModel
from pydantic import Field
class User(BaseModel):
    username: str
    password: str

# 提供数据给服务器
@app.post("/register/")
async def register_user(user: User):
    return {"msg": f"用户 {user.username} 已注册"}

# 练习
class library(BaseModel):
    bookname: str=Field(default="人民", description="书籍名称")
    bookauthor: str
    bookaddress: str
    bookprice: float

@app.post("/library/")
async def add_book(book: library):
    return {"msg": f"书籍 {book.bookname} 已添加到图书馆"}

# JSON HTML 响应模型
from fastapi.responses import HTMLResponse, JSONResponse
@app.get("/html", response_class=HTMLResponse)
async def get_html():
    html_content = """
    <html>
        <head>
            <title>FastAPI HTML Response</title>
        </head>
        <body>
            <h1>Hello, FastAPI!</h1>
            <p>This is an HTML response.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# 需求 按id查询新闻 1-6
from fastapi import HTTPException
@app.get("/news/{id}")
async def get_news(id: int = Path(..., gt=0, lt=100, description="新闻ID,范围1-6")):
    news_data = {
        1: {"title": "新闻1", "content": "这是新闻1的内容"},
        2: {"title": "新闻2", "content": "这是新闻2的内容"},
        3: {"title": "新闻3", "content": "这是新闻3的内容"},
        4: {"title": "新闻4", "content": "这是新闻4的内容"},
        5: {"title": "新闻5", "content": "这是新闻5的内容"},
        6: {"title": "新闻6", "content": "这是新闻6的内容"},
    }
    if id in news_data:
        return JSONResponse(content=news_data[id], status_code=200)
    else:
        raise HTTPException(status_code=404, detail="新闻未找到,404not found!")

# 中间件
from fastapi import Request
@app.middleware("http")
async def log_request(request: Request, call_next):
    # 在请求处理之前执行的逻辑
    print("中间件1开始处理 -- start")
    response = await call_next(request)
    print("中间件1处理完成 -- end")
    # 在请求处理之后执行的逻辑
    return response


@app.middleware("http")
async def log_request(request: Request, call_next):
    # 在请求处理之前执行的逻辑
    print("中间件2开始处理 -- start")
    response = await call_next(request)
    print("中间件2处理完成 -- end")
    # 在请求处理之后执行的逻辑
    return response

@app.get("/middlewaretest")
async def middleware_test():
    return {"msg": "ldd这是一个中间件测试接口"}


#依赖注入
#1创建依赖项 2导入Depends 3声明依赖项
from fastapi import Depends,Query,FastAPI,HTTPException
#1 创建依赖项：一个普通的函数（也可以是类）即可，参数照样会做类型校验
async def common_parameters(ldd: str = None, skip: int = 0, limit: int = 100):
    return {"query": ldd, "skip": skip, "limit": limit}

#3 声明依赖项：在路径操作函数的参数上使用 Depends(依赖项)
#FastAPI 会自动调用 common_parameters，把返回值注入给 commons
@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons

#同一个依赖项可以被多个接口复用
@app.get("/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    return {"msg": "用户列表", **commons}

#依赖项也可以写在装饰器上：只执行逻辑，返回结果不注入函数参数
def verify_token(token: str = None):
    if token != "ldd":
        raise HTTPException(status_code=401, detail="token 无效")
    return token

@app.get("/profile/", dependencies=[Depends(verify_token)])
async def get_profile():
    return {"msg": "profile 数据"}


#依赖项可以嵌套：子依赖的结果注入给父依赖
async def user_dependency(commons: dict = Depends(common_parameters)):
    return {"user": "ldd", **commons}

@app.get("/order/")
async def read_order(user: dict = Depends(user_dependency)):
    return {"msg": "订单列表", "user": user["user"], "limit": user["limit"]}

