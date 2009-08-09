#
# Makefile for MoinMoin
#

# location for the wikiconfig.py we use for testing:
export PYTHONPATH=$(PWD)

share := ./wiki

all:
	python setup.py build

install-docs:
	-mkdir build
	wget -U MoinMoin/Makefile -O build/INSTALL.html "http://master19.moinmo.in/InstallDocs?action=print"
	sed \
		-e 's#href="/#href="http://master19.moinmo.in/#g' \
		-e 's#http://master19.moinmo.in/moin_static.../#../MoinMoin/web/static/htdocs/#g' \
		-e 's#http://static.moinmo.in/moin_static.../#../MoinMoin/web/static/htdocs/#g' \
        build/INSTALL.html >docs/INSTALL.html
	-rm build/INSTALL.html

	wget -U MoinMoin/Makefile -O build/UPDATE.html "http://master19.moinmo.in/HelpOnUpdating?action=print"
	sed \
		-e 's#href="/#href="http://master19.moinmo.in/#g' \
		-e 's#http://master19.moinmo.in/moin_static.../#../MoinMoin/web/static/htdocs/#g' \
		-e 's#http://static.moinmo.in/moin_static.../#../MoinMoin/web/static/htdocs/#g' \
        build/UPDATE.html >docs/UPDATE.html
	-rm build/UPDATE.html
	-rmdir build

interwiki:
	wget -U MoinMoin/Makefile -O $(share)/data/intermap.txt "http://master19.moinmo.in/InterWikiMap?action=raw"
	chmod 664 $(share)/data/intermap.txt

check-tabs:
	@python -c 'import tabnanny ; tabnanny.check("MoinMoin")'

# Create documentation
epydoc: patchlevel
	@epydoc -o ../html-1.9 --name=MoinMoin --url=http://moinmo.in/ --graph=all --graph-font=Arial MoinMoin

pagepacks:
	@python MoinMoin/_tests/maketestwiki.py
	@MoinMoin/script/moin.py --config-dir=MoinMoin/_tests --wiki-url=http://localhost/ maint mkpagepacks
	
dist: clean-testwiki clean-devwiki
	-rm MANIFEST
	python setup.py sdist

# Create patchlevel module
patchlevel:
	@echo -e patchlevel = "\"`hg identify`\"\n" >MoinMoin/patchlevel.py
	@MoinMoin/version.py update

# Report translations status
check-i18n:
	MoinMoin/i18n/tools/check_i18n.py

# Update the workdir from the default pull repo
update:
	hg pull -u
	$(MAKE) patchlevel

test:
	@echo Testing is now done using \`py.test\`. py.test can be installed by downloading from http://codespeak.net/py/dist/download.html
	@echo Writing tests is explained on http://codespeak.net/py/dist/test.html

coverage:
	@python MoinMoin/_tests/maketestwiki.py
	@python -u -m trace --count --coverdir=cover --missing tests/runtests.py

pylint:
	@pylint --disable-msg=W0142,W0511,W0612,W0613,C0103,C0111,C0302,C0321,C0322 --disable-msg-cat=R MoinMoin

clean: clean-testwiki clean-pyc
	rm -rf build

clean-devwiki:
	-rm -rf wiki/data/cache/__session__
	-rm -rf wiki/data/cache/jinja
	-rm -rf wiki/data/cache/wikiconfig
	-rm -rf wiki/data/content
	-rm -rf wiki/data/userprofiles
	-rm -rf wiki/data/trash
	->wiki/data/event-log

clean-testwiki:
	-rm -rf MoinMoin/_tests/wiki/data/cache/*
	-rm MoinMoin/_tests/wiki/data/event-log

clean-pyc:
	find . -name "*.pyc" -exec rm -rf "{}" \; 

.PHONY: all dist install-docs check-tabs epydoc patchlevel \
	check-i18n update test testwiki clean \
	clean-testwiki clean-devwiki clean-pyc

