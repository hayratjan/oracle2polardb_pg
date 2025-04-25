# 创建必要的目录
New-Item -ItemType Directory -Force -Path "static\css"
New-Item -ItemType Directory -Force -Path "static\webfonts"

# 下载 Font Awesome CSS
$cssUrl = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"
Invoke-WebRequest -Uri $cssUrl -OutFile "static\css\all.min.css"

# 下载字体文件
$fontUrls = @(
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-solid-900.woff2",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-regular-400.woff2",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/webfonts/fa-brands-400.woff2"
)

foreach ($url in $fontUrls) {
    $fileName = $url.Split('/')[-1]
    Invoke-WebRequest -Uri $url -OutFile "static\webfonts\$fileName"
}

Write-Host "Font Awesome 文件下载完成！" 