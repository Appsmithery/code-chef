.\scripts\build_all.ps1 -EnvFile config/env/.env `
                        -ComposeFile compose/docker-compose.yml `
                        -Profiles agents,infra,rag `
                        -Registry registry.digitalocean.com/the-shop-infra `
                        -ImageTag $(git rev-parse --short HEAD) `
                        -Push