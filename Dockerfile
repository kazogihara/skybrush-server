# Baseimage
FROM ubuntu:22.04

# Working Directory
WORKDIR /app

# Port
EXPOSE 5000/tcp 
EXPOSE 5001/tcp 
EXPOSE 14550/udp 

# Install Packages
RUN apt-get -y update && apt-get -y upgrade
RUN apt-get install -y curl
RUN apt-get install -y npm
RUN apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev
RUN wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
RUN tar -xf Python-3.12.0.tgz
RUN cd Python-3.12.*/ && ./configure --enable-optimizations && make && make install
RUN pip3.12 install poetry

# Copy source code
WORKDIR /app/skybrush-server
COPY ./skybrush-server .

# Build Skybrush Server
RUN poetry install

# Run Skybrush Server
ENTRYPOINT ["poetry", "run", "skybrushd", "-c"]
CMD ["etc/conf/skybrush-outdoor.jsonc"]
