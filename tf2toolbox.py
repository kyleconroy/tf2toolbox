"""
This is TF2Toolbox in Flask Python!
"""

from __future__ import with_statement

from collections import defaultdict
import contextlib
import datetime
import difflib
from email import Encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import simplejson as json
import smtplib
import time
import urllib2
import xml.etree.ElementTree as xml
from xml.parsers.expat import ExpatError

import bpdata

from flask import *

app = Flask(__name__)
# Configuration
app.config.from_pyfile('config.py')
app.jinja_env.trim_blocks = True

# News messages
HOME_NEWS_MSG = ''
BPTEXT_NEWS_MSG = ''
METAL_NEWS_MSG = ''
WEAPONS_NEWS_MSG = ''

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def index():
  stime = time.time()
  template_info = {'nav_cell': 'Home', 'news_msg': HOME_NEWS_MSG,'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    set_user_session(template_info, request.form['steamURL'])
  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('index.html', template_info=template_info, session=session)

@app.route('/about', methods=['GET', 'POST'])
def about():
  stime = time.time()
  template_info = {'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    if request.form['form_id'] == 'signin':
      set_user_session(template_info, request.form['steamURL'])
  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('about.html', template_info=template_info, session=session)

@app.route('/donate', methods=['GET', 'POST'])
def donate():
  stime = time.time()
  template_info = {'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    if request.form['form_id'] == 'signin':
      set_user_session(template_info, request.form['steamURL'])
  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('donate.html', template_info=template_info, session=session)

@app.route('/bptext', methods=['GET', 'POST'])
def bptext():
  stime = time.time()
  template_info = {'nav_cell': 'Backpack Text', 'news_msg': BPTEXT_NEWS_MSG, 'signin_action': '/bptext', 'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    if request.form['form_id'] == 'signin':
      set_user_session(template_info, request.form['steamURL'])

    elif request.form['form_id'] == 'bptext':
      if 'steamID' in session:
        bp_json = get_user_backpack(template_info, session['steamID'])
        if 'error_msg' not in template_info:
          bp_parse(template_info, bp_json, request.form, session)
      template_info['py_time'] = time.time() - stime - template_info['api_time']
      return render_template('bptext_result.html', template_info=template_info, session=session)

  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('bptext_form.html', template_info=template_info, session=session)

@app.route('/metal', methods=['GET', 'POST'])
def metal():
  stime = time.time()
  template_info = {'nav_cell': 'Metal Maker', 'news_msg': METAL_NEWS_MSG, 'signin_action': '/metal', 'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    if request.form['form_id'] == 'signin':
      set_user_session(template_info, request.form['steamURL'])

    elif request.form['form_id'] == 'metal':
      if 'steamID' in session:
        bp_json = get_user_backpack(template_info, session['steamID'])
        if 'error_msg' not in template_info:
          bp_metal(template_info, bp_json, request.form, session)
      template_info['py_time'] = time.time() - stime - template_info['api_time']
      return render_template('metal_result.html', template_info=template_info, session=session)

  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('metal_form.html', template_info=template_info, session=session)

@app.route('/weapons', methods=['GET', 'POST'])
def weapons():
  stime = time.time()
  template_info = {'nav_cell': 'Weapon Stock', 'news_msg': WEAPONS_NEWS_MSG, 'signin_action': '/weapons', 'api_time': 0, 'py_time': 0}
  if request.method == 'POST':
    if request.form['form_id'] == 'signin':
      set_user_session(template_info, request.form['steamURL'])
  if 'steamID' in session:
    bp_json = get_user_backpack(template_info, session['steamID'])
    if 'error_msg' not in template_info:
      bp_weapons(template_info, bp_json, session)

  template_info['py_time'] = time.time() - stime - template_info['api_time']
  return render_template('weapon_stock.html', template_info=template_info, session=session)

@app.errorhandler(500)
def internal_server_error(e):
  # Create the error message.
  error_msg = {'error': str(e), 'request': str(request), 'form': str(request.form), 'session': str(session)}

  if app.config['SEND_MAIL'] and not app.debug:
    send_notification_email('TF2Toolbox ERROR: %s' % time.ctime(time.time()), str(error_msg))
    print '[500 ERROR] Error email successfully sent!'

  return render_template('500.html', error_info=error_msg)

def set_user_session(template_info, steamURL):
  """
  Given a Steam Community URL, sets the following session variables for the current user:
    * username
    * avatar
    * steamID
    * num_bp_slots
    * customURL

  In the case of an error, adds an error message to template_info.
  """
  session.pop('username', None)
  session.pop('avatar', None)
  session.pop('steamID', None)
  session.pop('num_bp_slots', None)
  session.pop('customURL', None)

  if not steamURL.startswith('http://steamcommunity.com/id/') and not steamURL.startswith('http://steamcommunity.com/profiles/'):
    template_info['error_msg'] = "That was not a valid Steam Community URL.\n"
    return

  steamURL += "?xml=1"

  try:
    rtime = time.time()
    url_file = urllib2.urlopen(steamURL)
    template_info['api_time'] += time.time() - rtime
    user_data = xml.XML(url_file.read())
    url_file.close()
    for child in user_data:
      if child.text is None:
        continue
      if child.tag == 'steamID':
        if not child.text:
          template_info['error_msg'] = 'This user has not yet set up his/her Steam Community profile.'
          return
        session['username'] = child.text
      elif child.tag == 'avatarMedium':
        session['avatar'] = child.text
      elif child.tag == 'steamID64':
        session['steamID'] = child.text
      elif child.tag == 'customURL':
        session['customURL'] = child.text
  except urllib2.URLError:
    template_info['error_msg'] = "We were unable to retrieve that URL. Please try again!\n"
    return
  except UnicodeEncodeError:
    template_info['error_msg'] = "Your URL contained an invalid character. Make sure that URL points to an existing Steam Community page!"
    return
  except ExpatError:
    pass

  if 'username' not in session or 'avatar' not in session or 'steamID' not in session:
    template_info['error_msg'] = "We were unable to retrieve info for that profile.\n"
    return

  bp_json = get_user_backpack(template_info, session['steamID'])
  if not bp_json:
    return
  session['num_bp_slots'] = bp_json['result']['num_backpack_slots']


def get_user_backpack(template_info, steamID):
  """
  Given an user's Steam ID, returns the backpack as a JSON object.

  In the case of an error, adds an error message to template_info.
  """
  backpack_url = "http://api.steampowered.com/IEconItems_440/GetPlayerItems/v0001/?SteamID=" + steamID + "&key=" + app.config['STEAM_API_KEY']
  try:
    rtime = time.time()
    url_file = urllib2.urlopen(backpack_url)
    template_info['api_time'] += time.time() - rtime
    bp_json = json.load(url_file)
  except urllib2.URLError:
    template_info['error_msg'] = "We were unable to retrieve that user's backpack. The URL may be wrong or the SteamAPI may be down.\n"
    return None

  status = bp_json['result']['status']
  if status == 1: #backpack validation
    return bp_json
  elif status == 15:
    template_info['error_msg'] = "Sorry, this user's backpack is private.\n"
  elif status == 8 or status == 18:
    template_info['error_msg'] = "Invalid SteamID.\n"
  return None

def pretty(json_obj):
  print json.dumps(json_obj, sort_keys=True, indent=2)



def bp_weapons(template_info, bp, session_info):
  """
  Given a JSON representation of a backpack,  and a copy of the user's session info (steamID, customURL, etc.),
  returns the following in template_info.

    * Weapon info on the backpack
    * Errors if needed.

  """

  # Result schema;
  """
  'result': {
    'Scout': {
      'essential': {'Sandman': True, 'Soda Popper': False}
      'alternative': {'Three-Rune Blade': False}
    }
    'Soldier'...
    'Multiple'
  }
  """
  schema = get_schema(template_info)
  if not schema:
    template_info['error_msg'] = "Could not retrieve the TF2 Item Schema.\n"
    return

  result = {
    'ordered_classes': ['Scout', 'Soldier', 'Pyro', 'Demoman', 'Heavy', 'Engineer', 'Medic', 'Sniper', 'Spy', 'Multiple'],
    'Special': {'alternative': {}}
  }
  for cls in result['ordered_classes']:
    result[cls] = {'essential': {}, 'alternative': {}}

  # Load the schema into an usable form, with defindexes as keys.
  s = {}
  for entry in schema['result']['items']:
    # Load the weapon list.
    if entry.get('item_slot', None) in ['primary', 'secondary', 'melee', 'pda', 'pda2'] and entry['item_class'] != 'slot_token':

      # Skip multiclass stock upgradeables.
      if entry.get('defindex') >= 190 and entry.get('defindex') <= 212:
        continue
      used_by = entry.get('used_by_classes', None)
      item_name = entry['item_name']

      # Categorize the weapon. Is it essential (adds new functionality to game?) or alternative (replicates existing functionality/promotional)
      # Is it used by one class or multiple?
      # Is it a stock weapon? (defindex 0-30). If so, initialize to True.
      category = 'essential'
      if item_name in bpdata.ALT_WEAPONS or item_name in bpdata.LIMITED_WEAPONS:
        category = 'alternative'

      if not used_by or len(used_by) > 1: # Special case for Saxxy - used_by = None
        cls = 'Multiple'
      else:
        cls = used_by[0]

      if item_name not in result[cls][category]:
        if entry.get('defindex') <= 30:
          result[cls][category][item_name] = [True, entry.get('image_url')]
        else:
          result[cls][category][item_name] = [False, entry.get('image_url')]

      s[entry['defindex']] = {'name': entry['item_name'],
                              'used_by': cls,
                              'category': category
                             }

  # Parse each item!
  for item in bp['result']['items']:
    # Skip non-indexed weapons.
    if item['defindex'] not in s:
      continue

    cls = s[item['defindex']]['used_by']
    category = s[item['defindex']]['category']
    name = s[item['defindex']]['name']

    result[cls][category][name][0] = True

  template_info['result'] = result


def bp_metal(template_info, bp, form, session_info):
  """
  Given a JSON representation of a backpack, the user's request form,
  and a copy of the user's session info (steamID, customURL, etc.), returns the following in template_info.

    * Metal info on the backpack
    * Errors if needed.

  """
  schema = get_schema(template_info)
  if not schema:
    template_info['error_msg'] = "Could not retrieve the TF2 Item Schema.\n"
    return

  # Load the schema into an usable form, with defindexes as keys.
  s = {}
  for entry in schema['result']['items']:
    s[entry['defindex']] = {'name': entry['item_name'],
                            'slot': entry.get('item_slot', None),
                            'class': entry['item_class'],
                            'craft': entry.get('craft_material_type', None),
                            'image': entry['image_url'],
                            'used_by': entry.get('used_by_classes', None)
                           }

  # Load in schema quality mappings: 0 -> "Normal", 1 -> "Genuine"
  s['qualities'] = {}
  for quality in schema['result']['qualities']:
    s['qualities'][schema['result']['qualities'][quality]] = schema['result']['qualityNames'][quality]


  # Set up the result schema.
  result = {
    'ordered_classes': ['Scout', 'Soldier', 'Pyro', 'Demoman', 'Heavy', 'Engineer', 'Medic', 'Sniper', 'Spy', 'Multiple'],
    'weapons': {},
    'v_all_count': 0,
    'nv_all_count': 0,
    'v_primary_count': 0,
    'nv_primary_count': 0,
    'v_secondary_count': 0,
    'nv_secondary_count': 0,
  }
  for cls in result['ordered_classes']:
    result['weapons'][cls] = {'standard': {}, 'special': [], 'total_s_count': 0, 'total_v_count': 0, 'total_nv_count': 0} # standard -> 'Item Name' {picture, nv_count, v_count}. special -> (picURL, altText)

  # Parse each item!
  for item in bp['result']['items']:

    # Skip invalid pages
    if 'all' not in form.getlist('pages[]'):
      pages = [int(page) for page in form.getlist('pages[]')]
      inv_page = ((item['inventory'] & 0xFFFF) - 1) / 50 + 1
      if inv_page not in pages:
        continue

    # Set item info from schema
    item['craft'] = s[item['defindex']]['craft']

    # If the item is a craftable weapon, count it!
    if item['craft'] == 'weapon':
      item['slot'] = s[item['defindex']]['slot']
      item['name'] = s[item['defindex']]['name']
      item['class'] = s[item['defindex']]['class']
      item['used_by'] = s[item['defindex']]['used_by']
      item['image'] = s[item['defindex']]['image']
      quality = s['qualities'][item['quality']]

      # Log item slot and count.
      if quality == 'Vintage':
        result['v_all_count'] += 1
      elif quality == 'Unique':
        result['nv_all_count'] += 1

      if item['slot'] in ['primary', 'secondary']:
        if quality == 'Vintage':
          result['v_' + item['slot'] + '_count'] += 1
        elif quality == 'Unique':
          result['nv_' + item['slot'] + '_count'] += 1

      # Figure out which TF2 class the item goes in
      if not item['used_by']:
        print '[WTF] Item not used by any class? %s' % item['name']
      elif len(item['used_by']) > 1:
        use_class = 'Multiple'
      elif len(item['used_by']) == 1:
        use_class = item['used_by'][0]

      # Classify the item.
      # Special weapons are any quality besides Unique/Vintage, or Vintage Offlevel, Named, or Described.
      if quality not in ['Unique', 'Vintage'] or (quality == 'Vintage' and (item['level'] not in bpdata.WEAPON_LEVEL_MAP or item['name'] not in bpdata.WEAPON_LEVEL_MAP[item['level']])) or 'custom_name' in item or 'custom_desc' in item:
        suffix_tags = []
        if 'custom_name' in item:
          display_name = item['custom_name']
          suffix_tags.append('%s%s' % (quality+' ' if quality != 'Unique' else '', item['name']))
        else:
          display_name = '%s%s' % (quality+' ' if quality != 'Unique' else '', item['name'])

        if quality == 'Vintage' and (item['level'] not in bpdata.WEAPON_LEVEL_MAP or item['name'] not in bpdata.WEAPON_LEVEL_MAP[item['level']]):
          suffix_tags.append('Level %d' % item['level'])

        if 'custom_desc' in item:
          suffix_tags.append('Description: %s' % item['custom_desc'])

        suffix = (' (%s)' % ', '.join(suffix_tags)) if suffix_tags else ''

        result['weapons'][use_class]['special'].append(('%s%s' % (display_name, suffix), item['image']))
        result['weapons'][use_class]['total_s_count'] += 1

      # Non special items just get entered.
      else:
        if item['name'] not in result['weapons'][use_class]['standard']:
          result['weapons'][use_class]['standard'][item['name']] = \
            {'image': item['image'],
             'v_count': 1 if quality == 'Vintage' else 0,
             'nv_count': 1 if quality == 'Unique' else 0
            }
        else:
          if quality == 'Vintage':
            result['weapons'][use_class]['standard'][item['name']]['v_count'] += 1
          elif quality == 'Unique':
            result['weapons'][use_class]['standard'][item['name']]['nv_count'] += 1
        if quality == 'Vintage':
          result['weapons'][use_class]['total_v_count'] += 1
        elif quality == 'Unique':
          result['weapons'][use_class]['total_nv_count'] += 1


  template_info['result'] = result
  template_info['metal_params'] = metal_form_to_params(form)

  return


def bp_parse(template_info, bp, form, session_info):
  """
  Given a JSON representation of a backpack, the user's request form,
  and a copy of the user's session info (steamID, customURL, etc.), returns the following in template_info.

    * A BBCode representation of the backpack
    * A list of status on what parts of the backpack are being displayed
    * Errors if needed.

  """
  schema = get_schema(template_info)
  if not schema:
    template_info['error_msg'] = "Could not retrieve the TF2 Item Schema.\n"
    return

  # Load the schema into an usable form, with defindexes as keys.
  s = {}
  for entry in schema['result']['items']:
    used_by_classes = entry.get('used_by_classes', None)
    s[entry['defindex']] = {'name': entry['item_name'],
                            'slot': entry.get('item_slot', None),
                            'class': entry['item_class'],
                            'blacklist': is_blacklisted(entry),
                            'used_by': 'Multiple' if not used_by_classes or len(used_by_classes) > 1 else used_by_classes[0]
                            }

  # Load in schema quality mappings: 0 -> "Normal", 1 -> "Genuine"
  s['qualities'] = {}
  for quality in schema['result']['qualities']:
    s['qualities'][schema['result']['qualities'][quality]] = schema['result']['qualityNames'][quality]

  # Load in schema particle effects
  s['particles'] = {}
  for particle in schema['result']['attribute_controlled_attached_particles']:
    s['particles'][particle['id']] = particle['name']

  # Set up the result schema.
  result = {
    'CATEGORY_ORDER': [category for category in bpdata.BPTEXT_FORM_CATEGORIES if category in form],
    'WEAPON_CATEGORIES': ['Strange Weapons', 'Genuine Weapons', 'Normal Weapons', 'Vintage Weapons']
  }
  for category in bpdata.BPTEXT_FORM_CATEGORIES:
    result[category] = {}

  # Set up seen class sets for hats and weapons.
  if form['output_sort'] == 'class':
    seen_hat_classes = set()
    seen_weapon_classes = set()

  # Parse each item!
  # The sort_key variables are important for sorting the output.
  # Regular alphabetical sort key: ('Team Captain Untradeable Gifted Team Spirit', 150, 99)
  # (Item w/tags, craftnum, level)
  #
  # Class based sort key for HATS AND WEAPONS: (10, 'Team Captain Untradeable Gifted Pink', 150, 99)
  # The 10 represents Team Captain as a Multiple class item, hence sorting after Scout items (code 1),
  # Soldier items (code 2), etc.
  #
  # We also have special subcategory sort keys for class based sort.
  # The scout one looks like this: (1, 0, 'Scout')
  # This way, it gets sorted ahead of all the Scout weapons/hats (due to the 0).
  for item in bp['result']['items']:

    # Set item info from schema
    item['name'] = s[item['defindex']]['name']
    item['slot'] = s[item['defindex']]['slot']
    item['class'] = s[item['defindex']]['class']
    item['blacklist'] = s[item['defindex']]['blacklist']
    item['used_by'] = s[item['defindex']]['used_by']

    # Get item attributes
    item['attr'] = {}
    if 'attributes' in item:
      for attribute in item['attributes']:
        if attribute['defindex'] == 142:
          item['attr']['paint'] = int(attribute['float_value']) # 1.0 -> Team Spirit.
        elif attribute['defindex'] == 186:
          item['attr']['gifted'] = True
        elif attribute['defindex'] == 229 and (attribute['value'] <= 100 or 'display_craft_num' in form):
          item['attr']['craftnum'] = attribute['value']
        elif attribute['defindex'] == 134:
          item['attr']['particle'] = s['particles'][int(attribute['float_value'])]

    # Skip invalid items
    if should_skip(item, form):
      continue

    # Hats
    if item['slot'] in ['head', 'misc']:
      quality = s['qualities'][item['quality']]
      # Suffixes: Quality tag, Untradeable, Gifted, Painted, CraftNum, Level if specified

      # Get Unusual particle effect
      if quality == 'Unusual' and 'particle' in item['attr']:
        item['name'] = '%s (%s)' % (item['name'], item['attr']['particle'])

      sort_key = [item['name']]
      suffix_tags = []

      # Get craft num, level for sort key.
      craft_num = ''
      if 'attr' in item and 'craftnum' in item['attr']:
        sort_key.append(item['attr']['craftnum'])
        craft_num = ' #%d ' % item['attr']['craftnum']

      if 'display_hat_levels' in form:
        sort_key.append(item['level'])
        suffix_tags.append('Level %d' % item['level'])

      if 'flag_cannot_trade' in item:
        sort_key[0] += ' Untradeable'
        suffix_tags.append('Untradeable')

      if 'gifted' in item['attr']:
        sort_key[0] += ' Gifted'
        suffix_tags.append('Gifted')

      # TODO: Fix dumb array copy hack to get suffix tags correct for plaintext vs bbcode.
      pt_suffix_tags = list(suffix_tags)
      if 'paint' in item['attr']:
        sort_key[0] += ' %s' % bpdata.PAINT_NUMBER_MAP['plaintext'][item['attr']['paint']]
        suffix_tags.append(bpdata.PAINT_NUMBER_MAP[item['attr']['paint']])
        pt_suffix_tags.append(bpdata.PAINT_NUMBER_MAP['plaintext'][item['attr']['paint']])

      suffix = ' (%s)' % ', '.join(suffix_tags) if suffix_tags else ''
      pt_suffix = ' (%s)' % ', '.join(pt_suffix_tags) if pt_suffix_tags else ''

      plaintext_string = '%s%s%s%s' % (quality+' ' if quality != 'Unique' else '', item['name'], craft_num, pt_suffix)
      bbcode_string = '%s%s%s[/color]%s' % (bpdata.QUALITY_BBCODE_MAP[quality], item['name'], craft_num, suffix)

      if item['name'] in bpdata.RARE_PROMO_HATS:
        category = 'Rare Promos'
      elif quality != 'Genuine' and item['name'] in bpdata.PROMO_HATS:
        category = 'Promo Hats'
      else:
        hat_quality = quality if quality in set(['Vintage', 'Genuine', 'Unusual']) else 'Normal'
        hat_quality = 'Unusual' if quality in set(['Community', 'Self-Made', 'Valve']) else hat_quality
        category = '%s Hats' % hat_quality

      # Depending on the output sort, add an extra value to the sort_key.
      if form['output_sort'] == 'class':
        sort_key.insert(0, bpdata.TF2CLASS_SORT_DICT[item['used_by']])
        # If we haven't seen this class before, add it to seen classes.
        if (category, item['used_by']) not in seen_hat_classes:
          seen_hat_classes.add((category, item['used_by']))
          subcat_sort_key = (bpdata.TF2CLASS_SORT_DICT[item['used_by']], 0, item['used_by'])
          result[category][subcat_sort_key] = {'SUBCATEGORY': item['used_by']}
      elif form['output_sort'] == 'release':
        pass

      sort_key = tuple(sort_key)
      add_to_result(result, sort_key, category, plaintext=plaintext_string, bbcode=bbcode_string)



    # Weapons
    elif item['slot'] in ['primary', 'secondary', 'melee', 'pda', 'pda2']:
      quality = s['qualities'][item['quality']]
      # Suffixes: Quality tag, Untradeable, Gifted, CraftNum, Weapon Level for Vintage
      # TODO: Support UHHH and other unusual weapons. Should probably go in Genuine Weapons.

      sort_key = [item['name']]
      suffix_tags = []

      # Get craft num, level for sort key.
      craft_num = ''
      if 'attr' in item and 'craftnum' in item['attr']:
        sort_key.append(item['attr']['craftnum'])
        craft_num = ' #%d ' % item['attr']['craftnum']

      if quality == 'Vintage' and (item['level'] not in bpdata.WEAPON_LEVEL_MAP or item['name'] not in bpdata.WEAPON_LEVEL_MAP[item['level']]):
        sort_key.append(item['level'])
        suffix_tags.append('Level %d' % item['level'])

      if 'flag_cannot_trade' in item:
        sort_key[0] += ' Untradeable'
        suffix_tags.append('Untradeable')

      if 'gifted' in item['attr']:
        sort_key[0] += ' Gifted'
        suffix_tags.append('Gifted')

      suffix = ' (%s)' % ', '.join(suffix_tags) if suffix_tags else ''

      plaintext_string = '%s%s%s%s' % (quality+' ' if quality != 'Unique' else '', item['name'], craft_num, suffix)
      bbcode_string = '%s%s%s[/color]%s' % (bpdata.QUALITY_BBCODE_MAP[quality], item['name'], craft_num, suffix)

      sort_quality = quality
      if quality == 'Unique':
        sort_quality = 'Normal'
      elif quality not in set(['Unique', 'Vintage', 'Strange']):
        sort_quality = 'Genuine'

      category = '%s Weapons' % sort_quality

      # Depending on the output sort, add an extra value to the sort_key.
      if form['output_sort'] == 'class':
        sort_key.insert(0, bpdata.TF2CLASS_SORT_DICT[item['used_by']])
        # If we haven't seen this class before, add it to seen classes.
        if (category, item['used_by']) not in seen_weapon_classes:
          seen_weapon_classes.add((category, item['used_by']))
          subcat_sort_key = (bpdata.TF2CLASS_SORT_DICT[item['used_by']], 0, item['used_by'])
          result[category][subcat_sort_key] = {'SUBCATEGORY': item['used_by']}
      elif form['output_sort'] == 'release':
        pass

      sort_key = tuple(sort_key)

      add_to_result(result, sort_key, category, plaintext=plaintext_string, bbcode=bbcode_string)

    # Paint
    elif item['name'] in bpdata.PAINT_MAP:
      add_to_result(result, item['name'], 'Paint', bbcode=bpdata.PAINT_MAP[item['name']]+'[/color]')

    # Tools
    elif item['class'] in ['tool', 'class_token', 'slot_token'] or item['slot'] == 'action':
      add_to_result(result, item['name'], 'Tools')

    # Metal
    elif item['class'] == 'craft_item':
      add_to_result(result, item['name'], 'Metal')

    # Crate
    elif item['class'] == 'supply_crate':
      add_to_result(result, int(item['attributes'][0]['float_value']), 'Crates', plaintext="Series %d Crate" % int(item['attributes'][0]['float_value']))

  bptext_suffix_tags = []
  if 'display_sc_url' in form:
    bptext_suffix_tags.append('Steam Community URL: http://steamcommunity.com/%s' % ('id/'+session['customURL'] if 'customURL' in session else 'profiles/'+session['steamID']))

  if form['inc_bp_link'] != 'none':
    if form['inc_bp_link'] == 'tf2b':
      bptext_suffix_tags.append('TF2B: http://tf2b.com/%s' % (session['customURL'] if 'customURL' in session else session['steamID']))
    elif form['inc_bp_link'] == 'tf2items':
      bptext_suffix_tags.append('TF2Items: http://tf2items.com/%s' % ('id/'+session['customURL'] if 'customURL' in session else 'profiles/'+session['steamID']))
    elif form['inc_bp_link'] == 'optf2':
      bptext_suffix_tags.append('OPTF2: http://optf2.com/user/%s' % (session['customURL'] if 'customURL' in session else session['steamID']))

  # TODO: Fix icky hack here to append extra line for Reddit
  if form['output_type'] == 'markdown':
    bptext_suffix_tags = [tag+'\n' for tag in bptext_suffix_tags]

  template_info['bptext_result_string'] = bp_to_text(result, 'display_credit' in form, 'only_dup_weps' in form, form['output_type']) + '\n' + '\n'.join(bptext_suffix_tags)

  template_info['bptext_params'] = bptext_form_to_params(form)

def add_to_result(result, sort_key, category, bbcode=None, plaintext=None, subcategory=None):
  """
  Given a result schema, a sort key (usually item_name. +bbcode/plaintext if needed),
  and its category (+subcategory if needed), add it to the result schema.

  bbcode is assigned to bbcode if possible, then to plaintext, then to sort_key.
  plaintext is assigned to plaintext if possible, then to sort_key.
  """
  if not bbcode:
    if plaintext:
      bbcode = plaintext
    else:
      bbcode = sort_key
  if sort_key not in result[category]:
    result[category][sort_key] = defaultdict(int)
  result[category][sort_key]['quantity'] += 1
  result[category][sort_key]['bbcode'] = bbcode
  if plaintext:
    result[category][sort_key]['plaintext'] = plaintext
  else:
    result[category][sort_key]['plaintext'] = sort_key

def get_schema(template_info):
  """
  Returns the TF2 schema in JSON format.
  """
  schema_cache = os.path.join(os.getcwd(), 'static/schema.json')
  schema_url = "http://api.steampowered.com/IEconItems_440/GetSchema/v0001/?key=" + app.config['STEAM_API_KEY'] + "&language=en"
  mtime = 0
  if os.path.exists(schema_cache):
    mtime = os.path.getmtime(schema_cache)

  dt = datetime.datetime.utcfromtimestamp(mtime)

  schema_req = urllib2.Request(schema_url)
  schema_req.add_header('If-Modified-Since', dt.strftime('%a, %d %b %Y %X GMT'))

  print '[SCHEMA] Checking schema at %s for mtime: %s' % (schema_cache, dt.strftime('%a, %d %b %Y %X GMT'))

  try:
    rtime = time.time()
    schema = urllib2.urlopen(schema_req)
    template_info['api_time'] += time.time() - rtime
    print '[SCHEMA] Retrieving new schema.'
    schema_lines = schema.readlines()

    new_schema_cache = open(schema_cache, 'w')
    print '[SCHEMA] Writing new schema cache.'
    new_schema_cache.writelines(schema_lines)
    new_schema_cache.close()

    schema_json = json.loads(''.join(schema_lines))

    if app.config['SEND_MAIL'] and not app.debug:
      send_notification_email('TF2 Schema Update: %s' % time.ctime(time.time()), 'Last modified time was %s' % dt.strftime('%a, %d %b %Y %X GMT'))
      print '[SCHEMA] Update email successfully sent!'

  except urllib2.HTTPError, e:
    print e
    if e.code == 304:
      print '[IMPORTANT] Cached schema is up-to-date!'
      schema = open(schema_cache)
      schema_json = json.load(schema)
      schema.close()
    else:
      return None

  return schema_json


def is_blacklisted(entry):
  """
  Given an item entry from the TF2 Item Schema, determine if it is both
  untradeable and un-gift-wrappable. These items should never appear in the result.
  """
  if 'attributes' in entry:
    for attr in entry['attributes']:
      if attr['name'] == 'cannot trade':
        can_gift_wrap = False
        if 'capabilities' in entry:
          for cap in entry['capabilities']:
            if cap == 'can_gift_wrap' and entry['capabilities'][cap]:
              can_gift_wrap = True
              break
        if not can_gift_wrap:
          return True
          break
  return False

def should_skip(item, form):
  """
  Given a TF2 item JSON object, augmented with information from bp_parse(),
  and an user's form data options, returns True if we should skip parsing this item.
  """
  # Skip invalid pages
  if 'all' not in form.getlist('pages[]'):
    pages = [int(page) for page in form.getlist('pages[]')]
    inv_page = ((item['inventory'] & 0xFFFF) - 1) / 50 + 1
    if inv_page not in pages:
      return True

  # Skip item blacklist. TODO: Fix hack for Director's Vision
  if item['blacklist'] or item['name'] == "Taunt: The Director's Vision":
    return True

  # Skip untradeables if optioned.
  if 'hide_untradeable' in form and 'flag_cannot_trade' in item:
    return True

  # Skip gifted if optioned.
  if 'hide_gifted' in form and 'gifted' in item:
    return True

  return False

BPTEXT_LANGUAGE_SYNTAX = {
  'bbcode': {
    'category_opener': '[b][u]%s[/u][/b][list]',
    'category_opener_w_cred': '[b][u]%s[/u][/b][color=#cd5c5c] (List generated at [URL=http://tf2toolbox.com/bptext]TF2Toolbox.com[/URL])[/color][list]',
    'item_opener': '[*][b]',
    'item_closer': '[/b]',
    'category_closer': '[/list]\n',
    'subcat_exp': '[b]--- %s ---[/b]'
  },
  'plaintext': {
    'category_opener': '%s',
    'category_opener_w_cred': '%s (List generated at TF2Toolbox.com)',
    'item_opener': '',
    'item_closer': '',
    'category_closer': '',
    'subcat_exp': '--- %s ---'
  },
  'markdown': {
    'category_opener': '**%s**\n', # Extra new lines needed for Reddit.
    'category_opener_w_cred': '**%s**\n', # No credit at the top. Credit goes at bottom.
    'item_opener': '* ',
    'item_closer': '',
    'category_closer': '\n',
    'subcat_exp': '\n_%s_\n',
    'parse_text': 'plaintext',
    'bottom_credit': 'List generated at [TF2Toolbox.com](http://tf2toolbox.com/bptext) with help from [JonDum](http://www.reddit.com/r/tf2trade/comments/k2zru/tool_tf2toolboxcom_bbcode_converter/) at Reddit.\n'
  }
}

def bp_to_text(bp, credit, dup_weps_only, language):
  """
  Consolidation function that translates a parsed bp (from bp_parse()) to
  a specified language.
  """
  result_lines = []
  first = True
  for category in bp['CATEGORY_ORDER']:
    if not bp[category]:
      continue
    if credit and first:
      result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['category_opener_w_cred'] % category)
      first = False
    else:
      result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['category_opener'] % category)
    for sort_key in sorted(bp[category].keys()):
      # First check for subcategories. If not a subcategory, then we know its an item entry.
      if 'SUBCATEGORY' in bp[category][sort_key]:
        result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['subcat_exp'] % bp[category][sort_key]['SUBCATEGORY'])
        continue
      if dup_weps_only and category in bp['WEAPON_CATEGORIES'] and bp[category][sort_key]['quantity'] == 1:
        continue
      text_type = BPTEXT_LANGUAGE_SYNTAX[language]['parse_text'] if 'parse_text' in BPTEXT_LANGUAGE_SYNTAX[language] else language
      quantity_string = ' x %d' % bp[category][sort_key]['quantity'] if bp[category][sort_key]['quantity'] > 1 else ''
      result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['item_opener'] + bp[category][sort_key][text_type] + quantity_string + BPTEXT_LANGUAGE_SYNTAX[language]['item_closer'])
    result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['category_closer'])

  if credit and 'bottom_credit' in BPTEXT_LANGUAGE_SYNTAX[language]:
    result_lines.append(BPTEXT_LANGUAGE_SYNTAX[language]['bottom_credit'])

  return '\n'.join(result_lines)


