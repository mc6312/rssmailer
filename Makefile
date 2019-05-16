pack = 7z a -mx=9
docs = COPYING README LICENSE README.md
arcname = rssmailer
arcx = .7z
configdir = ~/.rssmailer
xchgdir = ~/shareddocs/pgm/python/
srcarcname = $(arcname)-src
feeddir = $(configdir)/feeds
pyz=$(arcname).pyz
pyztmp = $(arcname).zip
version = $(shell python3 -c 'from rssmailer import RELEASE; print(RELEASE)')

src-archive:
	$(pack) $(srcarcname)$(arcx) *.py *.sh *. Makefile $(docs) subscriptions* backup-me *.geany
zip:
	$(pack) -tzip $(pyztmp) *.py
	@echo '#!/usr/bin/env python3' >$(pyz)
	cat $(pyztmp) >>$(pyz)
	rm $(pyztmp)
archive:
	make zip
	$(pack) $(arcname)$(arcx) $(pyz) $(docs)
backup:
	make src-archive
	mv $(srcarcname)$(arcx) $(xchgdir)
update:
	7z x -y $(xchgdir)$(srcarcname)$(arcx)
install:
	make zip
	./install.sh $(pyz)
	rm $(pyz)
commit:
	git commit -a -uno -m "$(version)"
settings-archive:
	$(pack) -r $(arcname)-settings$(arcx) $(configdir)
reset-feeds:
	rm $(feeddir)/*
clean:
	rm *$(arcx) $(pyz)
