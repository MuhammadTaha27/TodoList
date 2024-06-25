# main.py
from contextlib import asynccontextmanager
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated,List
from todo import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, ForeignKey
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel
from todo.auth.auth_bearer import create_jwt_token, get_current_user 


 

class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    

class DoneTodo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


    
class LoginRequest(BaseModel):
    email: str
    password: str    

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    password: str    

class Userdata(BaseModel):
    user_id: int
    username: str
    exp: int    


origins = [
    "http://localhost",
    "http://localhost:3000",  # Update with your frontend URL
]

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/")
def read_root():
    return {"Hello": "World"}
    
    
@app.put("/todos/{todo_id}/done/")
def mark_todo_as_done(todo_id: int,user_data: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    user = Userdata(**user_data)
    user_id = user.user_id
    todo = session.exec(select(Todo).where((Todo.id == todo_id)& (Todo.user_id == user_id))).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    done_todo = DoneTodo(content=todo.content, user_id = user_id)
    session.add(done_todo)
    session.delete(todo)
    session.commit()
    return {"message": "Todo marked as done successfully"}
  
@app.get("/done_todos/", response_model=list[DoneTodo])
def read_done_todos(user_data: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    user = Userdata(**user_data)
    user_id = user.user_id
    done_todos = session.exec(select(DoneTodo).where(DoneTodo.user_id == user_id)).all()
    if not done_todos:
        return{"message":"No entry in the database"}
    else:
        return done_todos

@app.post("/done_todos/", response_model=DoneTodo)
def create_todo(donetodo: DoneTodo, user_data: Annotated[dict, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    user = Userdata(**user_data)
    user_id = user.user_id
    donetodo.user_id = user_id  
    session.add(donetodo)
    session.commit()
    session.refresh(donetodo)
    return donetodo



@app.post("/todos/", response_model=Todo)
def create_todo(todo: Todo, user_data: Annotated[dict, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    user = Userdata(**user_data)
    user_id = user.user_id
    todo.user_id = user_id  
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


@app.get("/todos/", response_model=List[Todo])
def read_todos_by_user(user_data: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    user = Userdata(**user_data)
    user_id = user.user_id
    todos = session.exec(select(Todo).where(Todo.user_id == user_id)).all() 
    return todos

@app.get("/todos/{todo_id}/", response_model=Todo)
def read_todo(todo_id: int, user_data: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    user = Userdata(**user_data)
    user_id = user.user_id
    todo = session.exec(select(Todo).where((Todo.id == todo_id) & (Todo.user_id == user_id))).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
    

@app.delete("/todos/{todo_id}/")
def delete_todo(todo_id: int, user_data: Annotated[dict, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    user = Userdata(**user_data)
    user_id = user.user_id
    todo = session.exec(select(Todo).where((Todo.id == todo_id)& (Todo.user_id == user_id))).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    session.delete(todo)
    session.commit()
    return {"message": "Todo deleted successfully"}

@app.put("/todos/{todo_id}/", response_model=Todo)
def update_todo(todo_id: int, updated_todo: Todo, user_data: Annotated[dict, Depends(get_current_user)], session: Annotated[Session, Depends(get_session)]):
    user = Userdata(**user_data)
    user_id = user.user_id
    todo = session.exec(select(Todo).where((Todo.id == todo_id)& (Todo.user_id == user_id))).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.content = updated_todo.content
    session.commit()
    session.refresh(todo)
    return todo



@app.post("/signup", response_model=User)
def register_user(user: User, session: Annotated[Session, Depends(get_session)]):
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message":"user created successfully"}



@app.post("/login", response_model=dict)
def login_user(user: LoginRequest, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.email == user.email)).first()
    if db_user:
        if user.password == db_user.password:
            if db_user.id is not None:
                jwt_token = create_jwt_token(db_user.id, db_user.username)
                return {"user": db_user, "token": jwt_token}
            else:
                raise HTTPException(status_code=500, detail="User ID is None")
        else:
            raise HTTPException(status_code=400, detail="Incorrect password")
    else:
        raise HTTPException(status_code=404, detail="User not found")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)