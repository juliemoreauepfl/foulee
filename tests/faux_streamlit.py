"""Un faux Streamlit minimal pour exécuter les écrans sans navigateur.

Il ne vérifie pas le rendu visuel : il attrape les erreurs Python
(variables manquantes, mauvais types, mauvaise navigation)."""
from __future__ import annotations

import contextlib
import types
from datetime import date


class Rerun(Exception):
    pass


class EtatSession(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v


class _Bloc:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, nom):
        return getattr(module, nom)

    def progress(self, *a, **k):
        return self


def creer():
    st = types.ModuleType("streamlit")
    st.session_state = EtatSession()
    st.clics = set()          # clés de boutons « cliqués » au prochain passage
    st.journal = []           # tout ce qui est affiché
    st.secrets = {}

    class Params(dict):
        def clear(self):
            super().clear()
    st.query_params = Params()
    st.link_button = lambda label, url, **k: _note("button", label, None)
    st.toggle = lambda label, value=False, key=None, **k: _widget(key, value)

    def _note(kind, *a):
        st.journal.append((kind, a))

    def set_page_config(**k):
        pass

    def markdown(body, unsafe_allow_html=False, **k):
        _note("markdown", body)

    def button(label, key=None, type="secondary", icon=None, disabled=False, help=None, on_click=None, **k):
        _note("button", label, key)
        if key in st.clics and not disabled:
            st.clics.discard(key)
            return True
        return False

    def download_button(label, data=None, file_name=None, mime=None, key=None, **k):
        assert data is not None and len(data) > 0
        _note("download", label, file_name, len(data))
        return False

    def _widget(key, defaut):
        if key is not None:
            if key not in st.session_state:
                st.session_state[key] = defaut
            return st.session_state[key]
        return defaut

    def segmented_control(label, options, default=None, key=None, on_change=None, format_func=None, **k):
        options = list(options)
        if format_func:
            [format_func(o) for o in options]
        v = _widget(key, default)
        assert v is None or v in options, f"{key}: {v} pas dans {options}"
        _note("segmented", label, v)
        return v

    def pills(label, options, selection_mode="single", default=None, key=None, **k):
        return _widget(key, default if default is not None else ([] if selection_mode == "multi" else None))

    def selectbox(label, options, index=0, key=None, **k):
        options = list(options)
        return _widget(key, options[index] if index is not None and options else None)

    def text_input(label, value="", key=None, **k):
        return _widget(key, value)

    def text_area(label, value="", key=None, **k):
        return _widget(key, value)

    def date_input(label, value=None, key=None, min_value=None, max_value=None, **k):
        v = _widget(key, value)
        if min_value and v < min_value:
            raise AssertionError("date sous le minimum")
        return v

    def number_input(label, min_value=None, max_value=None, value=None, key=None, **k):
        return _widget(key, value)

    def file_uploader(*a, **k):
        return None

    def columns(spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Bloc() for _ in range(n)]

    def rerun():
        raise Rerun()

    def cache_data(fn=None, **k):
        if fn is None:
            return lambda f: f
        return fn

    for nom in ("success", "error", "warning", "info", "caption", "toast", "subheader", "write"):
        setattr(st, nom, (lambda n: lambda *a, **k: _note(n, *a))(nom))
    st.set_page_config, st.markdown, st.button = set_page_config, markdown, button
    st.download_button, st.segmented_control, st.pills = download_button, segmented_control, pills
    st.text_input, st.text_area, st.date_input, st.number_input = text_input, text_area, date_input, number_input
    st.file_uploader, st.columns, st.rerun, st.cache_data = file_uploader, columns, rerun, cache_data
    st.selectbox = selectbox
    st.expander = st.form = st.spinner = st.status = st.popover = lambda *a, **k: _Bloc()
    st.form_submit_button = lambda *a, **k: False
    st.progress = lambda *a, **k: _Bloc()
    return st


module = None


def installer():
    global module
    import sys
    module = creer()
    sys.modules["streamlit"] = module
    return module
