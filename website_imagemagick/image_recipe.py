# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2014-2017 Vertel AB (<http://vertel.se>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from io import StringIO, BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning
from odoo import http
from odoo.http import request, STATIC_CACHE
from datetime import datetime
from odoo.modules import get_module_resource, get_module_path
import werkzeug
import pytz
import re
import hashlib
import sys
import traceback
import codecs

from .safeish_eval import safe_eval as eval
import os
from wand.image import Image
from wand.display import display
from wand.drawing import Drawing
from wand.color import Color
import subprocess
import wand.api
import ctypes
import time
import uuid
import base64
import logging
_logger = logging.getLogger(__name__)

# https://developers.google.com/web/fundamentals/performance/optimizing-content-efficiency/image-optimization#selecting-the-right-image-format

class Image(Image):
    def is_landscape(self):
        return self.width >= self.height

    def shrink_width(self, width):
        return self.width >= int(width)

    def shrink_height(self, height):
        return self.height >= int(height)


class website_imagemagic(http.Controller):

    # this controller will control url: /imagemagick/attachment_id/id/recipe_id or /imagemagick/attachment_id/ref/recipe_ref
    @http.route(['/imagemagick/<model("ir.attachment"):image>/id/<model("image.recipe"):recipe>',
                 '/imagemagick/<model("ir.attachment"):image>/ref/<string:recipe_id>'], type='http', auth="public", website=True)
    def view_attachment(self, image=None, recipe=None, recipe_ref=None, **post):
        if recipe_ref:
            recipe = request.env.ref(recipe_ref)
        if recipe:
            return recipe.send_file(attachment=image)
        return request.registry['website']._image(
                request.cr, request.uid, 'ir.attachment','%s_%s' % (image.id, hashlib.sha1(image.sudo().write_date or image.sudo().create_date or '').hexdigest()[0:7]),
                'datas', werkzeug.wrappers.Response(),250,250,cache=STATIC_CACHE)

    # this controller will control url: /imageurl/id/<recipe_id>?url=<your url> or /imageurl/ref/<recipe_ref>?url=<your url>
    @http.route(['/imageurl/id/<model("image.recipe"):recipe>', '/imageurl/ref/<string:recipe_ref>'], type='http', auth="public", website=True)
    def view_url(self, recipe=None, recipe_ref=None, **post):
        url = post.get('url','')
        if len(url)>0 and url[0] == '/':
            url=url[1:]
        if recipe_ref:
            recipe = request.env.ref(recipe_ref) # 'imagemagick.my_recipe'
        if url:
            return recipe.send_file(url='/'.join(get_module_path(url.split('/')[0]).split('/')[0:-1]) + '/' + url)
        return http.send_file(StringIO(recipe.run(Image(filename=get_module_path('web') + '/static/src/img/placeholder.png')).make_blob(format=recipe.image_format if recipe.image_format else 'png')))

    # this controller will control url: /imagefield/model_id/field_id/obj_id/ref/recipe_ref or /imagefield/model_id/field_id/obj_id/id/recipe_id
    @http.route([
        '/imagefield/<model>/<field>/<id>/ref/<recipe_ref>',
        '/imagefield/<model>/<field>/<id>/id/<model("image.recipe"):recipe>',
        ], type='http', auth="public", website=True, multilang=False)
    def website_image(self, model, id, field, recipe=None, recipe_ref=None, **post):
        if recipe_ref:
            recipe = request.env.ref(recipe_ref) # 'imagemagick.my_recipe'
        return recipe.send_file(field=field, model=model, id=int(id))

    # this controller will control url: /imagefield/model_id/field_id/ref/recipe_ref/image/file_name
    @http.route([
        '/imagefield/<model>/<field>/<id>/ref/<recipe_ref>/image/<file_name>'
        ], type='http', auth="public", website=True, multilang=False)
    def website_image_hash(self, model, id, field, recipe_ref, file_name=None, **post):
        if recipe_ref:
            recipe = request.env.ref(recipe_ref) # 'imagemagick.my_recipe'
        return recipe.send_file(field=field, model=model, id=int(id))

    # this controller will control url: /website/imagemagick/model_id/field_id/obj_id/recipe_id
    @http.route([
        '/website/imagemagick/<model>/<field>/<id>/<model("image.recipe"):recipe>',
        ], type='http', auth="public", website=True, multilang=False)
    def website_imagemagick(self, model, field, id, recipe=None, **post):
        try:
            idsha = id.split('_')
            id = int(idsha[0])
            response = werkzeug.wrappers.Response()
            return request.env['website']._imagemagick(
                model, id, field, recipe, response,
                cache=STATIC_CACHE if len(idsha) > 1 else None)
        except Exception:
            _logger.exception("Cannot render image field %r of record %s[%s] with recipe[%s]",
                             field, model, id, recipe.id)
            response = werkzeug.wrappers.Response()
            return self.placeholder(response)
    """
     class werkzeug.contrib.cache.FileSystemCache(cache_dir, threshold=500, default_timeout=300, mode=384)

    A cache that stores the items on the file system. This cache depends on being the only user of the cache_dir. Make absolutely sure that nobody but this cache stores files there or otherwise the cache will randomly delete files therein.
    Parameters:

        cache_dir – the directory where cache files are stored.
        threshold – the maximum number of items the cache stores before it starts deleting some.
        default_timeout – the default timeout that is used if no timeout is specified on set().
        mode – the file mode wanted for the cache files, default 0600

    """

    def placeholder(self, response):
        # ~ return request.env['website']._image_placeholder(response)
        f = open(get_module_path('web') + '/static/img/placeholder.png', 'rb')
        # ~ asd = Image(file=f, format='PNG')
        response.mimetype = 'image/png'
        filename = 'placeholder.png'
        response.headers['Content-Disposition'] = 'inline; filename="%s"' % filename
        response.data = f.read()
        return response.make_conditional(request.httprequest)

