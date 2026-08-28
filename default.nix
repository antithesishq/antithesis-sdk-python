{ pkgs ? import <nixpkgs> {} }:

let
  sdk_version = (builtins.fromTOML(builtins.readFile( ./pyproject.toml))).project.version;
  sdk = with pkgs;
  python3.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python";
    version = sdk_version;
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python3.pkgs; [
      wheel
      build
      setuptools
    ];
  };
  sdk_with_docs = pkgs.python3.withPackages (ps: [
      sdk
      ps.pdoc
    ]);
  docs = pkgs.runCommand "make_docs" {} ''
      mkdir -p $out
      ln -s ${./src/antithesis} antithesis_sdk
      ${sdk_with_docs}/bin/python -m pdoc -d google --no-show-source -o $out -n antithesis
    '';

  # The tests import the *installed* package (sdk_constants resolves the
  # SDK version through importlib.metadata), so the test env must carry the
  # built SDK, not just its dependencies.
  check = pkgs.runCommand "antithesis-sdk-python-pytest" {
      nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ sdk ps.pytest ])) ];
    } ''
      cp -r ${./.} pkg
      chmod -R u+w pkg
      cd pkg
      python -m pytest tests -q -p no:cacheprovider
      touch $out
    '';
in {
    inherit sdk docs check;
  }
