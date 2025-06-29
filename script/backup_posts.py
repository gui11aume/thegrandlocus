"""
Run from the root of the project.
You may need to authenticate first:
```bash
    gcloud auth application-default login
```
"""

import argparse
import datetime
import json
import os

from google.cloud import datastore
from models.blog_post import BlogPost


def main():
    parser = argparse.ArgumentParser(description="Backup blog posts from Datastore.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch posts without writing to a file.",
    )
    parser.add_argument(
        "--project",
        type=str,
        default="thegrandlocus",
        help="The project ID of the Datastore.",
    )
    args = parser.parse_args()

    client = datastore.Client(project=args.project)

    query = client.query(kind="BlogPost")
    posts_entities = list(query.fetch())
    posts = [BlogPost.from_datastore_entity(entity) for entity in posts_entities]

    print(f"Found {len(posts)} posts in Datastore for project '{args.project}'.")

    if args.dry_run:
        print("Dry run requested. Posts will not be saved.")
        return

    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    backup_filename = os.path.join(backup_dir, f"posts_backup_{timestamp}.json")

    posts_data = [post.to_dict() for post in posts]

    with open(backup_filename, "w", encoding="utf-8") as f:
        json.dump(posts_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully saved {len(posts)} posts to {backup_filename}")


if __name__ == "__main__":
    main() 