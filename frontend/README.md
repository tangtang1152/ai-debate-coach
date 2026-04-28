# 论点攻防前端原型

这是一个原生 HTML/CSS/JS 单页前端，用于对接已完成的 Flask 后端接口。

## 文件

- `index.html`：页面结构
- `styles.css`：界面样式
- `app.js`：状态管理、SSE 解析、接口调用

## 预览

推荐在本目录启动静态服务：

```bash
python3 -m http.server 5173
```

然后访问：

```text
http://127.0.0.1:5173
```

页面只保留正式后端模式，需要先启动后端服务。

## 对接后端

1. 启动 Flask 后端，默认地址：

```text
http://127.0.0.1:8000
```

2. 确认页面右上角 API 输入框为：

```text
http://127.0.0.1:8000
```

3. 依次完成：

- 创建会话：`POST /api/debate/start`
- 三回合流式辩论：`POST /api/debate/stream`
- 赛后评分：`POST /api/debate/evaluate`

## 注意

如果前端使用 `http://127.0.0.1:5173`、后端使用 `http://127.0.0.1:8000`，需要后端允许该前端来源。当前后端已为本地 `5173` 前端配置 CORS。

可选处理方式：

- 后端增加 Flask-CORS。
- 使用前端开发服务器代理 `/api` 到后端。
- 将前端静态文件交给 Flask 同源托管。
