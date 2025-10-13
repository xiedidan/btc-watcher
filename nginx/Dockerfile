FROM nginx:1.25-alpine

# 复制配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 暴露端口
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
