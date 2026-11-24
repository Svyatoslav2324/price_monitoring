"""Install the Camoufox build used for local parser tests."""
from camoufox.addons import DefaultAddons, maybe_download_addons
from camoufox.locale import download_mmdb
from camoufox.pkgman import CamoufoxFetcher, Version


class TestedBrowser(CamoufoxFetcher):
    def get_asset(self):
        version = Version(version="159.0", release="beta.43")
        tag = f"{version.version}-{version.release}"
        filename = f"camoufox-{tag}-lin.{self.arch}.zip"
        return version, f"https://github.com/daijro/camoufox/releases/download/v{tag}/{filename}"


if __name__ == "__main__":
    TestedBrowser().install()
    download_mmdb()
    maybe_download_addons(list(DefaultAddons))
