FROM ubuntu:14.04

RUN apt-get update -q && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      curl \
      ca-certificates \
      git-core \
      ruby2.0 && \
    update-alternatives --install /usr/bin/ruby ruby /usr/bin/ruby2.0 1 && \
    update-alternatives --install /usr/bin/gem gem /usr/bin/gem2.0 1 && \
    git clone https://github.com/sstephenson/bats.git /tmp/bats && \
    cd /tmp/bats && ./install.sh /usr/local && cd .. && rm -fr /tmp/bats
