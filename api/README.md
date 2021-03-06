Enermaps HTTP api.

This directory host the api for the enermaps project.

# Running locally

For running the api locally, the current recommended method
is to use docker-compose (see the README at the root of the directory).

You can still run the api locally for developpement purpose. You will need

* python 3.6+
* pip
* mapnik version above 3.0

You can optionally create a virtual environment prior to running the install commands for installing the environment.

Then proceed to install the requirement with:

```
pip install -r requirements.txt
```

You should then be able to run main.py for running the webserver locally or test.py for running all tests using on unix platform:

```
python $(pwd)/main.py
```
The api will listen http://127.0.0.1:7000 after a short initialisation period.

# acceptance test

Currently, the wms_test/acceptance_test.py is testing for the initialisation of the wms library.
The script can be ran as a python script. It need the enermaps project to already be started and be reachable
under the url URL.

You can then call the script with:

```sh
python wms_test/acceptance_test.py --url URL
```

You can also test for a specific wms version with

```sh
python wms_test/acceptance_test.py --url URL --version 1.3.0
```

# Integration test

## Run

By default, running test.py will only select test that are not marked with
a label. You can select a testsuite by label by adding the label of that test suite
after the test.py script.

We have a small integration testsuite, that can be run with.


```sh
docker-compose up --build
docker-compose exec -T api ./test.py integration
```

The integration test will only be updated when the docker image for the api is rebuilt.
You can rebuild the image and run the integration test using the following commands after the stack is up:

```sh
docker-compose up --build -d api
docker-compose exec -T api ./test.py integration
```

## Add an integration test
Integration test can be added by making a subclass of the class BaseIntegrationTest in app/common/test.py you can use self.api_url as the base url for the api.