def bptext_form_to_params(form):
  """
  Given a form request from bptext, return a list of human-readable parameters
  for the user to read on the side of the result.

  The template will go through each element in the list and create a <li> bullet for each.
  """
  params_list = []

  # Items printing
  items_list = [opt.lower() for opt in bpdata.BPTEXT_FORM_CATEGORIES if opt in form]
  if not items_list:
    params_list.append('Displaying no items. Huh?')
  else:
    params_list.append('Displaying %s.' % ', '.join(items_list))

  # Options printing
  if 'only_dup_weps' in form:
    params_list.append('Only showing duplicate weapons!')
  if 'hide_untradeable' in form and 'hide_gifted' in form:
    params_list.append('Hiding untradeable and gifted items.')
  elif 'hide_gifted' in form:
    params_list.append('Hiding gifted items.')
  elif 'hide_untradeable' in form:
    params_list.append('Hiding untradeable items.')

  # Print backpack pages displayed.
  page_list = form.getlist('pages[]')
  if 'all' in page_list:
    params_list.append('Displaying all backpack pages.')
  elif not page_list:
    params_list.append('Not displaying any backpack pages. Huh?')
  elif len(page_list) == 1:
    params_list.append('Displaying backpack page %s.' % str(page_list[0]))
  else:
    params_list.append('Displaying backpack pages %s.' % ', '.join([str(num) for num in page_list]))

  # Output sort.
  if form['output_sort'] == 'alpha':
    params_list.append('Sorting items alphabetically.')
  elif form['output_sort'] == 'class':
    params_list.append('Sorting items by TF2 class (Scout, Soldier, Pyro, etc.).')
  elif form['output_sort'] == 'release':
    params_list.append('Sorting items by TF2 update (Uber Update, etc.).')

  # Output type
  if form['output_type'] == 'bbcode':
    params_list.append('Translated backpack to BBCode.')
  elif form['output_type'] == 'markdown':
    params_list.append('Translated backpack to Reddit Markdown. Huge thanks to <a href="http://www.reddit.com/r/tf2trade/comments/k2zru/tool_tf2toolboxcom_bbcode_converter/">JonDum at Reddit</a> for the help and inspiration!')
  elif form['output_type'] == 'plaintext':
    params_list.append('Translated backpack to plaintext.')

  return params_list

