# Router

These Dockerfiles represent a router in the generated architecture.

2 versions are available:
- [Dockerfile](./Dockerfile) for the router without CLT.
- [Dockerfile_clt](./Dockerfile_clt) for the router with CLT.

## Reduce size for router with CLT

By using the command `docker build -t router_clt -f Dockerfile_clt .`, the image will be approximately 189MB.

The size of the image can be reduced down to approximately 36MB by using [Docker Squash](https://github.com/goldmann/docker-squash).

If you have Python >= 3.6, you can do the following:
```bash
pip3 install docker-squash # you might need to update your PATH, check the logs
docker build -t router_clt -f Dockerfile_clt .
docker-squash router_clt -t router_clt
```
