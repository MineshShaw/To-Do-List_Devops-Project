# Stage 1: Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json .
COPY index.html app.js style.css ./

RUN npm run build

# Stage 2: Production stage
FROM nginx:alpine AS production

# Create non-root user
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser

# Copy built files to nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Change ownership of nginx directories to non-root user
RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d

# Make nginx pid file writable
RUN touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
