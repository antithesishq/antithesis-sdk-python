{ pkgs ? import <nixpkgs> {} }:

let
  sdk_version = (builtins.fromTOML(builtins.readFile( ./pyproject.toml))).project.version;
  sdk = with pkgs;
  python312.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python";
    version = sdk_version;
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python312.pkgs; [
      wheel
      build
      setuptools
      cython
      cffi
    ];
  };
  sdk_with_docs = pkgs.python312.withPackages (ps: [
      sdk
      ps.pdoc
    ]);
  docs = pkgs.runCommand "make_docs" {} ''
      mkdir -p $out
      ln -s ${./src/antithesis} antithesis_sdk
      ${sdk_with_docs}/bin/python -m pdoc -d google --no-show-source -o $out -n antithesis
    '';
in {
    inherit sdk docs;
  }
