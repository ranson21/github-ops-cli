FROM python:3.9-slim

# Install git and other dependencies
RUN apt-get update && apt-get install -y \
  git \
  curl \
  jq && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# Copy our utility scripts
COPY github_ops.py /usr/local/bin/
COPY cli.py /usr/local/bin/

# Make the CLI executable
RUN chmod +x /usr/local/bin/cli.py

ENTRYPOINT ["python", "/usr/local/bin/cli.py"]