#
# Web Editor tools
#

    """
    Parameters:
    * img_src: image src for target image
    * recipe_id: recipe id of selected recipe
    """
    @http.route(['/website_imagemagick_recipe_change'], type='json', auth="public", website=True)
    def website_imagemagick_recipe_change(self, img_src, recipe_id, **kw):
        _logger.error('url %s' % img_src)
        attachment_id = 0
        url = None
        if '/website/static/src/img/' in img_src and not '/imageurl' in img_src:
            url = img_src[img_src.find('/website'):]
            return '/imageurl/id/%s?url=%s' %(recipe_id, url)
        if '/website/image/ir.attachment/' in img_src:
            attachment_id = re.search('/website/image/ir.attachment/(.*)/datas', img_src).group(1).split('_')[0]
        elif '/imagefield/ir.attachment/datas/' in img_src:
            attachment_id = re.search('/imagefield/ir.attachment/datas/(.*)/id', img_src).group(1)
        elif '/web/image/' in img_src:
            attachment_id = re.search('/web/image/(.*)', img_src).group(1)
        elif '/imagemagick/' in img_src:
            attachment_id = re.search('/imagemagick/(.*)/id', img_src).group(1)
            attachment = request.env['ir.attachment'].browse(int(attachment_id if attachment_id.isdigit() else 0))
            return '/imagemagick/%s/id/%s' %(attachment.id, recipe_id)
        else:
            attachment_id = 0
        attachment = request.env['ir.attachment'].browse(int(attachment_id  if attachment_id.isdigit() else 0))
        return '/imagefield/ir.attachment/datas/%s/id/%s' %(attachment.id, recipe_id)

    #TODO: reset recipe to normal attachment

