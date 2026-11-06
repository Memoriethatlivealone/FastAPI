# ============================================================
# 这个文件的整体流程（从上到下按顺序执行）：
#   步骤 1：导入需要的库
#   步骤 2：创建 FastAPI 应用对象
#   步骤 3：创建"异步数据库引擎"（连接 MySQL 的入口）
#   步骤 4：定义基类 Base（放公共字段，不是表）
#   步骤 5：定义 Book 模型类（对应数据库里的 books 表）
#   步骤 6：定义建表函数
#   步骤 7：把建表函数挂到应用启动事件上
#   步骤 8：定义一个测试接口 /
#
# 运行方式：
#   1) 先确保本地 MySQL 已启动，并且数据库 FastAPI_first 已创建：
#        mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS FastAPI_first CHARACTER SET utf8mb4;"
#   2) 启动服务：
#        uv run uvicorn orm:app --reload
#   3) 浏览器访问 http://127.0.0.1:8000
# ============================================================


# ------------------------------------------------------------
# 步骤 1：导入需要的库
# ------------------------------------------------------------
# datetime：Python 自带的日期时间类型。
#   注意这里导入的是"类"，不是模块，所以可以直接写 datetime.now()。
#   （如果写成 import datetime，就只能写 datetime.datetime.now()）
from datetime import datetime

# os：读取环境变量（数据库账号密码不写死在代码里）
import os

# quote_plus：对密码里的特殊字符做 URL 编码，避免连接串被截断
from urllib.parse import quote_plus

# create_async_engine：创建"异步"数据库引擎（配合 async/await 使用）
from sqlalchemy.ext.asyncio import create_async_engine

# FastAPI：Web 框架，app 就是基于它创建的
from fastapi import FastAPI

# DeclarativeBase：SQLAlchemy 2.x 的 ORM 基类，模型类都继承它
# Mapped：类型注解，告诉 SQLAlchemy 这个属性的 Python 类型
# mapped_column：把类属性映射成数据库表的列，并配置主键、默认值等
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 具体的列类型：
#   String   → VARCHAR
#   DateTime → DATETIME
#   Numeric  → DECIMAL，适合存金额（精确小数）
#   func     → 调用数据库函数，比如 func.now() 表示数据库当前时间
from sqlalchemy import String, DateTime, func, Numeric, select

# 异步会话类 AsyncSession：用它来操作数据库（增删改查）
from sqlalchemy.ext.asyncio import  create_async_engine,AsyncSession
# sessionmaker：创建"会话工厂"，用它生成 AsyncSession 对象
from sqlalchemy.orm import sessionmaker

from fastapi import Depends, Query, FastAPI, HTTPException

# ------------------------------------------------------------
# 步骤 2：创建 FastAPI 应用对象
# ------------------------------------------------------------
# uvicorn 命令里的 "orm:app" 就是"文件 orm.py 里的 app 变量"。
# 这个名字不能乱改，否则启动命令也要跟着改。
app = FastAPI()


# ------------------------------------------------------------
# 步骤 3：配置数据库连接
# ------------------------------------------------------------
# 连接串格式：数据库驱动://用户名:密码@主机:端口/数据库名?参数
#   mysql+aiomysql → 使用 aiomysql 这个异步驱动连接 MySQL
#   charset=utf8   → 字符编码（新库建议用 utf8mb4，能存 emoji）
#
# 账号密码不写死在代码里，从环境变量读取，避免密码被提交到仓库。
# 运行前先设置环境变量（或者把 .env.example 复制成 .env，用
# `set -a; source .env; set +a` 加载）：
#   export DB_USER=root
#   export DB_PASSWORD=你的密码
#   export DB_HOST=localhost
#   export DB_PORT=3306
#   export DB_NAME=FastAPI_first
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "FastAPI_first")

ASYNC_DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8"
)

# 创建异步引擎（相当于"连接池管理器"）
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # True 表示在控制台打印执行的 SQL，调试时很有用；上线时设为 False
    pool_size=10,  # 连接池里常驻的连接数
    max_overflow=20,  # 连接池用满后，最多再临时创建多少连接
)


