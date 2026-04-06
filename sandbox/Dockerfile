FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends iptables && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas>=2.2.0 \
    scipy>=1.12.0 \
    matplotlib>=3.8.0 \
    requests>=2.32.0 \
    numpy>=1.26.0

COPY iptables_rules.sh /usr/local/bin/iptables_rules.sh
RUN chmod +x /usr/local/bin/iptables_rules.sh

RUN useradd --create-home --shell /bin/bash sandboxuser
USER sandboxuser
WORKDIR /workspace

CMD ["python", "--version"]
