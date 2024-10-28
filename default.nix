let
  pkgs = import <nixpkgs> {};
  sdk_version = (builtins.fromTOML(builtins.readFile( ./pyproject.toml))).project.version;
in
  with pkgs;
  python312.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python";
    version = sdk_version;
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python312.pkgs; [
      setuptools
      cython
      cffi
    ];
  }
