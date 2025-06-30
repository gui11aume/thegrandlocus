"""
Run
```bash
    gcloud auth application-default login
```

"""

import argparse
from google.cloud import datastore
from models.blog_post import BlogPost


def save_post_to_firestore(client, post):
    """Saves a BlogPost object to the new Firestore database."""
    entity = datastore.Entity(
        client.key("BlogPost", post.key.id_or_name),
        exclude_from_indexes=["body"],
    )
    entity.update(
        {
            "title": post.title,
            "body": post.body,
            "published": post.published,
            "updated": post.updated,
            "path": post.path,
            "tags": post.tags,
        }
    )
    client.put(entity)


def main():
    parser = argparse.ArgumentParser(description="Migrate blog posts to Firestore.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch posts without writing to the new database.",
    )
    parser.add_argument(
        "--project",
        type=str,
        default="thegrandlocus-new",
        help="The project ID of the new Firestore database.",
    )
    args = parser.parse_args()

    # Client for the old Datastore
    old_client = datastore.Client(project="thegrandlocus")

    # Client for the new Firestore in Datastore mode
    new_client = datastore.Client(project=args.project)

    query = old_client.query(kind="BlogPost")
    posts = [BlogPost.from_datastore_entity(entity) for entity in query.fetch()]

    print(f"Found {len(posts)} posts in the old Datastore.")

    if args.dry_run:
        print("Dry run requested. Posts will not be migrated.")
        for post in posts:
            print(post)
    else:
        print(f"Migrating {len(posts)} posts to project '{args.project}'...")
        for post in posts:
            save_post_to_firestore(new_client, post)
        print("Migration complete.")


if __name__ == "__main__":
    main()
