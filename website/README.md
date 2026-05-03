# Chattodo Website

Chattodo 官网与基础文档站，使用 `Vite + 原生多页` 实现。

## 本地开发

```powershell
cd website
npm install
npm run dev
```

## 构建

```powershell
cd website
npm run build
```

默认输出目录为 `website/dist/`。

## Netlify 发布

当前生产站点：

- Site URL: https://chattodo-801.netlify.app
- Netlify project: `chattodo-801`
- Project ID: `7c6862ff-c643-46f1-a1e9-85710ef7cb91`

构建配置写在 `netlify.toml`：

```toml
[build]
  command = "npm run build"
  publish = "dist"
```

### 日常生产发布

```powershell
cd website
npm install
npm run build
npx --yes netlify-cli deploy --prod --dir=dist
```

发布成功后，CLI 会输出：

- `Production URL`：正式线上地址
- `Unique deploy URL`：本次发布的唯一版本地址
- `Build logs`：Netlify 后台构建日志

### 预览发布

如果只想先生成一个预览版本，不影响生产站点：

```powershell
cd website
npm run build
npx --yes netlify-cli deploy --dir=dist
```

确认预览无误后，再运行生产发布命令。

### 首次换机器或重新绑定

如果 Netlify CLI 提示未登录：

```powershell
cd website
npx --yes netlify-cli login
```

如果提示当前目录未绑定站点：

```powershell
cd website
npx --yes netlify-cli link --id 7c6862ff-c643-46f1-a1e9-85710ef7cb91
```

绑定状态会保存在本地 `.netlify/state.json`，该目录不需要提交到 Git。
