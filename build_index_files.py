import os.path
import mimetypes

# load settings file
from buildsettings import buildSettings

# load option local settings file
try:
    from localbuildsettings import buildSettings as localBuildSettings
    buildSettings.update(localBuildSettings)
except ImportError:
    pass

class ChDir(object):
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        cwd = self.original_cwd = os.getcwd()
        if self.path is not None and self.path != cwd:
            os.chdir(self.path)
    def __exit__(self, *args):
        if os.getcwd() != self.original_cwd:
            os.chdir(self.original_cwd)

class PathNode(object):
    def __init__(self, path=None, parent=None):
        self.all_children = {}
        if path is None:
            path = ''
        if '/' not in path:
            base_path = path
            sub_path = None
        else:
            base_path = path.split('/')[0]
            sub_path = '/'.join(path.split('/')[1:])
        self.path = base_path
        self.parent = parent
        if parent is not None:
            parent.children[self.path] = self
        self.post_init()
        self.children = {}
        if sub_path is not None:
            self.add_child(sub_path)
    @property
    def root(self):
        r = getattr(self, '_root', None)
        if r is None:
            if self.parent is None:
                r = self._root = self
            else:
                r = self._root = self.parent.root
        return r
    @property
    def full_path(self):
        path = getattr(self, '_full_path', None)
        if path is None:
            if self.parent is not None:
                path = self._full_path = os.path.join(self.parent.full_path, self.path)
            else:
                path = self._full_path = self.path
        return path
    @property
    def is_dir(self):
        return os.path.isdir(self.full_path)
    def post_init(self):
        pass
    def get_relative_path(self, node):
        if self.parent is None:
            return node.full_path
        _node = node
        path_list = []
        while _node is not None:
            path_list.append(_node.path)
            if _node == self:
                break
            _node = _node.parent
        return '/'.join(reversed(path_list))
    def add_child(self, path, cls=None):
        if '/' in path:
            r = path.split('/')[0]
            if r in self.children:
                c = self.children[r]
                c.add_child('/'.join(path.split('/')[1:]))
                return
        if cls is None:
            if os.path.isdir(os.path.join(self.full_path, path)):
                cls = DirNode
            elif path.endswith('.meta.js'):
                cls = ScriptMetaNode
            elif path.endswith('.user.js'):
                cls = ScriptNode
            else:
                cls = FileNode
        c = cls(path, self)
        self.root.all_children[c.full_path] = c
        #self.children[c.path] = c
    def add_node_full(self, path):
        r = self.root
        if '/' not in path:
            if path in r.children:
                return r.children[path]
            return r.add_child(path)
        c = r.children.get(path.split('/')[0])
        if c is not None:
            return c.add_child('/'.join(path.split('/')[1:]))
        return r.add_child(path)
    def find_node(self, path):
        return self.root._find_node(path, path)
    def _find_node(self, path, full_path):
        if full_path == self.full_path:
            return self
        if '/' not in path:
            return
        base = path.split('/')[0]
        child = self.children.get(base)
        if child is None:
            return
        return child._find_node('/'.join(path.split('/')[1:]), full_path)
    def __repr__(self):
        return '<PathNode object at %s> (%s)' % (id(self), self)
    def __str__(self):
        return self.full_path

class DirNode(PathNode):
    node_type = 'dir'
    def post_init(self):
        self.meta_nodes = {}
        self.script_nodes = {}
class FileNode(PathNode):
    node_type = 'file'
    def post_init(self):
        mtype, cencoding = mimetypes.guess_type(self.path)
        self.content_type = mtype
        self.content_encoding = cencoding
class ScriptMetaNode(FileNode):
    attr_map = {
        '@id':'id', 
        '@name':'name', 
        '@category':'category'
    }
    def post_init(self):
        super(ScriptMetaNode, self).post_init()
        self.script_id = self.path.split('.meta.js')[0]
        with open(self.full_path, 'r') as f:
            s = f.read()
        self.meta_attrs = {}
        for line in s.splitlines():
            line = line.strip().strip('\n').lstrip('// ')
            vlist = line.split()
            if not len(vlist):
                continue
            if vlist[0] in self.attr_map:
                key = self.attr_map[vlist[0]]
                val = line.split(vlist[0])[1].strip()
                self.meta_attrs[key] = val
                setattr(self, key, val)
        if not hasattr(self, 'category'):
            self.category = 'None'
        self.parent.meta_nodes[self.script_id] = self
        script_node = self.parent.script_nodes.get(self.script_id)
        if script_node is not None and script_node.meta_node != self:
            script_node.meta_node = self
        
