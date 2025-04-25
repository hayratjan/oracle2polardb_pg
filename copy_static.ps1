# 创建目录（如果不存在）
New-Item -ItemType Directory -Force -Path "static\css"
New-Item -ItemType Directory -Force -Path "static\js"
New-Item -ItemType Directory -Force -Path "static\fonts"
New-Item -ItemType Directory -Force -Path "static\webfonts"

# 复制Bootstrap文件
Copy-Item "static\bootstrap-5.3.5\css\bootstrap.min.css" -Destination "static\css\" -Force
Copy-Item "static\bootstrap-5.3.5\js\bootstrap.bundle.min.js" -Destination "static\js\" -Force

# 复制Font Awesome字体文件
Copy-Item "static\fonts\fa-solid-900.woff2" -Destination "static\webfonts\" -Force

# 复制其他已有的静态文件
Copy-Item "static\css\all.min.css" -Destination "static\css\" -Force
Copy-Item "static\css\content.css" -Destination "static\css\" -Force
Copy-Item "static\js\jquery.min.js" -Destination "static\js\" -Force
Copy-Item "static\js\chart.min.js" -Destination "static\js\" -Force 