# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Add a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user

# Set up the user environment
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory to the user's home directory
WORKDIR $HOME/app

# Install python dependencies first to leverage Docker cache
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=user . .

# Create the SQLite DB file and make sure the user owns it, or ensure the directory is writable.
# Actually, SQLAlchemy will create the DB file on startup. We just need the directory to be writable.
RUN mkdir -p /home/user/app/data && chown -R user:user /home/user/app/data
ENV DATABASE_URL="sqlite:////home/user/app/data/finance_tracker.db"

# Expose port
EXPOSE 7860

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
