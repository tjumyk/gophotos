<img align="right" src="gophotos/static/image/logo-64.png"/>

# Go Photos

## Introduction

This is a tiny web server that integrates Google Client API and [又拍云(UpYun, a Chinese cloud storage provider)](https://www.upyun.com) API to automatically 
copy the selected albums from your Google Photos to UpYun and generate a share link.

As we all know, mainland China has blocked most of the Google services. The purpose of this project is to share the Google Photos albums with
parents or friends in mainland China with just one click.

## Configuration

1. Register a new project and OAuth 2.0 Client ID in [Google Developer Console](https://console.developers.google.com)
2. Download the OAuth 2.0 Client ID configuration file (in JSON format), rename it as `google_client.json` and put it in the `secrets` folder. You may also 
copy `google_client.json.example` to `google_client.json` and edit the contents directly.
3. Register a cloud storage in [Upyun](https://www.upyun.com)
4. Also in `secrets` folder, copy `upyun.json.example` to `upyun.json` and edit the contents according to your registration  

## License

[The MIT License (MIT)](LICENSE.md)