class website(models.Model):
    _inherit = 'website'

    #~ def _image_placeholder(self, response):
        #~ """
        #~ Choose placeholder.
        #~ """
        #~ # file_open may return a StringIO. StringIO can be closed but are
        #~ # not context managers in Python 2 though that is fixed in 3
        #~ with contextlib.closing(openerp.tools.misc.file_open(
                #~ os.path.join('web', 'static', 'src', 'img', 'placeholder.png'),
                #~ mode='rb')) as f:
            #~ response.data = f.read()
            #~ return response.make_conditional(request.httprequest)

    @api.model
    def imagemagick_url(self, record, field, recipe, id=None):
        """Returns a local url that points to the image field of a given browse record, run through an imagemagick recipe.
           Record can be a record object, external id or model name (requires id to be given as well).
           Recipe can be a record object, external id, or an id.
        """
        if type(record) is str:
            if id:
                record = self.env[record].browse(id)
            else:
                record = self.env.ref(record)
        model = record._name
        sudo_record = record.sudo()
        if type(recipe) is str:
            sudo_recipe = self.env.ref(recipe)
        elif type(recipe) is int:
            sudo_recipe = self.env['image.recipe'].browse(recipe).sudo()
        else:
            sudo_recipe = recipe.sudo()
        id = '%s_%s' % (record.id, hashlib.sha1(('%s%s' % (sudo_record.write_date or sudo_record.create_date or '',
            sudo_recipe.write_date or sudo_recipe.create_date or '')).encode('utf-8')).hexdigest())
        return '/website/imagemagick/%s/%s/%s/%s' % (model, field, id, sudo_recipe.id)

    # WIP. Very temporary solution.
    @api.model
    def _imagemagick(self, model, id, field, recipe, response, cache=None):
        """ Fetches the requested field and applies the given imagemagick recipe on it.

        If the record is not found or does not have the requested field,
        returns a placeholder image via :meth:`~._image_placeholder`.

        Sets and checks conditional response parameters:
        * :mailheader:`ETag` is always set (and checked)
        * :mailheader:`Last-Modified is set iif the record has a concurrency
          field (``__last_update``)

        The requested field is assumed to be base64-encoded image data in
        all cases.
        """
        user = self.env['res.users'].browse(self._uid)
        o = self.env[model].sudo().browse(int(id))
        if o.check_access_rights('read', raise_exception=False):
            return recipe.sudo().send_file(field=field,model=model,id=id)
        if 'website_published' in o.fields_get().keys() and o.website_published == True:
            if user.has_group('base.group_website_publisher') or recipe.website_published == True:
                return recipe.sudo().send_file(field=field, model=model, id=id)
        return recipe.send_file(field=field,model=model,id=id)

        record = self.env[model].browse(id)
        if not len(record) > 0 and 'website_published' in record._fields:
            record = self.env[model].sudo().search(
                                [('id', '=', id),
                                ('website_published', '=', True)])
        if not len(record) > 0:
            return self.env['website_imagemagick'].placeholder(response)

        concurrency = '__last_update'
        record = record.sudo()
        if hasattr(record, concurrency):
            server_format = odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            try:
                response.last_modified = datetime.datetime.strptime(
                    getattr(record, concurrency), server_format + '.%f')
            except ValueError:
                # just in case we have a timestamp without microseconds
                response.last_modified = datetime.datetime.strptime(
                    getattr(record, concurrency), server_format)

        # Field does not exist on model or field set to False
        if not hasattr(record, field) and getattr(record, field) and recipe:
            # FIXME: maybe a field which does not exist should be a 404?
            return self.env['website_imagemagick'].placeholder(response)

        #TODO: Keep format of original image.
        img = recipe.run(Image(blob=getattr(record, field).decode('base64'))).make_blob() #format='jpg')
        response.set_etag(hashlib.sha1(img).hexdigest())
        response.make_conditional(request.httprequest)

        if cache:
            response.cache_control.max_age = cache
            response.expires = int(time.time() + cache)

        # conditional request match
        if response.status_code == 304:
            return response

        data = img.decode('base64')
        image = Image.open(cStringIO.StringIO(data))
        response.mimetype = Image.MIME[image.format]

        filename = '%s_%s.%s' % (model.replace('.', '_'), id, str(image.format).lower())
        response.headers['Content-Disposition'] = 'inline; filename="%s"' % filename

        response.data = data

        return response

    @api.model
    def imagefield_hash(self, model, field, id, recipe):
        """Returns a local url that points to the image field of a given browse record, run through an imagemagick recipe.
        """
        record = self.env[model].sudo().browse(id)
        sudo_recipe = self.env.ref(recipe).sudo()
        txt = f"""{
            record.write_date or record.create_date or '' }{
            sudo_recipe.write_date or sudo_recipe.create_date or '' }{
            model }{
            id }{
            sudo_recipe.id }"""
        hashtxt = hashlib.sha1(txt.encode('utf-8')).hexdigest()[0:7]

        try:
            device_type = request.session.get('device_type','md')
        except:
            device_type = 'md'

        return '/imagefield/{model}/{field}/{id}/ref/{recipe}/image/{file_name}'.format(
            model=model, field=field, id=id, recipe=recipe,
            file_name='%s-%s.%s' % (
                device_type,
                hashtxt, sudo_recipe.image_format or 'jpeg')) if record[field] else ''

