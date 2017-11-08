from __future__ import unicode_literals

import posixpath
from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
try:
    from django.urls import NoReverseMatch, reverse
except:
    # Fallback for Django <= 1.9
    from django.core.urlresolvers import NoReverseMatch, reverse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from markitup import settings
from markitup.util import absolute_url

import inspect

"""Compatibility mixin by @spookeylukey
https://github.com/mlavin/django-selectable/commit/9426afeb16b07c2aa222f664a3e3177d6640f372
"""

new_style_build_attrs = (
    'base_attrs' in
    inspect.getargs(forms.widgets.Widget.build_attrs.__code__).args)

class BuildAttrsCompat(object):
    """
    Mixin to provide compatibility between old and new function
    signatures for Widget.build_attrs, and a hook for adding our
    own attributes.
    """
    # These are build_attrs definitions that make it easier for
    # us to override, without having to worry about the signature,
    # by adding a standard hook, `build_attrs_extra`.
    # It has a different signature when we are running different Django
    # versions.
    if new_style_build_attrs:
        def build_attrs(self, base_attrs, extra_attrs=None):
            attrs = super(BuildAttrsCompat, self).build_attrs(
                base_attrs, extra_attrs=extra_attrs)
            return self.build_attrs_extra(attrs)
    else:
        def build_attrs(self, extra_attrs=None, **kwargs):
            attrs = super(BuildAttrsCompat, self).build_attrs(
                extra_attrs=extra_attrs, **kwargs)
            return self.build_attrs_extra(attrs)

    def build_attrs_extra(self, attrs):
        # Default implementation, does nothing
        return attrs

    # These provide a standard interface for when we want to call build_attrs
    # in our own `render` methods. In both cases it is the same as the Django
    # 1.11 signature, but has a different implementation for different Django
    # versions.
    if new_style_build_attrs:
        def build_attrs_compat(self, base_attrs, extra_attrs=None):
            return self.build_attrs(base_attrs, extra_attrs=extra_attrs)

    else:
        def build_attrs_compat(self, base_attrs, extra_attrs=None):
            # Implementation copied from Django 1.11, plus include our
            # hook `build_attrs_extra`
            attrs = base_attrs.copy()
            if extra_attrs is not None:
                attrs.update(extra_attrs)
            return self.build_attrs_extra(attrs)


CompatMixin = BuildAttrsCompat

class MarkupInput(forms.Widget):
    def render(self, name, value, attrs=None):
        if value is not None:
            # Special handling for MarkupField value.
            # This won't touch simple TextFields because they don't have
            # 'raw' attribute.
            try:
                value = value.raw
            except AttributeError:
                pass
        return super(MarkupInput, self).render(name, value, attrs)


class MarkupTextarea(MarkupInput, forms.Textarea):
    pass


class MarkupHiddenWidget(MarkupInput, forms.HiddenInput):
    pass


class MarkItUpWidget(CompatMixin, MarkupTextarea):
    """
    Widget for a MarkItUp editor textarea.

    Takes two additional optional keyword arguments:

    ``markitup_set``
        URL path (absolute or relative to STATIC_URL) to MarkItUp
        button set directory.  Default: value of MARKITUP_SET setting.

    ``markitup_skin``
        URL path (absolute or relative to STATIC_URL) to MarkItUp skin
        directory.  Default: value of MARKITUP_SKIN setting.

    """
    def __init__(self, attrs=None,
                 markitup_set=None,
                 markitup_skin=None,
                 auto_preview=None):
        self.miu_set = absolute_url(markitup_set or settings.MARKITUP_SET)
        self.miu_skin = absolute_url(markitup_skin or settings.MARKITUP_SKIN)
        if auto_preview is None:
            auto_preview = settings.MARKITUP_AUTO_PREVIEW
        self.auto_preview = auto_preview
        super(MarkItUpWidget, self).__init__(attrs)

    def _media(self):
        js_media = [absolute_url(settings.JQUERY_URL)] if settings.JQUERY_URL is not None else []
        js_media = js_media + [absolute_url('markitup/ajax_csrf.js'),
                               absolute_url('markitup/jquery.markitup.js'),
                               posixpath.join(self.miu_set, 'set.js')]
        return forms.Media(
            css={'screen': (posixpath.join(self.miu_skin, 'style.css'),
                            posixpath.join(self.miu_set, 'style.css'))},
            js=js_media)
    media = property(_media)

    def render(self, name, value, attrs=None):
        html = super(MarkItUpWidget, self).render(name, value, attrs)

        base_attrs = self.build_attrs(attrs, name=name)
        final_attrs = self.build_attrs_compat(base_attrs, attrs)

        try:
            preview_url = reverse('markitup_preview')
        except NoReverseMatch:
            preview_url = ""

        html += render_to_string('markitup/editor.html',
                                 {'textarea_id': final_attrs['id'],
                                 'AUTO_PREVIEW': self.auto_preview,
                                 'preview_url': preview_url})

        return mark_safe(html)


class AdminMarkItUpWidget(MarkItUpWidget, AdminTextareaWidget):
    """
    Add vLargeTextarea class to MarkItUpWidget so it looks more
    similar to other admin textareas.

    """
    pass
