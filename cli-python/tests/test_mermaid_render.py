# Unit tests for mermaid_render.py -- the optional local-svg renderer
# wrapper. Run from repo root: pytest cli-python/tests -q
from __future__ import annotations

import builtins
import sys
from unittest.mock import MagicMock, patch

import pytest

from sdd.utils.mermaid_render import MermaidRendererNotInstalled, render_mermaid_svg


class TestRenderMermaidSvg:
    def test_raises_clear_error_when_mmdr_not_installed(self):
        """Simulates the common case: the optional [diagrams] extra was
        never installed. Must name the exact install command, never a
        bare ImportError traceback."""
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "mmdr":
                raise ImportError("No module named 'mmdr'")
            return real_import(name, *args, **kwargs)

        with (
            patch.object(builtins, "__import__", side_effect=fake_import),
            pytest.raises(MermaidRendererNotInstalled) as exc_info,
        ):
            render_mermaid_svg("flowchart LR; A-->B")
        assert 'pip install "sddflow[diagrams]"' in str(exc_info.value)

    def test_returns_svg_string_on_success(self):
        fake_mmdr = MagicMock()
        fake_mmdr.render.return_value.svg.return_value = "<svg>ok</svg>"
        with patch.dict(sys.modules, {"mmdr": fake_mmdr}):
            result = render_mermaid_svg("flowchart LR; A-->B")
        assert result == "<svg>ok</svg>"
        fake_mmdr.render.assert_called_once_with("flowchart LR; A-->B")

    def test_invalid_diagram_source_propagates_the_renderer_error(self):
        """A bad diagram (renderer's own validation failure) must
        propagate as-is -- callers (md_to_cf.py) decide how to handle
        it (fall back to a code block), this wrapper doesn't swallow it."""
        fake_mmdr = MagicMock()
        fake_mmdr.render.side_effect = ValueError("no diagram type detected")
        with (
            patch.dict(sys.modules, {"mmdr": fake_mmdr}),
            pytest.raises(ValueError, match="no diagram type detected"),
        ):
            render_mermaid_svg("not a diagram")
