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
  sdk_with_tests = pkgs.python312.withPackages (ps: [
      sdk
      ps.pytest
    ]);
  tests = pkgs.runCommand "run_tests" {} ''
      cp -r ${./.} source
      chmod -R +w source
      cd source
      ${sdk_with_tests}/bin/pytest
      touch $out
    '';
in {
    inherit sdk docs tests;
  }
