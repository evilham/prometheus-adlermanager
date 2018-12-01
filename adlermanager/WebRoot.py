from klein import Klein
from twisted.web import resource, static
from twisted.python.filepath import FilePath

import jinja2
import markdown

from .Config import Config
from .AdlerManagerTokenResource import AdlerManagerTokenResource

def get_jinja_env(supportDir):
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
            'markdown.extensions.toc',
            'markdown.extensions.tables',
        ]
    )
    templates = jinja2.Environment(
        extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'],
        loader=jinja2.ChoiceLoader([
            jinja2.FileSystemLoader(supportDir),
            jinja2.PackageLoader("adlermanager", "templates"),
        ]),
        autoescape=True,
    )
    templates.filters['markdown'] = lambda txt: jinja2.Markup(
        md.convert(txt))
    return templates


def web_root(sites_manager):
    app = Klein()

    @app.route('/')
    def index(request):
        try:
            host = request.getRequestHostname().decode('utf-8')
            print(host)
            site = sites_manager.get_site(host)
        except:
            return resource.ErrorPage(400, 'Bad cat', '<a href="http://http.cat/400">http://http.cat/400</a>')

        site_path = FilePath(Config.data_dir).child("sites").child(host).path
        templates = get_jinja_env(site_path)
        template = templates.get_template("template.j2")

        # TODO: Get and use alert data
        return template.render(**site)

    @app.route('/api/v1/alerts', methods=["POST"])
    def alert_handler(request):
        return AdlerManagerTokenResource(sites_manager)

    @app.route('/static', branch=True)
    def static_files(request):
        return static.File(Config.web_static_dir)

    return app.resource()
