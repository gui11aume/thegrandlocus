from google.cloud import datastore


def get_datastore_client():
    return datastore.Client()
