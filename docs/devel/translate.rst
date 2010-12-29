====================
Translating MoinMoin
====================

.. todo::

   document how to add a new translation
   how to fix existing translations

If your language already exists
-------------------------------

Currently, there is a translation available for *German*, so if you
want to work on this, you can follow these steps.

1. Make sure you have the latest version of the source tree (hg)
   and you are able to "make" it.

2. Go to the top directory and execute
   ::
     ./babel update <locale>
   
   where locale is the short language descriptor of your desired
   language. It should be the name of a folder in MoinMoin/translations.
   For German it is "de".

3. Open the file MoinMoin/translations/<locale>/LC_MESSAGES/messages.po
   and do your translation. A short explanation of this process follows:
   
   * find an entry, with an empty or bad translated text (the text after
     msgstr) and do your changes.
   
   * **never** edit the msgid string, just edit the msgstr field
   
   * Variables like %(name)x (x can be any character) must be kept as
     they are. They must occur in the translated text.
   
   * For better readability you can divide a text-string over more than
     one lines, by "surrounding" each line with double quotes (").
     It is a usual convention to have a maximal line-length of 80
     characters.
   
   * Comments starting with "*#.*", "*#:*", "*#,*" or "*#|*" are
     auto-generated and should not be modified.
   
   * Comments starting with "# " (# and at least one whitespace) are
     translator-comments. You can modify/add them. They have to be 
     placed right before the auto-generated comments.

4. Save the messages.po file and execute
   ::
     ./babel compile
   
If your language doesn't exist yet
----------------------------------

You want to translate moin2 to your language? Great! Get in contact with
the developers, but ...

.. note::

  please don't ask us whether we want other translations, we
  currently do not want them, it is still too early. We just want
  1 translation and it needs to be German because that is what many
  moin developers can maintain themselves.

1. Run babel:
   ::
     ./babel init <locale>
   
2. Adjust the *MoinMoin/translations/<locale>/LC_MESSAGES/messages.po* .

   Especially edit the header (comment and first msgstr section), 
   replace the placeholders (written in CAPITAL letters) and then you
   can remove the fuzzy flag, which prevents the file from being compiled.

3. Follow the steps above (`If your language already exists`_).
