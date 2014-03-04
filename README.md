Fargo 2 xhtml
==============

Accepts a URL to a Fargo outline as first argument and will render it to html files.

This is software that was developed for my own use and requires settings in
your Fargo outline. It will almost certainly not work for you out of the box.

I did have an online form for testing this out, but it is down for now. I am
working on putting it back in place and will try to add documentation then.

See http://www.bsoi.st/fargoToXhtml for more information.

Usage:
-----
    import fargo2html

Then call one of two functions.

renderFromConfigFile()
----------------------
This will render all outlines according to you config file. The options are the
same as for command line or for calling render.

Two locations will be checked for config files:

    /etc/fargo2html.cfg
    ~/.fargo2htmrc

An example would look like this.


    [foo]
    outline = https://dl.dropbox.com/s/rand/foobar.opml
    folder = /home/bill/data/foo.bar
    upload = s3
    s3profile = foo
    s3bucket = www.foo.bar
    zip = True


render()
--------
Then call fargo2html.upload() with at least three arguments.
    
    my_outline = http://dl.dropbox.com/s/ran/myoutline.opml
    my_folder = /home/bill/foobar
    fargo2html.render(my_outline, my_folder, "UPDATE")

will render the outline http://dl.dropbox.com/s/ran/myoutline.opml to the
folder /home/bill/foobar and will update existing files. Use "REPLACE" to
delete /home/bill/foobar before saving files ( thereby creating all new files
) or "ABORT" to quit if the folder you pass in exists.

To create a ZIP of the folder, pass in a fourth argument.

    fargo2html.render(my_outline, my_folder, "UPDATE", True)

To upload to S3 ...

    fargo2html.render(my_outline, my_folder, "UPDATE", False, s3)

This will upload to a bucket named folder for the default s3 profile. NOTE: Requires folder2s3.py and boto and a valid boto config file. See the readme for folder2s3.py for more info.

To specify a profile and/or bucket use ...
    
    fargo2html.render(my_outline, my_folder, "UPDATE", False, s3, bill, www.foo.bar)

This will upload to a bucket named www.foo.bar for profile bill.


Command Line Examples:
---------------------
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


