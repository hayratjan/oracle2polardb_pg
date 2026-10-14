# 前端镜像：多阶段构建（node 构建 → nginx 托管）
# v2.4.4 新增：与 docker-compose 的 frontend profile 配套使用

# ─── 阶段 1：构建 ───
FROM node:22-alpine AS builder
WORKDIR /app

# 先拷贝依赖清单，利用 Docker 层缓存
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# VITE_API_BASE_URL 留空 → 前端请求走相对路径，由 nginx 同源反代到后端，
# 彻底避免跨域 CORS 问题（也可构建时指向独立后端域名）
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . .
RUN pnpm build

# ─── 阶段 2：运行 ───
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
