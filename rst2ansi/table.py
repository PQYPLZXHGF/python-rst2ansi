"""
The MIT License (MIT)

Copyright © 2015-2016 Franklin "Snaipe" Mathieu <http://snai.pe/>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from docutils import nodes

class TableSizeCalculator(nodes.NodeVisitor):

  def __init__(self, document):
    nodes.NodeVisitor.__init__(self, document)
    self.level = 0
    self.widths = []
    self.heights = []
    self.rows = 0

  def __getattr__(self, name):
    if name.startswith('visit_') or name.startswith('depart_'):
      def noop(*args, **kwargs):
        pass
      return noop
    raise AttributeError(name)

  def visit_table(self, node):
    if self.level > 0:
      raise SkipChildren
    self.level += 1

  def depart_table(self, node):
    self.width = sum(self.widths) + (len(self.widths) + 1)
    self.height = sum(self.heights) + (len(self.heights) + 1)
    self.level -= 1

  def visit_tgroup(self, node):
    self.cols = node.attributes['cols']

  def visit_colspec(self, node):
    self.widths.append(node.attributes['colwidth'] + 2)

  def visit_row(self, node):
    self.rows += 1
    self.heights.append(1)

  def visit_entry(self, node):
    self.heights[-1] = max(self.heights[-1], len(node.astext().split('\n')))
    raise nodes.SkipChildren

class TableDrawer(nodes.NodeVisitor):

  def __init__(self, props, document):
    nodes.NodeVisitor.__init__(self, document)
    self.props = props
    self.level = 0
    self.lines = ['']
    self.line = 0
    self.cursor = 0
    self.col = 0
    self.row = 0
    self.nb_rows = 0

  def __getattr__(self, name):
    if name.startswith('visit_') or name.startswith('depart_'):
      def noop(*args, **kwargs):
        pass
      return noop
    if name == 'curline':
      return self.lines[self.line]
    raise AttributeError(name)

  def _draw_rule(self):
    self.lines[self.line] += '+' + '-' * (self.props.width - 1)
    self.lines.extend(['|' + ' ' * (self.props.width - 1)] * (self.props.height - 1))
    self.line += 1
    self.cursor = 0

  def visit_table(self, node):
    if self.level > 0:
      raise SkipChildren
    self.level += 1
    self._draw_rule()

  def depart_table(self, node):
    self.level -= 1

  def visit_row(self, node):
    self.col = 0
    self.cursor = 0

  def depart_row(self, node):
    self.line += self.props.heights[self.row] + 1
    self.row += 1
    self.local_row += 1

  def visit_thead(self, node):
    self.nb_rows = len(node.children)
    self.local_row = 0

  visit_tbody = visit_thead

  def visit_entry(self, node):
    cols = node.attributes.get('morecols', 0) + 1
    rows = node.attributes.get('morerows', 0) + 1

    width = sum(self.props.widths[self.col:self.col + cols]) + (cols - 1)
    height = sum(self.props.heights[self.row:self.row + rows]) + (rows - 1)

    rule = '=' if self.local_row + rows - 1 == self.nb_rows - 1 else '-'
    sep = '|'

    # Draw the horizontal rule

    line = self.lines[self.line + height]
    line = line[:self.cursor] + '+' + (width * rule) + '+' + line[self.cursor + width + 2:]
    self.lines[self.line + height] = line

    # Draw the vertical rule

    for i in range(height):
      line = self.lines[self.line + i]
      line = line[:self.cursor + width + 1] + sep + line[self.cursor + width + 2:]
      self.lines[self.line + i] = line

    line = self.lines[self.line - 1]
    line = line[:self.cursor + width + 1] + '+' + line[self.cursor + width + 2:]
    self.lines[self.line - 1] = line

    self.col += cols
    self.cursor += width + 1

    # Do not recurse
    raise nodes.SkipChildren

class TableWriter(nodes.NodeVisitor):

  def __init__(self, props, document):
    nodes.NodeVisitor.__init__(self, document)
    self.props = props
    self.level = 0
    self.line = 0
    self.cursor = 0
    self.col = 0
    self.row = 0
    self.nb_rows = 0

  def __getattr__(self, name):
    if name.startswith('visit_') or name.startswith('depart_'):
      def noop(*args, **kwargs):
        pass
      return noop
    raise AttributeError(name)

  def visit_table(self, node):
    drawer = TableDrawer(self.props, self.document)
    node.walkabout(drawer)
    self.lines = drawer.lines

  def visit_row(self, node):
    self.col = 0
    self.cursor = 0

  def depart_row(self, node):
    self.line += self.props.heights[self.row] + 1
    self.row += 1
    self.local_row += 1

  def visit_thead(self, node):
    self.nb_rows = len(node.children)
    self.local_row = 0

  visit_tbody = visit_thead

  def visit_entry(self, node):
    cols = node.attributes.get('morecols', 0) + 1
    rows = node.attributes.get('morerows', 0) + 1

    width = sum(self.props.widths[self.col:self.col + cols]) + (cols - 1)
    height = sum(self.props.heights[self.row:self.row + rows]) + (rows - 1)

    from rst2ansi import ANSITranslator

    v = ANSITranslator(self.document, termsize=(width - 2, height))
    node.children[0].walkabout(v)
    v.strip_empty_lines()
    i = 1
    for l in v.lines:
      for sl in l.split('\n'):
        line = self.lines[self.line + i]
        line = line[:self.cursor + 2] + sl + line[self.cursor + 2 + len(sl):]
        self.lines[self.line + i] = line
        i += 1

    self.col += cols
    self.cursor += width + 1

    # Do not recurse
    raise nodes.SkipChildren