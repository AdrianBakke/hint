To my fellow countrymen out there who also live in the terminal

if you have an openai key, make sure you can reach it with `echo $OPENAI_API_KEY`

chmod the script and put it in /usr/local/lib, then symlink it to /usr/local/bin with the name `hint` or whatever you like

now you can talk with your terminal:
```bash
hint "what to have for dinner?"
```
