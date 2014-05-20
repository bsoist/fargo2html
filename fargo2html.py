#!/usr/bin/env python
"# encoding: utf-16"
"""
fargo2html.py

Created by Bill Soistmann on 2013-10-06.

Accepts a URL to a Fargo outline as first argument and will render it to html files.

See README.md for more information about importing or using a config file.

Command Line Examples:

    ./fargo2html.py http://dl.dropbox.com/s/ran/myoutline.opml

will render the outline to the folder ~/fargo_outlines/myoutline

To create a ZIP of the folder, use --z

    ./fargo2html.py --z http://dl.dropbox.com/s/ran/myoutline.opml

To specify a folder to render to, use

    ./fargo2html.py -f/path/to/folder http://dl.dropbox.com/s/ran/myoutline.opml

To upload to S3
    ./fargo2html.py --us3 -f/path/to/folder http://dl.dropbox.com/s/ran/myoutline.opml

This will upload to a bucket named folder for the default s3 profile. NOTE: Requires folder2s3.py and boto and a valid boto config file. See the readme for folder2s3.py for more info.

To specify a profile and/or bucket use ...

    ./fargo2html.py -pme -bmybucket -f/path/to/folder http://dl.dropbox.com/s/ran/myoutline.opml

This will upload to bucket mybucket for profile me.

NOTES:
* -us3 is not necessary when specifying either a bucket of profile.
* If you specify a bucket or profile along with a different upload method ( which are not supported yet ), s3 will be assumed.
* Only files newer than on S3 will be uploaded. To change this behavior, you have three options
1. Delete the local folder before you start.
2. Empty the S3 bucket before you start
3. Don't use the S3 option and then call folder2s3.upload() yourself with a replaceAll=True


"""

import sys, os, shutil, getopt, re, datetime, random, errno, itertools, operator
import opml, requests, zipfile, PyRSS2Gen
from ConfigParser import ConfigParser

DEBUG = False

MONTHS = dict([(datetime.date(2013,i,1).strftime("%B"),"%02d" % i) for i in range(1,13)])

DEFAULT_RULES = [
    None,
    {
    'no-icons':False,
    'expanded':False,
    'outline-indent': '30px',
    'outline-space': '10px'
    },
    {
    'no-icons':False,
    'expanded':False,
    'outline-indent': '30px',
    'outline-space': '10px'
    }
]

DEFAULT_GLOSSARY = {}
# Add Macros to GLOSSARY
DEFAULT_GLOSSARY['<%useRules%>'] = """
<link href="http://outliner.smallpicture.com/rules.css" rel="stylesheet" />
<link href="http://wcscs.cloudvent.net/rules.css" rel="stylesheet" />
<script src="http://outliner.smallpicture.com/rules.js"></script>
"""

DEFAULT_GLOSSARY['<%rssLink ()%>'] = """
<link rel="alternate" type="application/rss+xml" title="RSS" href="http://wcscs.smallpict.com/rss.xml" />
"""
DEFAULT_GLOSSARY['<%comments%>'] = "<!-- COMMENTS -->"

