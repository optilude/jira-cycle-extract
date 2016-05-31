FROM python:2-onbuild
MAINTAINER Martin Aspeli <optilude@gmail.com>

WORKDIR /data
VOLUME /data

ENTRYPOINT [ "jira-cycle-extract" ]