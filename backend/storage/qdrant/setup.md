# Install Qdrant (if not installed)
curl -L https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-gnu.tar.gz -o qdrant.tar.gz
tar -xzf qdrant.tar.gz
sudo mv qdrant /usr/local/bin/
rm qdrant.tar.gz

# Create data directory
mkdir -p "/mnt/e/code/Course Code/AgentSystem/AI-Trip-Planner/backend/storage/qdrant"

# Start Qdrant
qdrant --storage-path "/mnt/e/code/Course Code/AgentSystem/AI-Trip-Planner/backend/storage/qdrant" --http-port 6333

# Test (in another terminal)
curl -sf http://127.0.0.1:6333/health && echo " - Qdrant OK"