FORMATS = {
    'outline': {
        'body_open': '<div class="divOutlineBody">',
        'list_header_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;" ec-id="%(ID)s"><a class="ec ecIcon expanded"><i class="icon-caret-right expandIcon"></i><i class="icon-caret-down collapseIcon"></i></a><a class="ec"><span class="spanOutlineText spanExpandableText">',
        'list_open': '<div class="divOutlineList" style="padding-left: %(outline-indent)s;">',
        'item_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;">',
        'item_close': '</span></p>',
        'list_close': '</div>',
        'list_header_close': '</span></a></p>',
        'body_close': '</div>'
    },
    'outlinex': {
        'body_open': '<div class="divOutlineBody">',
        'list_header_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;" ec-id="%(ID)s"><a class="ec ecIcon expanded"><i class="icon-caret-right expandIcon"></i><i class="icon-caret-down collapseIcon"></i></a><a class="ec"><span class="spanOutlineText spanExpandableText">',
        'list_open': '<div class="divOutlineList" style="padding-left: %(outline-indent)s;">',
        'item_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;">',
        'item_close': '</span></p>',
        'list_close': '</div>',
        'list_header_close': '</span></a></p>',
        'body_close': '</div>'
    },
    'bloghome': {
        'body_open': '<div class="divOutlineBody">',
        'list_header_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;" ec-id="%(ID)s"><a class="ec ecIcon expanded"><i class="icon-caret-right expandIcon"></i><i class="icon-caret-down collapseIcon"></i></a><a class="ec"><span class="spanOutlineText spanExpandableText">',
        'list_open': '<div class="divOutlineList" style="padding-left: %(outline-indent)s;">',
        'item_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;">',
        'item_close': '</span></p>',
        'list_close': '</div>',
        'list_header_close': '</span></a></p>',
        'body_close': '</div>'
    },
    'bloghomex': {
        'body_open': '<div class="divOutlineBody">',
        'list_header_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;" ec-id="%(ID)s"><a class="ec ecIcon expanded"><i class="icon-caret-right expandIcon"></i><i class="icon-caret-down collapseIcon"></i></a><a class="ec"><span class="spanOutlineText spanExpandableText">',
        'list_open': '<div class="divOutlineList" style="padding-left: %(outline-indent)s;">',
        'item_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;">',
        'item_close': '</span></p>',
        'list_close': '</div>',
        'list_header_close': '</span></a></p>',
        'body_close': '</div>'
    },
        'listoflinks': {
        'body_open': '<div class="divOutlineBody">',
        'list_header_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;" ec-id="%(ID)s"><a class="ec ecIcon expanded"><i class="icon-caret-right expandIcon"></i><i class="icon-caret-down collapseIcon"></i></a><a class="ec"><span class="spanOutlineText spanExpandableText">',
        'list_open': '<div class="divOutlineList" style="padding-left: %(outline-indent)s;">',
        'item_open': '<p class="divOutlineItem" style="padding-bottom: %(outline-space)s;">',
        'item_close': '</span></p>',
        'list_close': '</div>',
        'list_header_close': '</span></a></p>',
        'body_close': '</div>'
    }
}

class Usage(Exception):
    def __init__(self, msg):
        self.message = msg

class Ruleset(object):
    def __init__(self,rules):
        self.rules = rules

    def __getitem__(self,i):
        try:
            return self.rules[i]
        except:
            return self.rules[-1]

def setTheme(option):
    parts = option.split(' ')
    try:
        theme = parts[1][1:-1].lower()
    except:
        theme = "spacelab"
    return {'<%useBootstrap%>': """
        <link href="http://static.smallpicture.com/bootswatch/%s/bootstrap.min.css" rel="stylesheet" />
        <script src="http://static.smallpicture.com/bootstrap/js/jquery-1.9.1.min.js"></script>
        <script src="http://static.smallpicture.com/bootstrap/js/bootstrap.min.js"></script>
        <link href="http://static.smallpicture.com/bootstrap/css/bootstrap-responsive.min.css" rel="stylesheet">
        <link rel="stylesheet" href="http://static.smallpicture.com/concord-assets/fontawesome/3.2.1/css/font-awesome.min.css">
        """ % theme }

def setGoogleAnalytics(option):
    parts = option.split(' ')
    try:
        ga_id = parts[1][1:-1]
    except:
        return ""
    return {'<%googleAnalytics ()%>': """
    <script>var _gaq = _gaq || []; _gaq.push(['_setAccount', '%s']); _gaq.push(['_setDomainName', 'wcscs.smallpict.com']); _gaq.push(['_trackPageview']); (function() {var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true; ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js'; var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s); })();</script>
    """ % ga_id}

GLOSSARY_FUNCTIONS = {
'#bootstrapTheme': setTheme,
'#googleAnalyticsID': setGoogleAnalytics
}

GLOSSARY_OPTIONS = GLOSSARY_FUNCTIONS.keys()

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def subData(d,glossary):
    for k,v in glossary.items():
        k = re.sub('\(','\\(',k)
        k = re.sub('\)','\\)',k)
        d = re.sub(k,v,d)
    return d

def removePunc(data):
    for punc in '!:&/#,"':
        data = re.sub(punc,'',data)
    for punc in "?.,'":
        data = re.sub("\%s" % punc, '', data)
    return data

