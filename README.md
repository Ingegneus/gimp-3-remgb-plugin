this plugin integrates the `rembg` python package into gimp 3. it removes the background of an image using AI. it provides many different models for different needs.

to install the plugin you need to download the `rembg.py` file and place it in your gimp plugin folder

then install rembg with `pip install rembg[cli]` oder `pip install rembg[cpu,cli]` if you only want to use the cpu. it requires python >=3.10, <3.14

when running a model for the first time, it will download it. that might take some time (bria-rmbg ~1GB)

for a detailed documentation see [this](https://deepwiki.com/danielgatis/rembg/1-overview)

a description of the differet models is given [here](https://deepwiki.com/danielgatis/rembg/5-models)