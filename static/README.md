# 静态文件下载清单

请手动下载以下文件并放置到对应目录：

## CSS 文件 (放在 static/css 目录)
1. ✅ Bootstrap CSS (已完成)
   - 来源：static\bootstrap-5.3.5\css\bootstrap.min.css
   - 目标位置：static\css\bootstrap.min.css

2. ✅ Font Awesome CSS (已完成)
   - 文件：static\css\all.min.css

3. ✅ 自定义内容样式 (已完成)
   - 文件：static\css\content.css

## JavaScript 文件 (放在 static/js 目录)
1. ✅ Bootstrap Bundle JS (已完成)
   - 来源：static\bootstrap-5.3.5\js\bootstrap.bundle.min.js
   - 目标位置：static\js\bootstrap.bundle.min.js

2. ✅ jQuery (已完成)
   - 文件：static\js\jquery.min.js

3. ✅ Chart.js (已完成)
   - 文件：static\js\chart.min.js

4. SweetAlert2 (待完成)
   - 来源：https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.js
   - 目标文件名：sweetalert2.min.js

## 字体文件 (放在 static/fonts 目录)
- Font Awesome 字体文件 (待完成)
  - 来源：https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.woff2
  - 目标文件名：fa-solid-900.woff2

## 自定义文件
1. ✅ static/css/custom.css (已完成)
2. ✅ static/js/custom.js (已完成)

## 目录结构
当前的目录结构：
```
static/
├── css/
│   ├── bootstrap.min.css
│   ├── all.min.css
│   ├── content.css
│   └── custom.css
├── js/
│   ├── bootstrap.bundle.min.js
│   ├── jquery.min.js
│   ├── chart.min.js
│   └── custom.js
└── fonts/
    └── (待添加字体文件)
```

## 待完成项
1. 下载并添加 SweetAlert2
2. 下载并添加 Font Awesome 字体文件

## 注意事项
由于已经有了 `all.min.css`，我们不再需要单独的 `fontawesome.min.css` 和 `solid.min.css` 文件。

## 操作说明
1. 请将 Bootstrap 文件从 static\bootstrap-5.3.5 复制到对应目录：
   - 将 static\bootstrap-5.3.5\css\bootstrap.min.css 复制到 static\css\bootstrap.min.css
   - 将 static\bootstrap-5.3.5\js\bootstrap.bundle.min.js 复制到 static\js\bootstrap.bundle.min.js

2. 请下载其他列出的文件并放置到对应目录。

3. 完成后，您的目录结构应该如下：
```
static/
├── css/
│   ├── bootstrap.min.css
│   ├── all.min.css
│   ├── content.css
│   └── custom.css
├── js/
│   ├── bootstrap.bundle.min.js
│   ├── jquery.min.js
│   ├── chart.min.js
│   └── custom.js
└── fonts/
    └── fa-solid-900.woff2
``` 