def processRules(template_rules,specific_rules):
    rules = DEFAULT_RULES[:]
    for ruleset in [template_rules,specific_rules]:
        if ruleset:
            rules_to_change = [0,0]
            for rule in ruleset:
                m = re.match('<rule level="(.*)" to="(.*)">',rule)
                if m:
                    rules_to_change = list(m.groups())
                    if rules_to_change[1].lower() == "infinity":
                        rules_to_change[1] = -2 # so I can add one later
                    rules_to_change = map(int,rules_to_change)
                    rules_to_change[1] += 1
                elif rule == "<rule>":
                    rules_to_change = [1,len(rules)-1]
                elif rule == "</rule>":
                    rules_to_change = [0,0]
                else:
                    m = re.match('<(.*)>(.*)<',rule)
                    if m:
                        for i in range(rules_to_change[1] - len(rules)):
                            rules.append(rules[-1].copy())
                        key, value = m.groups()
                        for i in range(rules_to_change[0],rules_to_change[1]):
                                rules[i][key] = value
    return Ruleset(rules)


def grabData(outline,base_rules=None,format=''):
    global DEBUG
    if len(outline) == 0:
        return []
    data = [node.get('text') for node in outline._root.iterdescendants()]
    if '<rules>' in data:
        start,end = data.index('<rules>'),data.index('</rules>')
        rules = data[start+1:end]
    else:
        rules = []
        end = 0
    if not format:
        try:
            content = data[:start] + data[end+1:]
        except:
            content = data
    else:
        rules = processRules(base_rules,rules)
        level = 1
        closings = [None]
        content = [FORMATS[format]['body_open'] % rules[level],FORMATS[format]['list_open'] % rules[level]]
        for i,node in enumerate(outline._root.iterdescendants()):
            try:
                if node.get('type')== 'link':
                        if '<a' not in node.get('text'):
                            node.set('text','<a href="%s">%s</a>' % (node.get('url'), node.get('text')))
            except:
                pass
            if i < end: continue
            count = len(node)
            for c in range(level):
                closing = closings.pop()
                if closing is not None:
                    level -= 1
                    try:
                        this_closing = level*"\t" + closing % rules[level]
                    except:
                        this_closing = level*"\t" + closing
                    content.append(this_closing)
            if count > 0:
                rules[level]['ID'] = "T%s" % i
                content.append("%s%s%s%s" % (level * "\t", FORMATS[format]['list_header_open'] % rules[level], node.get('text'), FORMATS[format]['list_header_close']))
                if rules[level]['expanded']:
                    show = 'show'
                else:
                    show = 'hide'
                content.append('''<div class="%s" id="T%s" name="T%s">''' % (show, i, i)) #'recommendedBloggingT86928'
                content.append(level*"\t" + FORMATS[format]['list_open'] % rules[level])
                closings.append(level*"\t" + "%s\n%s" % (FORMATS[format]['list_close'] % rules[level], "</div>"))
                for c in range(count*level):
                    closings.append(None)
                if count: closings.append(None)
                level += 1
            else:
                content.append("%s%s%s%s" % (level * "\t", FORMATS[format]['item_open'] % rules[level], node.get('text'), FORMATS[format]['item_close']))
                closings.append(None)
        for closing in closings:
            if closing:
                content.append(closing)
        content.append(FORMATS[format]['body_close'] % rules[level])
    return rules, content

def grabChildren(outline):
    return dict([(node.text,grabData(node)) for node in outline])

def getPrevNextLinks(next, prev):
    # TODO
    # next = prev_path_name
    # prev meaning the previous loop, not prev post
    # that's why they are next, prev here
    links = []
    output =  '<span class="nex-prev" style="text-align:right;">'
    if next: links.append('<a href="/%s">Next</a>' % next)
    if prev: links.append('<a href="/%s">Prev</a>' % prev)
    return """
    <div class="nex-prev" style="float:right;">%s</div>
    """ % ("&nbsp;&nbsp;|&nbsp;&nbsp;".join(links))

def makeName(name):
    name = ''.join([namepart.lower().capitalize() for namepart in name.split(' ')])
    return removePunc(name[0].lower() + name[1:])

