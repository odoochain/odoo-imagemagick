# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2022- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Image: Imagemagick: Website',
    'version': '1.0',
    'summary': 'Advanced Image handling',
    'category': 'Technical',
    'description': 
    """
        Advanced Image handling
        =======================

        * Use responsive avare recipies for image handling
        * Web Editor Tools for end user, choose recipe for your images as you are creating pages
        * Tools for qweb use

        https://graphicdesign.stackexchange.com/questions/39430/using-imagemagick-to-create-vibrant-images
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-imagemagick/website_imagemagick',
    'images': ['static/description/banner.png'], # 560x280 px.
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-imagemagick',
    'depends': ['base', 'website'],
    'external_dependencies': {
        'python': ['wand', ],

        #'bin': ['imagemagick'], this is a quick fix, somebody who how this module should have at it.
        # sudo apt install python3-wand
    },
    'data': [
        'website_imagemagick_data.xml',
        'security/ir.model.access.csv',
        #'views/snippet.xml',
        #'views/image_recipe.xml',
    ],
    'application': True,
    # 'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
