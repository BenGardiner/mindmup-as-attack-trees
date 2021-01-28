FROM node:6

WORKDIR /usr/src/app

COPY ../package.json .

RUN mkdir deps.js
COPY ../deps.js/* deps.js/
COPY ../d3.v4.min.js .
COPY ../mupcommon.js .
COPY ../mupstyle.css .
COPY ../webstub.html .

COPY ../rendermup .
COPY ../render_mup.js .

RUN npm install

ENTRYPOINT [ "/usr/src/app/rendermup" ]