def getFileName(proposed_name, filenames):
    # TODO - I could probably do this with path_name
    # but since this was already working, I changed behavior for now
    # it replaces existing files
    i = 2
    while proposed_name in filenames:
        proposed_name += str(i)
        i += 1
    return proposed_name

def addCalendar(b,o,t,calendars):
    if b in calendars:
        calendars[b][0].append(o)
    else:
        calendars[b] = [[o],t]
    return calendars

def zipdir(folder):
    zipp = zipfile.ZipFile('%s.zip' % folder, 'w')
    for root, dirs, files in os.walk("%s/" % folder):
        for file in files:
            zipp.write(os.path.join(root,file))
    zipp.close()

def buildFeed(feed_title, feed_link, feed_desc, feed_posts, feed_path):
    rss = PyRSS2Gen.RSS2(
    title = feed_title,
    link = feed_link,
    description = feed_desc,
    lastBuildDate = datetime.datetime.now(),
    items = feed_posts
    )
    rss.write_xml(open(feed_path + "/rss.xml", "w+"))

def parse(outline_url, my_folder, my_home_index_page):
    global DEBUG
    OPTIONS = {}
    TEMPLATES = {}
    PAGES = {}
    FILENAMES = []
    GLOSSARY_COMPLETE = False
    CALENDARS = {}
    GLOSSARY = DEFAULT_GLOSSARY.copy()
    data_folder, my_folder = os.path.split(my_folder)
    working_dir, DATA_FOLDER = os.path.split(data_folder)
    os.chdir(working_dir)
    base_folder = "%s/%s" % (DATA_FOLDER, my_folder)

    mkdir_p(base_folder)
    outline_url = re.sub('www','dl',outline_url)
    if 'usercontent' not in outline_url:
        outline_url = re.sub('dropbox','dropboxusercontent', outline_url)
    outline = list(opml.from_string(requests.get(outline_url).content))


    for i, node in enumerate(outline):
        if node.text == '#glossary':
            GLOSSARY.update(grabChildren(outline.pop(i)))
        elif node.text == '#templates':
            TEMPLATES.update(grabChildren(outline.pop(i)))
        else:
            first_word = node.text.split(' ')[0]
            if first_word in GLOSSARY_OPTIONS:
                try:
                    value = OPTIONS[first_word[1:]]
                except:
                    value = node.text
                GLOSSARY.update(GLOSSARY_FUNCTIONS[first_word](value))

    for k,v in GLOSSARY.items():
        if type(v[0]) == type([]):
            GLOSSARY[k] = ''.join(v[1])

    for k,v in TEMPLATES.items():
        if type(v[0]) == type([]):
            TEMPLATES[k] = (v[0],''.join(v[1]))

    GLOSSARY_COMPLETE = True

    while outline:
        next_node = outline.pop()
        try:
            if next_node.type == 'include':
                real_url = re.sub('dropbox','dropboxusercontent',next_node.url)
                real_url = re.sub('https','http',real_url)
                include = list(opml.from_string(requests.get(real_url).content))
                nodes = include
            else:
                nodes = [next_node]
        except:
            nodes = [next_node]

        for node in nodes:
            try:
                if node.icon == 'calendar':
                    try:
                        i_title = node.name
                    except:
                        i_title = node.text
                    CALENDARS = addCalendar('Home',node,i_title, CALENDARS)
                    continue
            except:
                pass
            try:
                if node[0].icon == 'calendar':
                    try:
                        i_title = node[0].name
                    except:
                        i_title = node.text
                    CALENDARS = addCalendar(node.text,node[0],i_title, CALENDARS)
                    continue
            except:
                pass
            if node.text[0] == '#':
                option = node.text[1:].rstrip().lstrip()
                parts = option.split(' ')
                if len(parts) < 2:
                    OPTIONS[option] = True
                else:
                    key, value = parts[0], ' '.join(parts[1:])
                    if value[0] == '[':
                        value = random.choice([v.strip() for v in value[1:-1].split(',')])
                    elif value[0] == '"':
                        value = value[1:-1]
                    if value.lower() in ['true','false']:
                        OPTIONS[key] = bool(value)
                    else:
                        try:
                            OPTIONS[key] = int(value)
                        except:
                            OPTIONS[key] = value
            else:
                brandLink = '/'
                blogHomeTitle = OPTIONS.get('blogHomeTitle','Home')
                page = {}
                try:
                    this_type = node.type
                except:
                    this_type = 'outline'
                try:
                    rules, template = TEMPLATES[this_type]
                except Exception as e:
                    raise Usage("#templates node required until I pull default templates from Trex. \n\n%s" % e.message)
                template = ''.join(template)
                for k,v in node._root.items():
                    template = re.sub('<%%%s%%>' % k,v,template)
                    page[k] = v
                page_desc = page.get('pageDescription', ' ')
                template = re.sub('<%blogHomeTitle%>', blogHomeTitle, template)
                template = re.sub('<%pageTitle%>', page['text'], template)
                template = re.sub('<%pageDescription%>', page_desc, template)
                if 'name' not in page:
                    page['name'] = makeName(page['text'])
                if 'url' not in page:
                    page['url'] = "/%s" % page['name']
                waste, bodytext = grabData(node, rules, this_type)
                bodytext.append('</div>') # not sure why we need this - something's not right
                bodytext = ''.join(bodytext)
                data = re.sub('<%bodytext%>',bodytext,template)
                page['bodytext'] = bodytext
                template = subData(data, GLOSSARY)
                template = re.sub('<%BRANDMENU%>', '<a class="brand" href="<%BRANDLINK%>"><%BRAND%></a>', template)
                template = re.sub('<%BRAND%>', blogHomeTitle, template)
                template = re.sub('<%BRANDLINK%>', brandLink, template)

                page['data'] = template
                PAGES[page['name']] = page

    for k, v in PAGES.items():
        file_name = getFileName("%s/%s" % (base_folder,v['name']),FILENAMES)
        FILENAMES.append(file_name)
        save_file = False
        new_data = v['data']

        if os.path.exists(file_name):
            fh = open(file_name)
            file_data = fh.read()[:-1]
            fh.close()
            save_file = (file_data != new_data)
        else:
            save_file = True
        if save_file:
            fh = open(file_name, "w+")
            print >>fh, new_data
            fh.close()
            if os.path.basename(file_name) == my_home_index_page:
                print file_name
                fh = open(os.path.join(os.path.split(file_name)[0], "index.html"), "w+")
                print >>fh, new_data
                fh.close()

    blogHomeTitle = OPTIONS.get('blogHomeTitle','Home')
    posts = {"Home": []}
    feedcount = OPTIONS.get('feedCount',20)
    domain = "http://%s" % OPTIONS.get('domainName','')
    feed_posts = []
    for base, calendar_stuff in CALENDARS.items():
        ycals, index_title = calendar_stuff
        page_data, path_name = None, None
        this_post_data, this_path_name = None, None
        while ycals:
            if this_post_data:
                file_name = getFileName("%s/%s" % (base_folder, this_path_name), FILENAMES)
                FILENAMES.append(file_name)
                save_file = False
                new_data = re.sub('<nextprev>', getPrevNextLinks(prev_path_name, path_name), this_post_data)
                if os.path.exists(file_name):
                    fh = open(file_name)
                    file_data = fh.read()[:-1]
                    fh.close()
                    save_file = (file_data != new_data)
                else:
                    save_file = True
                if save_file:
                    fh = open(file_name, "w+")
                    print >>fh, new_data
                    fh.close()
            ycal = ycals.pop()
            try:
                index_desc = ycal.description
            except:
                index_desc = ''
            year_title = ycal.text
            year_name = ycal.text
            year_num = ycal.text
            if base == 'Home':
                brandLink = '/'
                sub_folder = ''
                root_folder = base_folder
                year_path = year_num
            else:
                sub_folder = makeName(base)
                brandLink = "/%s" % sub_folder
                root_folder = "%s/%s" % (base_folder,sub_folder)
                if not os.path.exists(root_folder): os.mkdir(root_folder)
                year_path = "%s/%s" % (sub_folder, year_num)
                if (sub_folder,index_title) not in posts: posts[(sub_folder,index_title)] = []
            year_folder = "%s/%s" % (base_folder, year_path)
            try:
                if not os.path.exists(year_folder): os.mkdir(year_folder)
            except:
                mkdir_p(year_folder)
            for mcal in ycal:
                month_title = mcal.text
                month_name = month_title.split(' ')[0]
                month_num = MONTHS[month_name]
                month_path = "%s/%s" % (year_path, month_num)
                month_folder = "%s/%s" % (year_folder, month_num)
                if not os.path.exists(month_folder): os.mkdir(month_folder)
                for dcal in mcal:
                    day_title = dcal.text
                    day_name = dcal.text
                    day_num = "%02d" % float(day_title.split(' ')[1])
                    day_path = "%s/%s" % (month_path, day_num)
                    day_folder = "%s/%s" % (month_folder, day_num)
                    if not os.path.exists(day_folder): os.mkdir(day_folder)
                    trail = [(year_path,year_title),(month_path,month_title),(day_path,day_title)]
                    trail_links = """
                    <nextprev>
                    <div class="breadcrumbs"><a href="/%s">%s</a> / %s</div>
                    """ % (sub_folder, base, " / ".join(['<a href="/%s/">%s</a>' % (l,n) for l,n in trail]))

                    # using page below because it matches above
                    for node in dcal:
                        prev_post_data = this_post_data
                        prev_path_name = this_path_name
                        this_post_data = page_data
                        this_path_name = path_name
                        page = {}
                        try:
                            this_type = node.type
                        except:
                            this_type = 'outline'
                        rules, template = TEMPLATES[this_type]
                        template = ''.join(template)
                        for k,v in node._root.items():
                            template = re.sub('<%%%s%%>' % k,v,template)
                            page[k] = v
                        page_desc = page.get('pageDescription', index_desc)
                        template = re.sub('<%blogHomeTitle%>', blogHomeTitle, template)
                        template = re.sub('<%pageTitle%>', page['text'], template)
                        template = re.sub('<%pageDescription%>', page_desc, template)
                        if 'name' not in page:
                            page['name'] = makeName(page['text'])
                        if 'url' not in page:
                            page['url'] = "/%s" % page['name']
                        waste, bodytext = grabData(node, rules, this_type)
                        bodytext.append('</div><!--FIX-->') # not sure why we need this - something's not right



                        bodytext = '\n'.join(bodytext)
                        data = re.sub('<%bodytext%>',bodytext,template)
                        page['bodytext'] = bodytext
                        template = re.sub('</h1>', '</h1>%s' % trail_links, subData(data, GLOSSARY))

                        template = re.sub('<%BRANDMENU%>', '<a class="brand" href="<%BRANDLINK%>"><%BRAND%></a>', template)
                        template = re.sub('<%BRAND%>', index_title, template)
                        template = re.sub('<%BRANDLINK%>', brandLink, template)

                        path_name = "%s/%s" % (day_path,page['name'])
                        page['url'] = "/%s" % path_name
                        listing = page['text'], page['bodytext'], page['url'], page_desc
                        if feedcount:
                            try:
                                if node.isFeedItem == 'true':
                                    feed_posts.append(
                                        PyRSS2Gen.RSSItem(
                                        title = page['text'],
                                        link = domain + page['url'],
                                        description = page['bodytext'],
                                        guid = domain + page['url'],
                                        pubDate = page['created']
                                        )
                                    )
                                    feedcount -= 1
                            except:
                                pass

                        # Do this after listing so comments don't show on index pages
                        disqusGroupName = OPTIONS.get('disqusGroupName', False)
                        commentsString = ''
                        if disqusGroupName:
                            uniq_id = outline_url + node.created
                            commentsString = """
                            <script>var disqus_identifier = '%s';</script><a onclick="showHideComments ()"><span id="idShowHideComments" style="cursor: pointer;"></span></a><div class="divDisqusComments" id="idDisqusComments" style="visibility: visible;" ><div id="disqus_thread"></div></div><script type="text/javascript" src="http://disqus.com/forums/%s/embed.js"></script></div>
                            """ % (uniq_id, disqusGroupName)

                        page_data = re.sub('<!-- COMMENTS -->', commentsString, template)
                        page['data'] = page_data

                        if sub_folder:
                            posts[(sub_folder,index_title)].append(listing)
                        else:
                            posts["Home"].append(listing)
                        for path_info in [(year_path, year_title), (month_path, month_title), (day_path, day_title)]:
                            if not path_info[0]: continue
                            if path_info not in posts:
                                if sub_folder:
                                    path_info = path_info[0], path_info[1]
                                posts[path_info] = []
                            posts[path_info].append(listing)
                        if this_post_data:
                            file_name = getFileName("%s/%s" % (base_folder, this_path_name), FILENAMES)
                            FILENAMES.append(file_name)
                            save_file = False
                            new_data = re.sub('<nextprev>', getPrevNextLinks(prev_path_name, path_name), this_post_data)
                            if os.path.exists(file_name):
                                fh = open(file_name)
                                file_data = fh.read()[:-1]
                                fh.close()
                                save_file = (file_data != new_data)
                            else:
                                save_file = True
                            if save_file:
                                fh = open(file_name, "w+")
                                print >>fh, new_data.encode('utf-16')
                                fh.close()

            if not ycals:
                prev_post_data = this_post_data
                prev_path_name = this_path_name
                this_post_data = page_data
                this_path_name = path_name
                path_name = None
                if this_post_data:
                    file_name = getFileName("%s/%s" % (base_folder, this_path_name), FILENAMES)
                    FILENAMES.append(file_name)
                    save_file = False
                    new_data = re.sub('<nextprev>', getPrevNextLinks(prev_path_name, path_name), this_post_data)
                    if os.path.exists(file_name):
                        fh = open(file_name)
                        file_data = fh.read()[:-1]
                        fh.close()
                        save_file = (file_data != new_data)
                    else:
                        save_file = True
                    if save_file:
                        fh = open(file_name, "w+")
                        print >>fh, new_data
                        fh.close()

    # Generate Feed
    date_format = "%a, %d %b %Y %H:%M:%S %Z"
    feed_posts.sort(key=lambda x: datetime.datetime.strptime(x.pubDate, date_format), reverse=True)
    buildFeed(OPTIONS['rssTitle'], domain, page_desc, feed_posts, base_folder)

    # iterate over posts
    for path_info, these_posts in posts.items():
        count = OPTIONS.get('bloghomeItemCount',20)

        chunks=[these_posts[x:x+count] for x in xrange(0, len(these_posts), count)]
        for i,chunk in enumerate(chunks):
            try:
                pageDescription = chunks[0][0][-1]
            except:
                pageDescription = OPTIONS.get('pageDescription',' ')
            blogHomeDescription = OPTIONS.get('blogHomeDescription', pageDescription)
            if not i:
                page_name = "index"
            else:
                page_name = str(i+1)
            if path_info == "Home":
                brandLink = '/'
                page_title = blogHomeTitle
                page_desc = blogHomeDescription
                file_name = getFileName("%s/%s.html" % (base_folder, page_name), FILENAMES)
                FILENAMES.append(file_name)
            else:
                path, page_title = path_info
                brandLink = "/%s" % path.split('/')[0]
                page_desc = pageDescription
                file_name = getFileName("%s/%s/%s.html" % (base_folder, path, page_name), FILENAMES)
                FILENAMES.append(file_name)
            rules, template = TEMPLATES['bloghome']
            template = ''.join(template)

            # do the title and desc first to avoid overwriting with home title
            template = re.sub("<\%blogHomeTitle\%>", page_title, template)
            template = re.sub("<\%blogHomeDescription\%>", page_desc, template)
            template = re.sub("<\%pageTitle\%>", page_title, template)
            template = re.sub("<\%pageDescription\%>", page_desc, template)
            template = subData(template, GLOSSARY)

            template = re.sub('<%BRANDMENU%>', '<a class="brand" href="<%BRANDLINK%>"><%BRAND%></a>', template)
            template = re.sub('<%BRAND%>', page_title, template)
            template = re.sub('<%BRANDLINK%>', brandLink, template)

            bodytext = ''
            for title, page_data, page_url, page_desc in chunk:
                bodytext += "<h2><a href=\"%s\">%s</a></h2>\n%s\n" % (page_url, title, page_data)
            save_file = False
            new_data = re.sub('<%bodytext%>', bodytext, template)
            if os.path.exists(file_name):
                fh = open(file_name)
                file_data = fh.read()[:-1]
                fh.close()
                save_file = (file_data != new_data)
            else:
                save_file = True
            if save_file:
                fh = open(file_name, "w+")
                print >>fh, new_data.encode('utf-16')
                fh.close()
            fh.close()

    return base_folder

