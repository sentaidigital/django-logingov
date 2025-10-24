import os
import re

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.apps import apps

register = template.Library()

@register.simple_tag
def svg_inject(svg_path, wrapper_class:str="", size:dict=None):
    try:
        # Get the logingov app configuration
        logingov_app = apps.get_app_config('logingov')

        # Construct full path to SVG file using the app's directory
        svg_full_path = os.path.join(logingov_app.path, 'static', 'logingov', 'img', svg_path)

        # Read the SVG file
        with open(svg_full_path, 'r') as file:
            svg_content = file.read()

        # Build the attributes string
        attrs = []
        attrs.append('role="img"')
        if wrapper_class:
            attrs.append(f'class="{wrapper_class}"')

        if size is not None and size["width"] is not None and size["height"] is not None:
            attrs.append(f'width="{size["width"]}"')
            attrs.append(f'height="{size["height"]}"')

        # Create the new attributes string
        all_attrs = " ".join(attrs)

        # Simple approach: replace just the opening svg tag with our new version
        # Use a simpler regex to find and replace the first SVG tag
        def replace_svg_tag(match):
            # Extract existing attributes from the SVG opening tag
            svg_tag_content = match.group(0)  # This will be something like <svg xmlns="..." viewBox="...">

            # Find the end of the opening tag
            close_bracket_pos = svg_tag_content.rfind('>')

            if close_bracket_pos == -1:
                # If we can't find the closing bracket, return original
                return svg_tag_content

            # Extract just the part between <svg and >
            existing_attrs = svg_tag_content[4:close_bracket_pos].strip()

            # If there are existing attributes, we want to preserve them
            if existing_attrs:
                # Merge existing and new attributes (new ones override existing)
                # Simple approach: combine them with proper spacing
                combined_attrs = existing_attrs + " " + all_attrs
            else:
                # No existing attributes, just use new ones
                combined_attrs = all_attrs

            # Return the modified SVG tag
            return f'<svg {combined_attrs}>'

        # Replace only the first <svg> tag in the content
        modified_svg = re.sub(r'<svg[^>]*>', replace_svg_tag, svg_content, count=1)

        return mark_safe(modified_svg)

    except FileNotFoundError:
        return mark_safe(f"<!-- SVG file '{svg_full_path}' not found -->")
