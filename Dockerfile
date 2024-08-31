FROM debian:bookworm-slim AS bench

LABEL author=frappé

ARG GIT_REPO=https://github.com/frappe/bench.git
ARG GIT_BRANCH=v5.x

# Create the sources.list if it doesn't exist
RUN [ -f /etc/apt/sources.list ] || echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list

# Use an alternative mirror and add retry logic
RUN sed -i 's|http://deb.debian.org/debian|http://ftp.us.debian.org/debian|g' /etc/apt/sources.list && \
    apt-get update || apt-get update --allow-releaseinfo-change && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    git \
    mariadb-client \
    postgresql-client \
    gettext-base \
    wget \
    libssl-dev \
    fonts-cantarell \
    xfonts-75dpi \
    xfonts-base \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    locales \
    build-essential \
    cron \
    curl \
    vim \
    sudo \
    iputils-ping \
    watch \
    tree \
    nano \
    less \
    software-properties-common \
    bash-completion \
    libpq-dev \
    libffi-dev \
    liblcms2-dev \
    libldap2-dev \
    libmariadb-dev \
    libsasl2-dev \
    libtiff5-dev \
    libwebp-dev \
    redis-tools \
    rlwrap \
    tk8.6-dev \
    ssh-client \
    net-tools \
    make \
    libbz2-dev \
    libsqlite3-dev \
    zlib1g-dev \
    libreadline-dev \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    liblzma-dev \
    file \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales

# The rest of your Dockerfile remains the same