# ------------------------------------------------------------
# 步骤 4：定义基类 Base（抽象，不生成表）
# ------------------------------------------------------------
# 继承 DeclarativeBase 后，Base 就成了所有模型类的"父类"。
# 它有 __tablename__ 吗？没有 → 所以它不会在数据库里生成表。
# 它的作用是：把"每个表都要有的公共字段"写一次，子类自动继承。
class Base(DeclarativeBase):
    # 创建时间：插入数据时，默认取数据库的当前时间（func.now()）
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        insert_default=func.now(),  # INSERT 时自动填当前时间
        comment="创建时间",  # 列的注释（会写进 MySQL 表结构里）
    )
    # 更新时间：插入时取当前时间；每次 UPDATE 时也自动刷新
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        insert_default=func.now(),  # INSERT 时填当前时间
        onupdate=func.now(),  # UPDATE 时自动更新为当前时间
        comment="修改时间",
    )


# ------------------------------------------------------------
# 步骤 5：定义 Book 模型类（会生成 books 表）
# ------------------------------------------------------------
# 继承 Base 后：
#   1) 自动拥有 create_time / update_time 两个字段
#   2) 只要写了 __tablename__，SQLAlchemy 就会为它建表
class Book(Base):
    __tablename__ = "books"  # 数据库里的表名

    # 主键 id：自增，不用手动传
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="书籍id")
    # 书名：VARCHAR(255)，不允许为空
    # 注意 mapped_column 的第一个"位置参数"是列类型，必须写在前面
    bookname: Mapped[str] = mapped_column(String(255), nullable=False, comment="书名")
    # 作者
    author: Mapped[str] = mapped_column(String(255), nullable=False, comment="作者")
    # 价格：DECIMAL(10, 2) 表示总共 10 位、小数 2 位，适合金额
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, comment="价格")
    # 出版社
    publisher: Mapped[str] = mapped_column(String(255), nullable=False, comment="出版社")

# 创建用户表 主键用户id 用户名 密码 创建时间 更新时间
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户id")
    username: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")

# ------------------------------------------------------------
# 步骤 6：定义建表函数
# ------------------------------------------------------------
async def create_tables():
    # async_engine.begin()：开启一个事务，结束时自动 commit
    async with async_engine.begin() as conn:
        # run_sync：SQLAlchemy 的建表接口是同步的，这里把它放到异步连接上执行
        # metadata 里记录了所有继承 Base 的模型，create_all 会为尚未存在的表建表
        await conn.run_sync(Base.metadata.create_all)


# ------------------------------------------------------------
# 步骤 7：应用启动时自动建表
# ------------------------------------------------------------
# @app.on_event("startup") 表示：FastAPI 启动的那一刻执行下面的函数。
# （这个写法在新版 FastAPI 中已标记为"弃用"，但当前版本仍可正常使用。）
@app.on_event("startup")
async def startup_event():
    await create_tables()


# ------------------------------------------------------------
# 步骤 8：定义一个测试接口
# ------------------------------------------------------------
# 访问 GET / 时返回一段 JSON，用来确认服务确实起来了
@app.get("/")
async def read_root():
    return {"Hello": "World"}

# 路由
# 创建会话工厂  查询图书 依赖注入路由处理函数
AsyncSessionLocal = sessionmaker(
    bind=async_engine,#绑定数据库引擎
    class_=AsyncSession, #指定会话类
    expire_on_commit=False#提交后不会过期，不会重新查询数据库
    )
# 依赖项
async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session #返回数据库会话给路由处理函数
            await session.commit()#提交事务
        except Exception as e:
            await session.rollback()#回滚事务
            raise e
        finally:
            await session.close()#关闭会话

@app.get("/book/books/{book_id}")   
async def get_books(book_id: int, db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book).where(Book.id==book_id))
    # book = result.scalars().all()#.all获取的所有
    # book1= result.scalars().first()#查单条
    # book2=await db.get(Book,2) #根据bookname查询单条数据
    book3=result.scalar_one_or_none()#查单条
    return book3
#try