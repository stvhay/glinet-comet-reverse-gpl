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
