FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl build-essential

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Upgrade build tools
RUN pip install --upgrade pip setuptools wheel

# Optionally install cython first if sticking with PyYAML 5.4.1
RUN pip install cython

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
