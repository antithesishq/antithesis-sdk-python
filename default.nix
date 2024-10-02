let
  pkgs = import <nixpkgs> {};
  sdk_version = (builtins.fromTOML(builtins.readFile( ./pyproject.toml))).project.version;
in
  with pkgs;
  python3.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python";
    version = sdk_version;
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python3.pkgs; [
      setuptools
      cython
      cffi
    ];
  }
