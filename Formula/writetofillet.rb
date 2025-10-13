class Writetofillet < Formula
  desc "Multithreaded file pumper CLI"
  homepage "https://github.com/supermarsx/writetofillet"
  version :latest

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/supermarsx/writetofillet/releases/latest/download/writetofillet-macos-arm64"
      sha256 :no_check
    else
      url "https://github.com/supermarsx/writetofillet/releases/latest/download/writetofillet-macos-x64"
      sha256 :no_check
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/supermarsx/writetofillet/releases/latest/download/writetofillet-linux-arm64"
      sha256 :no_check
    else
      url "https://github.com/supermarsx/writetofillet/releases/latest/download/writetofillet-linux-x64"
      sha256 :no_check
    end
  end

  def install
    asset = Dir["writetofillet-*"][0]
    chmod 0755, asset
    bin.install asset => "writetofillet"
  end

  test do
    system "#{bin}/writetofillet", "--help"
  end
end

