"""Smoke test. Run once after any credential change."""

from integrations.meta_client import MetaClient, MetaError

def main() -> None:
    client = MetaClient()
    try:
        acct = client.get_ig_account()
        print(f"IG: @{acct['username']}  "
              f"followers={acct['followers_count']}  media={acct['media_count']}")

        media = client.get_ig_media(limit=3)
        print(f"Fetched {len(media)} recent posts")

        if media:
            insights = client.get_media_insights(media[0]["id"])
            print(f"Latest post insights: {insights}")
    except MetaError as exc:
        print(f"FAILED — code {exc.code}: {exc.message}")
        return

    print(f"OK. Calls used: {client.calls_used}/50")

if __name__ == "__main__":
    main()