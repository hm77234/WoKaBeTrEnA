# Simple multilingual vocabletrainer

Easy Vocable- and Phrasetrainer for different languages. All translations except german are done by KI, so sorry for errors ;)

# First steps
* clone the repo
* set ENV MUTTERLANG to your mutter language, default is deutsch ("german"). Valid default MUTTERLANG are deutsch, espanol, english and italiano
* go to the admin page and reset pairs, this will build your langugage pairs
* import your first csv into the trainer, examples are in "example" folder.
* optional: set ENV DEBUGLEVEL=debug or one of warning, error or info (default)
* run uv run uvicorn asgi:asgi_app --reload 

If you want to use it with podman (i expect docker also) check the install section.

# add a mutter language
 add a dictonary in translation.py with your values. the key has to be the new mutter language.

# add a foreign training language
  add a language in mutterlang to the list with key 'foreigns' in translations dict.
  Example Mutterlang German: 'foreigns': ['spanisch', 'englisch', 'italienisch', 'französisch' ],

# TLS
 Put your Certificates in a folder named certs. 

# License

 mit

# install

## slim

   follow

## distroless (experimentel)

Tested with mac/arm64. Check Dockerfile_distroless for amd options

* podman build --platform linux/arm64 -t trainer -f Dockerfile_distroless .        
* podman volume create trainer-data
* podman run -d \
  --name trainer \
  -p 8000:8000 \
  -v trainer-/app/instance \
  trainer