class ScriptNode(FileNode):
    def post_init(self):
        super(ScriptNode, self).post_init()
        self.script_id = self.path.split('.user.js')[0]
        self.meta_node = self.parent.meta_nodes.get(self.script_id)
        self.parent.script_nodes[self.script_id] = self

class HtmlLine(object):
    def __init__(self, s, indent=None):
        self.s = s
        if indent is None:
            indent = 0
        self.indent = indent
    def get_indented(self):
        return ''.join(['\t' * self.indent, self.s])
    
class BaseIndexFile(object):
    add_header_back_button = False
    def get_html(self):
        return '\n'.join([line.get_indented() for line in self.get_document()])
    def get_document(self):
        lines = [
            HtmlLine('<!DOCTYPE html>'),
            HtmlLine('<html>'),
            HtmlLine('<head>'),
        ]
        head = self.get_head()
        for line in head:
            line.indent = 1
        lines.extend(head)
        lines.extend([
            HtmlLine('</head>'),
            HtmlLine('<body>'),
        ])
        body = self.get_body()
        for line in body:
            line.indent = line.indent + 1
        lines.extend(body)
        lines.extend([
            HtmlLine('</body>'),
            HtmlLine('</html>'),
        ])
        return lines
    def get_head(self):
        lines = [
            HtmlLine('<title>%s</title>' % (self.title)),
            HtmlLine('<meta name="viewport" content="width=device-width, initial-scale=1">'),
            HtmlLine('<link rel="stylesheet" href="http://code.jquery.com/mobile/1.4.4/jquery.mobile-1.4.4.min.css" />'),
        ]
        return lines
    def get_body(self):
        lines = self.get_page()
        lines.extend(self.get_foot())
        return lines
    def get_page(self):
        header_back_btn = ''
        if self.add_header_back_button:
            header_back_btn = ' data-add-back-btn="true"'
        lines = [
            HtmlLine('<div data-role="page">'),
            HtmlLine('<div data-role="header"%s>' % (header_back_btn), indent=1),
        ]
        lines.extend(self.get_header(indent=2))
        lines.extend([
            HtmlLine('</div>', indent=1),
            HtmlLine('<div data-role="content">', indent=1),
        ])
        lines.extend(self.get_content(indent=2))
        lines.extend([
            HtmlLine('</div>', indent=1),
            HtmlLine('</div>'),
        ])
        return lines
    def get_header(self, indent):
        return [HtmlLine('<h1>%s</h1>' % (self.title), indent=indent)]
    def get_content(self, indent):
        return [HtmlLine('')]
    def get_foot(self):
        lines = [
            HtmlLine('<script src="http://code.jquery.com/jquery-1.11.1.min.js"></script>'),
            HtmlLine('<script src="http://code.jquery.com/mobile/1.4.4/jquery.mobile-1.4.4.min.js"></script>'),
        ]
        return lines
            
class MainIndexFile(BaseIndexFile):
    def __init__(self, sub_index_files):
        self.sub_index_files = sub_index_files
        self.title = 'IITC Dev Build (nocarryr)'
    @property
    def filename(self):
        return 'index.html'
    def get_content(self, indent):
        lines = [HtmlLine('<ul data-role="listview">')]
        for index_file in self.sub_index_files:
            fn = index_file.filename
            title = index_file.title
            lines.append(HtmlLine('<li><a href="%s">%s</a></li>' % (fn, title), indent=1))
        lines.append(HtmlLine('</ul>'))
        return lines
