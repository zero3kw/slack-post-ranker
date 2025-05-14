FROM python:3.11-slim

RUN apt-get update -y \
  && apt-get install -y curl \
  && pip install --upgrade pip \
  &&  pip install requests \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*