def metal_form_to_params(form):
  """
  Given a form request from metal, return a list of human-readable parameters
  for the user to read on the side of the result.

  The template will go through each element in the list and create a <li> bullet for each.
  """
  params_list = []

  # Print backpack pages displayed.
  page_list = form.getlist('pages[]')
  if 'all' in page_list:
    params_list.append('Displaying all backpack pages.')
  elif not page_list:
    params_list.append('Not displaying any backpack pages. Huh?')
  elif len(page_list) == 1:
    params_list.append('Displaying backpack page %s.' % str(page_list[0]))
  else:
    params_list.append('Displaying backpack pages %s.' % ', '.join([str(num) for num in page_list]))

  return params_list

def send_notification_email(subject, message):
  # Read the email info file and parse
  msg = MIMEText(message)
  msg['Subject'] = subject
  msg['To'] = app.config['EMAIL_RECEIVER']
  # Send the email via Gmail.
  s = smtplib.SMTP(app.config['SMTP_SERVER'])
  s.ehlo()
  s.starttls()
  s.ehlo()
  s.login(app.config['EMAIL_SENDER'], app.config['EMAIL_SENDER_PASSWORD'])
  s.sendmail(app.config['EMAIL_SENDER'], app.config['EMAIL_RECEIVER'], msg.as_string())
  s.quit()

if __name__ == '__main__':
  app.run()
