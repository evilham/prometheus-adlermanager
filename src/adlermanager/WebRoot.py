# pyright: reportUnusedFunction=false
from typing import cast

import jinja2
import markdown
from jinja2.utils import markupsafe  # type: ignore
from klein import Klein
from klein.resource import KleinResource
from twisted.logger import Logger
from twisted.python.filepath import FilePath
from twisted.web import resource, static
from twisted.web.server import Request

from .AdlerManagerTokenResource import AdlerManagerTokenResource
from .Config import Config
from .SitesManager import SiteManager, SitesManager

log = Logger()


def get_jinja_env(supportDir: str) -> jinja2.Environment:
    """
    Return a L{jinja2.Environment} with templates loaded from:
      - Package
      - Support dir

    @param supportDir: Full path to supportDir.
      See L{authapiv02.DefaultConfig.Config}
    @type supportDir: L{str}
    """
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.toc",
            "markdown.extensions.tables",
        ]
    )
    templates = jinja2.Environment(
        extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
        loader=jinja2.ChoiceLoader(
            [
                jinja2.FileSystemLoader(supportDir),
                jinja2.PackageLoader("adlermanager", "templates"),
            ]
        ),
        autoescape=True,
    )

    def md_filter(txt: str) -> markupsafe.Markup:
        return markupsafe.Markup(md.convert(txt))

    templates.filters["markdown"] = md_filter  # type: ignore
    return templates


def web_root(sites_manager: "SitesManager") -> KleinResource:
    app = Klein()

    @app.route("/")  # type: ignore
    def index(request: Request):
        try:
            host = cast(str, request.getRequestHostname().decode("utf-8"))
        except Exception:
            return resource.ErrorPage(
                400, "Bad cat", '<a href="http://http.cat/400">http://http.cat/400</a>'
            )
        if host not in sites_manager.site_managers:
            return resource.ErrorPage(
                404, "Gone cat", '<a href="http://http.cat/404">http://http.cat/404</a>'
            )
        site: SiteManager
        try:
            site = sites_manager.site_managers[host]
        except Exception:
            log.failure("sad cat")
            return resource.ErrorPage(
                500, "Sad cat", '<a href="http://http.cat/500">http://http.cat/500</a>'
            )

        site_path = cast(  # type: ignore
            str, FilePath(Config.data_dir).child("sites").child(host).path
        )
        templates = get_jinja_env(site_path)
        template = templates.get_template("template.j2")

        return template.render(site=site)

    @app.route("/api/v1/alerts", methods=["POST"])  # type: ignore
    def alert_handler(request: Request):
        return AdlerManagerTokenResource(sites_manager)

    @app.route("/static", branch=True)  # type: ignore
    def static_files(request: Request):
        return static.File(Config.web_static_dir)

    return app.resource()