class IndexFile(BaseIndexFile):
    add_header_back_button = True
    def __init__(self, node, title=None):
        self.node = node
        if title is None:
            title = node.path.title()
        if title == 'Local':
            title = 'Desktop'
        self.title = title
        self.main_script = self.build_nodelink(script_id='total-conversion-build')
        self.category_nodes = {}
        self.build_plugins()
    @property
    def filename(self):
        return '%s.html' % (self.node.path)
    def build_plugins(self):
        node = self.node.children['plugins']
        for script_id, script_node in node.script_nodes.iteritems():
            meta_node = node.meta_nodes[script_id]
            category = self.category_nodes.get(meta_node.category)
            if not category:
                category = CategoryNodeLink(category=meta_node.category)
                self.category_nodes[meta_node.category] = category
            nodelink = self.build_nodelink(dir_node=node, 
                                           script_id=script_id, 
                                           script_node=script_node, 
                                           meta_node=meta_node)
            category.plugins[script_id] = nodelink
    def build_nodelink(self, **kwargs):
        node = kwargs.get('dir_node', self.node)
        script_id = kwargs.get('script_id')
        script_node = kwargs.get('script_node')
        if not script_node:
            script_node = node.script_nodes[script_id]
        meta_node = kwargs.get('meta_node')
        if not meta_node:
            meta_node = node.meta_nodes[script_id]
        if meta_node.id == 'ingress-intel-total-conversion@jonatkins':
            cls = MainScriptNodeLink
        else:
            cls = PluginNodeLink
        return cls(script_node=script_node, meta_node=meta_node)
    def get_content(self, indent):
        lines = []
        if self.title.lower() == 'mobile':
            lines.extend([
                HtmlLine('<h3 class="ui-bar ui-bar-a ui-corner-all">%s</h3>' % ('Mobile Zip File'), indent),
                HtmlLine('<div class="ui-body">', indent),
                HtmlLine('<a href="%s" data-ajax="false">%s</a>' % ('/'.join([self.node.path, 'mobile.zip']), 'mobile.zip'), indent+1),
                HtmlLine('</div>', indent),
            ])
        lines.extend(self.main_script.get_content(indent=indent))
        for category in self.category_nodes.itervalues():
            lines.extend(category.get_content(indent=indent))
        return lines
    
class NodeLink(object):
    def __init__(self, **kwargs):
        pass
class ScriptNodeLink(NodeLink):
    def __init__(self, **kwargs):
        self.script_node = kwargs.get('script_node')
        self.meta_node = kwargs.get('meta_node')
    @property
    def title(self):
        return self.get_title()
    def get_title(self):
        return self.meta_node.name
    @property
    def url(self):
        return self.get_url()
    def get_url(self):
        node = self.script_node
        path = node.full_path
        if path.startswith('/'):
            path = path[1:]
        return path
    def get_content(self, indent):
        #lines = [
        #    HtmlLine('<li><a href="%s">' % (self.url), indent), 
        #    HtmlLine('<h2>%s</h2>' % (self.title), indent+1),
        #    HtmlLine('</li>', indent),
        #]
        return [HtmlLine('<li><a href="%s" data-ajax="false">%s</a></li>' % (self.url, self.title), indent)]
class CategoryNodeLink(NodeLink):
    def __init__(self, **kwargs):
        self.category = kwargs.get('category')
        self.plugins = {}
    def get_content(self, indent):
        if self.category.lower() == 'deleted':
            return [HtmlLine('')]
        lines = [
            HtmlLine('<h3 class="ui-bar ui-bar-a ui-corner-all">%s</h3>' % (self.category), indent),
            HtmlLine('<div class="ui-body">', indent),
            HtmlLine('<ul>', indent + 1),
        ]
        for script_id, plugin in self.plugins.iteritems():
            lines.extend(plugin.get_content(indent=indent+2))
        lines.extend([HtmlLine('</ul>', indent+1), 
                      HtmlLine('</div>', indent)])
        return lines
class MainScriptNodeLink(ScriptNodeLink):
    def get_title(self):
        return 'IITC Main Script'
    def get_content(self, indent):
        lines = [
            HtmlLine('<h3 class="ui-bar ui-bar-a ui-corner-all">%s</h3>' % (self.title), indent),
            HtmlLine('<div class="ui-body">', indent),
            HtmlLine('<ul>', indent+1),
        ]
        lines.extend(super(MainScriptNodeLink, self).get_content(indent+2))
        lines.extend([
            HtmlLine('</ul>', indent+1),
            HtmlLine('</div>', indent),
        ])
        return lines
class PluginNodeLink(ScriptNodeLink):
    pass

    
def build_nodes(paths=None):
    if paths is None:
        paths = ['local', 'mobile']
    root_node = DirNode()
    for path in paths:
        root_node.add_child(path)
        for root, dirs, files in os.walk(path):
            root_node.add_node_full(root)
            for fn in files:
                full_path = os.path.join(root, fn)
                root_node.add_node_full(full_path)
    return root_node

def build_index_files(root_node):
    index_files = {}
    for cnode in root_node.children.itervalues():
        index_files[cnode.path] = IndexFile(node=cnode)
    main_index = MainIndexFile(index_files.values()[:])
    index_files['index'] = main_index
    return index_files
    
