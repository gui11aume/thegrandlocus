# Install gcloud
See details in the [documentation](https://cloud.google.com/sdk/docs/install#deb).

```
sudo apt-get install apt-transport-https ca-certificates gnupg curl sudo
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-cli
```

Once this is done, initialize `gcloud`.

```
gcloud init
gcloud auth login
```

You may have to set the current project.

```
gcloud config set project thegrandlocus
```

# Install virtual environment
First create a virtual environment with `venv` and activate it.

```
/usr/bin/python3 -m venv venv
source venv/bin/activate
```

Then install the requirements with `pip`.

```
pip install -r requirements.txt
```

# Deploy
Use `gcloud` to deploy the app (billing must be enabled).

```
gcloud app deploy --quiet
```

You can monitor the versions of the app on the [console](https://console.cloud.google.com/appengine/versions?project=thegrandlocus&serviceId=default).


### Acknowledgements
I forked `bloggart` for The Grand Locus.
Here is the original README of bloggart.

Bloggart is a blog application for Google App Engine. It's currently being
developed as a demonstration app for [a series of blog
posts](http://blog.notdot.net/2009/10/Writing-a-blog-system-on-App-Engine) but
is intended to be a useful and versatile blogging system for App Engine by the
time it's done.

![The original picture for bloggart](http://github.com/Arachnid/bloggart/raw/master/themes/default/static/images/bloggart-ae.png)

