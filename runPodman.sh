PROJECTNAME="wokabetrena"
echo "Project name $PROJECTNAME"
IMAGENAME="localhost/$PROJECTNAME"
echo "Image name: $IMAGENAME"
IMAGE_ID=$(podman images -q --filter reference=$IMAGENAME | head -1)
echo "Image ID: $IMAGE_ID"
echo "Start podman"
podman run -d --name $PROJECTNAME -v ./certs/cert.pem:/app/certs/certs.pem:Z -v ./certs/key.pem:/app/certs/key.pem:Z -p 8443:8443  -v trainerdata:/app/instance:Z --replace $IMAGE_ID
#delet dangling images
echo "Clean UP dangling"
podman images -q -f "dangling=true" | xargs -r podman rmi -f
sleep 5
IP=$(podman inspect $PROJECTNAME --format '{{.NetworkSettings.IPAddress}}')
echo "$IMAGENAME IP: $IP"

podman images -q --filter reference=$IMAGENAME | head -1