class image_recipe_state(models.Model):
    _name = 'image.recipe.state'
    _description = 'TODO'

    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence')
    fold = fields.Boolean(string='Folded in Kanban View', help='This stage is folded in the kanban view when there are no records in that state to display.')


class image_recipe(models.Model):
    _name = "image.recipe"
    _description = 'TODO'

    test = fields.Binary(compute='compute_test')

    param_list = fields.Char(compute='_params')
    website_published =fields.Boolean(string="Published", default = True)
    description = fields.Text(string="Description")
    image_format = fields.Selection([('progressive_jpeg', 'Progressive JPEG'),('jpeg','Jpeg'),('jp2','JPEG 2000'),('png','PNG'),('GIF','gif'),('webp','WebP')],string='Image Format')
    color = fields.Integer(string='Color Index')
    name = fields.Char(string='Name')
    recipe = fields.Text(string='Recipe')
    param_ids = fields.One2many(comodel_name='image.recipe.param', inverse_name='recipe_id', string='Recipes')
    state_id = fields.Many2one(comodel_name='image.recipe.state', string='State' ) # , default=_default_state_id)
    image = fields.Binary(compute='_image')
    external_id = fields.Char(string='External ID')

    def compute_test(self):
        time.sleep(5)

    def _default_state_id(self):
        for state in self:
            return state.env.ref('website_imagemagick.image_recipe_state_draft').id if state.env.ref('website_imagemagick.image_recipe_state_draft') else None

    def _params(self):
        for params in self:
            params.param_list = ','.join(params.param_ids.mapped(lambda p: '%s: %s' % (p.name,p.value)))

    def _image(self):
        for image_ in self:
            try:
                url = image_.env['ir.config_parameter'].get_param('imagemagick.test_image')
                if not url:
                    image_.env['ir.config_parameter'].set_param('imagemagick.test_image','website/static/src/img/snippets_demo/s_banner.jpg')
                    url = self.env['ir.config_parameter'].get_param('imagemagick.test_image')
                image_.image = codecs.encode(self.run(image_.url_to_img('/'.join(get_module_path(url.split('/')[0]).split('/')[0:-1]) + '/' + url)).make_blob(format='png'),'base64')
            except:
                e = sys.exc_info()
                message = '\n%s' % ''.join(traceback.format_exception(e[0], e[1], e[2]))
                _logger.error(message)

    def get_external_id(self):
        for ext_id in self:
            external_id = ext_id.env['ir.model.data'].search([('model', '=', 'image.recipe'), ('res_id', '=', ext_id.id)])
            if not external_id:
                try:
                    external_id = ext_id.env['ir.model.data'].create({
                        'name': '_'.join((ext_id.name.lower()).split(' ')),
                        'module': 'website_imagemagick',
                        'model': 'image.recipe',
                        'res_id': ext_id.id,
                    })
                    ext_id.external_id = external_id.complete_name
                except:
                    e = sys.exc_info()
                    raise Warning('\n%s' % ''.join(traceback.format_exception(e[0], e[1], e[2])))
            else:
                ext_id.external_id = external_id.complete_name

    @api.model
    def _read_state_id(self, present_ids, domain, **kwargs):
        states = self.env['image.recipe.state'].search([], order='sequence').name_get()
        return states, None

    _group_by_full = {
        'state_id': _read_state_id,
    }

  # http://docs.wand-py.org/en/0.4.1/index.html

    def attachment_to_img(self, attachment):  # return an image object while filename is an attachment
        if attachment.url:  # make image url as /module_path/attachment_url and use it as filename
            path = '/'.join(get_module_path(attachment.url.split('/')[1]).split('/')[0:-1])
            return Image(filename=path + attachment.url)
        #_logger.warning('<<<<<<<<<<<<<< attachment_to_img >>>>>>>>>>>>>>>>: %s' % attachment.datas)
        return Image(blob=codecs.decode(attachment.datas, 'base64'))

    def data_to_img(self, data):  # return an image object while filename is data
        #_logger.warning('<<<<<<<<<<<<<< data_to_img >>>>>>>>>>>>>>>>: %s' % data)
        if data:
            return Image(blob=data.decode('base64'))
        return Image(filename='/'.join(get_module_path('/web/static/src/img/foo.png'.split('/')[1]).split('/')[0:-1]) + '/web/static/src/img/placeholder.png')


    def url_to_img(self, url):  # return an image object while filename is an url
        return Image(filename=url)


    def get_mtime(self, attachment):    # return a last modified time of an image
        if attachment.write_date > self.write_date:
            return attachment.write_date
        return self.write_date

    def send_file(self,attachment=None, url=None,field=None,model=None,id=None):   # return a image while given an attachment or an url
        # ~ mimetype = 'image/%s' % self.image_format if self.image_format else 'png'
        mimetype = self.get_mimetype(attachment, model, field, id)
        if field:
            #o = self.env[model].sudo().browse(int(id if id.isdigit() else 0))
            o = self.env[model].sudo().search_read([('id','=',id)],[field])
            if not o:
                return http.send_file(BytesIO(self.run(Image(filename=get_module_path('web') + '/static/src/img/placeholder.png')).make_blob(format=self.image_format if self.image_format else 'png')), mimetype=mimetype)
            o = o[0]

            if self.image_format == 'progressive_jpeg':
                unique_filename = str(uuid.uuid4())
                image = self.run(Image(blob=codecs.decode(o[field], 'base64')))
                image.format = "jpg"
                image.save(filename=f"/tmp/{unique_filename}")
                cmd = "convert /tmp/%s -interlace line /tmp/%s"% (unique_filename, unique_filename)
                _logger.warning(cmd)
                os.system(cmd)
                img = open(f"/tmp/{unique_filename}", "r+b")
                os.remove(f"/tmp/{unique_filename}")
                mimetype = "image/jpg"
                return http.send_file(img, mimetype=mimetype, filename=field)
            else:
                return http.send_file(BytesIO(self.run(Image(blob=codecs.decode(o[field], 'base64'))).make_blob(format=self.image_format or 'jpg')), mimetype=mimetype, filename=field)

        if attachment:
            #_logger.warning('<<<<<<<<<<<<<< attachment >>>>>>>>>>>>>>>>: %s' % attachment)
            # ~ return http.send_file(BytesIO(self.run(Image(blob=codecs.decode(o[field], 'base64'))).make_blob(format=self.image_format or 'png')), mimetype=mimetype, filename=attachment.datas_fname, mtime=self.get_mtime(attachment))
            return http.send_file(BytesIO(self.run(self.attachment_to_img(attachment)).make_blob(format=self.image_format or 'png')), mimetype=mimetype, filename=attachment.datas_fname, mtime=self.get_mtime(attachment))
        #~ return http.send_file(self.run(self.url_to_img(url)), filename=url)
        return http.send_file(BytesIO(self.run(Image(filename=url)).make_blob(format=self.image_format or 'png')),mimetype=mimetype)

    @api.model
    def get_mimetype(self, attachment=None, model=None, field=None, id=None):
        res = 'image/%s' % (self.image_format if self.image_format else 'png')
        if attachment and attachment.mimetype:
            res = attachment.mimetype
        if model == 'ir.attachment' and field == 'datas':
            res = self.env[model].browse(id).mimetype
        if self.image_format == "progressive_jpg":
            res = "image/jpg"
        return res

    def run(self, image, **kwargs):   # return a image with specified recipe
        kwargs.update({p.name: p.value for p in self.param_ids})
        kwargs.update({p.name: p.value for p in self.param_ids.filtered(lambda p: p.device_type == request.session.get('device_type','md'))})    #get parameters from recipe
        #TODO: Remove time import once caching is working
        import time
        # ~ company = request.website_id.company_id if request.website_id else self.env.user.company_id
        company = self.env.user.company_id

        MagickEvaluateImage = wand.api.library.MagickEvaluateImage
        MagickEvaluateImage.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]
        def convert(self, operation, argument):
            MagickEvaluateImage(
                self.wand,
                wand.image.EVALUATE_OPS.index(operation),
                self.quantum_range * float(argument))

        kwargs.update({
            'time': time,
            'Image': Image,
            'Color': Color,
            'display': display,
            'Drawing': Drawing,
            'image': image,
            '_logger': _logger,
            'user': self.env['res.users'].browse(self._uid),
            'record': kwargs.get('record',None),
            'http': http,
            'request': request,
            # ~ 'website': request.website,
            'convert': convert,
            #~ 'logo': Image(blob=company.logo.decode('base64')),
            #~ 'logo_web': Image(blob=company.logo_web.decode('base64')),
            })
        try:
            eval(self.recipe, kwargs, mode='exec', nocopy=True)
        except ValueError:
            e = sys.exc_info()
            _logger.error('ImageMagick Recipe: %s' % ''.join(traceback.format_exception(e[0], e[1], e[2])))
        return kwargs.get('res', image or None) or Image(filename=get_module_path('web') + '/static/src/img/placeholder.png')

