FROM ubuntu:24.04

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    pandoc \
    texlive-latex-recommended \
    texlive-bibtex-extra \
    texlive-extra-utils \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["bash"]
