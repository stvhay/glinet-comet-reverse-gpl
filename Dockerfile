FROM nixos/nix:2.28.3

# Enable flakes
RUN echo "experimental-features = nix-command flakes" >> /etc/nix/nix.conf

# Layer 1: Build Nix dev shell closure (cached unless flake changes)
COPY flake.nix flake.lock /build/
WORKDIR /build
RUN nix develop --command true

# Layer 2: Pre-install Python dependencies
COPY pyproject.toml uv.lock /build/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN nix develop --command uv sync --frozen

# Runtime
WORKDIR /workspace
ENTRYPOINT ["nix", "develop", "/build", "--command"]
CMD ["bash"]