class set_device_type(http.Controller):

    @http.route(['/set_device_type'], type='json', auth='public', website=True)
    def set_device_type(self, width=992, **kw):
        if width < 768:
            request.session['device_type'] = 'xs'
        elif width >= 768 and width < 992:
            request.session['device_type'] = 'sm'
        elif width >= 992 and width < 1200:
            request.session['device_type'] = 'md'
        else:
            request.session['device_type'] = 'lg'


class image_recipe_param(models.Model):
    _name = "image.recipe.param"
    _description = """
   Device Type == Extra small devices    Small devices       Medium devices      Large devices
                   Phones (<768px)        Tablets (≥768px)    Desktops (≥992px)   Desktops (≥1200px)
   column ca       auto                     ~62px                   ~81px            ~97px
   gutter 15+15 px

   device_type is saved in session by a javascript / json-controller

    """

    name = fields.Char(string='Name')
    device_type = fields.Selection([('xs','Extra Small'),('sm','Small'),('md','Medium'),('lg','Large'),('','None')],string='Device Type',default='')
    value = fields.Char(string='Value')
    recipe_id = fields.Many2one(comodel_name='image.recipe', string='Recipe')
    #~ type = fields.Selection([('string', 'String'), ('float', 'Float'), ('int', 'Integer'), ('', '')], default='string')

    #~ @api.multi
    #~ def get_value(self):
        #~ if not self.type or self.type == string:
            #~ #Keep current recipes working
            #~ return value
        #~ elif self.type == 'float':
            #~ return float(self.value)
        #~ elif self.type == 'int':
            #~ return int(self.value)
