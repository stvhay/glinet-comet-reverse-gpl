{
  description = "GL.iNet Comet (RM1) firmware reverse engineering environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              # Firmware analysis
              binwalk
              squashfsTools
              dtc

              # Binary analysis
              file
              xxd
              hexdump

              # General utilities
              curl
              jq

              # Device extraction
              sshpass
              openssh

              # Development
              shellcheck

              # Python toolchain and development tools
              # NOTE: Python package dependencies are managed in pyproject.toml
              #       This just provides the tools (linters, formatters, test runners)
              python311                     # Python interpreter
              ruff                          # Python linter and formatter
              python311Packages.mypy        # Type checking
              python311Packages.pytest      # Test runner
              python311Packages.pytest-cov  # Test coverage reporting

              # Python runtime dependencies (needed for scripts to run)
              # TODO: Migrate to `uv` package manager (from pyproject.toml)
              #       For now, provided by nix for reproducibility
              python311Packages.jinja2
              python311Packages.tomlkit
            ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
              # Linux-only tools
              rkdeveloptool
            ];

            shellHook = ''
              echo "GL.iNet Comet (RM1) reverse engineering environment"
              echo "Firmware URL: https://fw.gl-inet.com/kvm/rm1/release/glkvm-RM1-1.7.2-1128-1764344791.img"
            '';
          };
        });
    };
}
