FROM node:20-alpine AS build 

WORKDIR /dashboard 

COPY ./package*.json . 

RUN npm i 

COPY . . 

RUN npm run build 



FROM nginx:1.29-alpine-slim 

COPY ./config /etc/nginx 

COPY --from=build /dashboard/dist /usr/share/nginx/html 

EXPOSE 80