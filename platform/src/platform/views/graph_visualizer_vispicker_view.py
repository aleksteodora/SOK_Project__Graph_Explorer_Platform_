import os
import sys


class VisualizerPickerView(object):
    def __init__(self):
        pass

    def render(self) -> (str, str, str):
        """
        Return the html content required for visualizer plugin selection.
        :return: (style, body, script) html strings that should be included in page
        """
        templates_dir = os.path.join(sys.prefix, 'templates')

        with open(os.path.join(templates_dir, 'graph-visualizer-vispicker-style.html'), 'r', encoding='utf-8') as f:
            style_html = f.read()

        with open(os.path.join(templates_dir, 'graph-visualizer-vispicker-body.html'), 'r', encoding='utf-8') as f:
            body_html = f.read()

        with open(os.path.join(templates_dir, 'graph-visualizer-vispicker-script.html'), 'r', encoding='utf-8') as f:
            script_html = f.read()

        return style_html, body_html, script_html


if __name__ == "__main__":
    style, body, script = VisualizerPickerView().render()
    print(style)
    print(body)
    print(script)

