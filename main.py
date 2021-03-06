import datetime
import time
from pprint import pprint

import twitter

import config


api = twitter.Api(
    consumer_key=config.TWITTER_CONSUMER_KEY,
    consumer_secret=config.TWITTER_CONSUMER_SECRET,
    access_token_key=config.TWITTER_ACCESS_TOKEN_KEY,
    access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET,
)


def get_last_round_newest_follower_id():
    try:
        with open(config.BTZ_LAST_ROUND_NEWEST_FOLLOWER_ID_FILENAME, 'r') as f:
            return int(f.read())
    except Exception as e:
        print(e)
        return None


def save_newest_follower_id(newest_follower_id):
    with open(config.BTZ_LAST_ROUND_NEWEST_FOLLOWER_ID_FILENAME, 'w') as f:
        f.write(str(newest_follower_id))


def log_blocked_user(blocked_user):
    with open(config.BTZ_BLOCKED_USERS_LOG_FILENAME, 'a') as f:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{now}] @{blocked_user.screen_name} {blocked_user.id}\n")

def is_default_twitter_profile_image(url):
    if "abs.twimg.com/sticky/default_profile_images" in url:
        return True
    return False


def is_zombie(follower):
    if is_default_twitter_profile_image(follower.profile_image_url):
        if (
            follower.statuses_count <= config.BTZ_DEFAULT_PROFILE_IMAGE_ZOMBIE_STATUSES_COUNT_THRESHOLD
            or
            follower.favourites_count <= config.BTZ_DEFAULT_PROFILE_IMAGE_ZOMBIE_FAVOURITES_COUNT_THRESHOLD
        ):
            return True
    else:
        if (
            follower.statuses_count <= config.BTZ_NON_DEFAULT_PROFILE_IMAGE_ZOMBIE_STATUSES_COUNT_THRESHOLD
            and
            follower.followers_count <= config.BTZ_NON_DEFAULT_PROFILE_IMAGE_ZOMBIE_FOLLOWERS_COUNT_THRESHOLD
        ):
           return True

    return False


def is_created_lately(follower):
    lately = datetime.timedelta(days=config.BTZ_CREATED_LATELY_DEFINITION_IN_DAYS)
    # "Mon Apr 16 10:05:35 +0000 2018"
    created_time = datetime.datetime.strptime(follower.created_at, "%a %b %d %H:%M:%S %z %Y")
    if datetime.datetime.now(datetime.timezone.utc) - created_time <= lately:
        return True
    return False


def block_if_zombie(follower):
    if is_created_lately(follower) and is_zombie(follower):
        try:
            api.CreateBlock(
                user_id=follower.id,
                include_entities=False,
                skip_status=True,
            )
        except Exception as e:
            print(e)
            print(f"Failed to blocked user: @{blocked_user.screen_name}")
        else:
            log_blocked_user(follower)
            print(f"Blocked user: @{follower.screen_name}")


def main():
    newest_follower_id = get_last_round_newest_follower_id()

    next_cursor = None
    first_round = True
    break_at_newest_follower = False
    while True:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\nRun at: {now}")
        print(f"newest_follower_id: {newest_follower_id}")
        try:
            next_cursor, previous_cursor, followers = api.GetFollowersPaged(
                cursor=next_cursor,
                skip_status=True,
                include_user_entities=False,
            )

        except twitter.error.TwitterError as e:
            print(e)

        except KeyboardInterrupt:
            return

        else:
            print(f"next_cursor: {next_cursor}")
            print(f"previous_cursor: {previous_cursor}")

            for follower in followers:
                if follower.id == newest_follower_id:
                    print(f"Break at newest_follower_id: {newest_follower_id}, @{follower.screen_name}")
                    break_at_newest_follower = True
                    break

                if first_round:
                    newest_follower_id = follower.id
                    first_round = False

                # pprint(follower._json)
                block_if_zombie(follower)

        finally:
            if newest_follower_id is not None:
                save_newest_follower_id(newest_follower_id)

        if break_at_newest_follower or next_cursor == 0:
            time.sleep(config.BTZ_CHECK_INTERVAL_SECONDS)
            next_cursor = None
            first_round = True
            break_at_newest_follower = False

if __name__ == "__main__":
    main()
