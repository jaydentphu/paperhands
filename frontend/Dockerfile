# Stage 1: compile the TypeScript/React app to static files.
# node:22 because Vite 8 requires Node 22.12+; alpine keeps the image small.
FROM node:22-alpine AS build
WORKDIR /app
# Copy the lockfile first so this layer is cached until dependencies change,
# not on every source edit.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve those static files. Nothing from stage 1 except dist/ is
# kept - no Node, no node_modules, no source.
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
