# Bio-Motion Evaluator — cliente React (Vite build + nginx)
FROM node:20-alpine AS build

WORKDIR /app

COPY appWeb/package.json appWeb/package-lock.json ./
RUN npm ci

COPY appWeb/ .

# Demo jurado por defecto; sobrescribible con build args.
ARG VITE_MVP_DEMO_MODE=true
ARG VITE_MVP_SHOW_DEV=false
ARG VITE_MVP_SHOW_SPRINT4=false
ARG VITE_MVP_SHOW_3D=false
ARG VITE_MVP_SHOW_ADV_VIDEO=false
ARG VITE_MVP_SHOW_LIVE_EXERCISE=false
ARG VITE_MVP_SHOW_REP_GOAL=false

ENV VITE_MVP_DEMO_MODE=$VITE_MVP_DEMO_MODE \
    VITE_MVP_SHOW_DEV=$VITE_MVP_SHOW_DEV \
    VITE_MVP_SHOW_SPRINT4=$VITE_MVP_SHOW_SPRINT4 \
    VITE_MVP_SHOW_3D=$VITE_MVP_SHOW_3D \
    VITE_MVP_SHOW_ADV_VIDEO=$VITE_MVP_SHOW_ADV_VIDEO \
    VITE_MVP_SHOW_LIVE_EXERCISE=$VITE_MVP_SHOW_LIVE_EXERCISE \
    VITE_MVP_SHOW_REP_GOAL=$VITE_MVP_SHOW_REP_GOAL

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY appWeb/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
