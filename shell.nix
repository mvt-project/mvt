with import <nixpkgs> {};
with python38Packages;

buildPythonPackage rec {
  name = "mvt";
  src = ./.;
  propagatedBuildInputs = [ pkgs.libusb1 libusb1 ];
  nativeBuildInputs = [ pkgs.libusb1 ];
}

