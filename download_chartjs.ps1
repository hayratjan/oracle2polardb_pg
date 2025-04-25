# 创建必要的目录
New-Item -ItemType Directory -Force -Path "static\js"

# 下载 Chart.js
$chartJsUrl = "https://cdn.jsdelivr.net/npm/chart.js/dist/chart.min.js"
Invoke-WebRequest -Uri $chartJsUrl -OutFile "static\js\chart.min.js"

Write-Host "Chart.js 文件下载完成！" 