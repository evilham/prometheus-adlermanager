MAIN  = src/Main.elm
OUTJS = bundle.js

ELM      = elm
ELM_LIVE = elm-live
ELMFLAGS =

.PHONY: default help clean clean-gitignore live

default: help

# -- END-USER RELEVANT -- #

build: $(OUTJS)  ## Compiles the app.

# -- DEV TARGETS -- #

live:  ## Runs an elm-live server for development.
	$(ELM_LIVE) $(MAIN) -- $(ELMFLAGS)

# -- THE TARGETS THAT ACTUALLY DO STUFF -- #

$(OUTJS): $(shell find src)
	$(ELM) make $(ELMFLAGS) $(MAIN) --output $(OUTJS)

# -- HELPERS -- #

help:  # stolen from marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

clean:  ## Cleans generated files
	rm -rf elm-stuff/build-artifacts/
	rm -f $(OUTJS)

clean-all: clean-gitignore  ## Cleans everything, including downloaded dependencies
	rm -rf $$(cat ./.gitignore | grep -v '^#')
