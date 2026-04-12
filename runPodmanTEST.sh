#!/bin/bash
PROJECTNAME="wokabetrena"
echo "Project name $PROJECTNAME"
IMAGENAME="localhost/$PROJECTNAME"
echo "Image name: $IMAGENAME"
IMAGE_ID=$(podman images -q --filter reference=$IMAGENAME | head -1)
echo "Image ID: $IMAGE_ID"
echo "Start podman"
podman run -d --name $PROJECTNAME -e VT_DB_FLAG='./instance/test_db_initialized.flag'  -e VT_DB_NAME='test_vocab.db'  -v ./certs/cert.pem:/app/certs/certs.pem:Z -v ./certs/key.pem:/app/certs/key.pem:Z -p 9443:8443  -v trainerdata:/app/instance:Z --replace $IMAGE_ID
#delete dangling images
echo "Clean UP dangling"
podman images -q -f "dangling=true" | xargs -r podman rmi -f
sleep 5
IP=$(podman inspect $PROJECTNAME --format '{{.NetworkSettings.IPAddress}}')
echo "$IMAGENAME IP: $IP"

podman images -q --filter reference=$IMAGENAME | head -1