def render(url, folder, ura, zipit=False, upload=None, s3profile=None, s3bucket=None, index_file=None):
    if ura not in ["ABORT", "REPLACE", "UPDATE"]:
        raise Usage("second argument must be one of ABORT, REPLACE, or UPDATE")
    args = []
    if zipit: args.append("--zip")
    if folder: args.append("-f%s" % folder)
    if upload: args.append("-u%s" % upload)
    if s3profile: args.append("-p%s" % s3profile)
    if s3bucket: args.append("-b%s" % s3bucket)
    if index_file: args.append("-i%s" % index_file)
    args += [url, ura]
    main(args)


def renderFromConfigFile():
    config_settings = ConfigParser()
    config_settings.read("/etc/fargo2html.cfg")
    config_settings.read(os.path.join(os.environ["HOME"], ".fargo2htmlrc"))
    for section in config_settings.sections():
        print section
        outline_url = config_settings.get(section, "outline")
        try:
            folder = config_settings.get(section, "folder")
        except:
            folder = None
        try:
            zipIt = bool(config_settings.get(section, "zip"))
        except:
            zipIt = False
        try:
            upload = config_settings.get(section, "upload")
        except:
            upload = None
        try:
            s3profile = config_settings.get(section, "s3profile")
        except:
            s3profile = None
        try:
            s3bucket = config_settings.get(section, "s3bucket")
        except:
            s3bucket = None
        try:
            index_file = config_settings.get(section, "index_file")
        except:
            index_file = None
        render(outline_url, folder, "UPDATE", zipIt, upload, s3profile, s3bucket, index_file)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        try:
            opts, args = getopt.getopt(argv, "hczu:p:b:f:i:", ["help","cfg","zip","upload=", "s3profile=", "s3bucket=", "folder=", "index="])
        except getopt.error, msg:
            raise Usage(msg)
        zipIt = False
        s3, s3profile, s3bucket, folder, cfg = None, None, None, None, None
        home_index_page = None
        for option, value in opts:
            if option in ("-h", "--help"):
                print __doc__
                sys.exit()
            # if from config file, ignore everything else, bail from this function to
            # a function that will call it repeatedly
            if option in ("-c", "--cfg"):
                return renderFromConfigFile()
            if option in ("-z", "--zip"): zipIt = True
            if option in ("-u", "--upload"):
                if value == 's3': s3 = True
            if option in ("-p", "--s3profile"):
                s3 = True
                s3profile = value
            if option in ("-b", "--s3bucket"):
                s3 = True
                s3bucket = value
            if option in ("-f", "--folder"): folder = value
            if option in ("-i", "--index"): home_index_page = value


        try:
            o_url = args[0]
        except:
            raise Usage("URL to outline required as first argument")

        try:
            folder = folder or os.path.join(os.environ["HOME"], "fargo_outlines/%s" % o_url.split('/')[-1].split('.')[0])
        except:
            raise Usage("Error determining folder. Pass in with -f or --folder=")

        if os.path.exists(folder):
            try:
                URA = args[1]
            except Exception, e:
                print e
                URA = raw_input("""
Folder %s exists.
Just press enter to update.
Type REPLACE and press enter to delete it.
Type any other keys and press enter to quit.
""" % folder)
            if URA == 'REPLACE':
                shutil.rmtree(folder)
            elif URA not in ["", "UPDATE"]:
                sys.exit(1)

        folder_parsed = parse(o_url, folder, home_index_page)
        if zipIt: zipdir(folder_parsed)
        if s3:
            s3profile = s3profile or "Credentials"
            s3bucket = s3bucket or os.path.basename(folder)
            import folder2s3
            folder2s3.upload(folder, s3profile, s3bucket)
        return 0

    except Usage, err:
        error_message = sys.argv[0].split("/")[-1] + ": " + str(err.message)
        print >> sys.stderr, error_message
        print >> sys.stderr, "for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())




