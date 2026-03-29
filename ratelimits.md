# Rate Limits (Karokit adapted from Twikit)

**Reference note:** This table is migrated from Twikit and adapted for Karokit naming. Actual Karotter limits can differ.

| Functions                             | Limit | Endpoint                            |
| --------------------------------------- |-------|-------------------------------------|
| add_members_to_group                  | -     | AddParticipantsMutation             |
| block_user                            | 187   | blocks/create.json                  |
| get_user_verified_followers           | 500   | BlueVerifiedFollowers               |
| get_bookmarks                         | 500   | Bookmarks                           |
| delete_all_bookmarks                  | -     | BookmarksAllDelete                  |
| change_group_name                     | 900   | {GroupID}/update_name.json          |
| get_group_dm_history, get_dm_history  | 900   | conversation/{ConversationID}.json  |
| bookmark_karot                        | -     | CreateBookmark                      |
| create_poll                           | -     | cards/create.json                   |
| follow_user                           | 15    | friendships/create.json             |
| create_list                           | -     | CreateList                          |
| rekarot                               | -     | CreateRetweet                       |
| create_scheduled_karot                | -     | CreateScheduledTweet                |
| create_karot                          | -     | CreateTweet                         |
| delete_bookmark                       | -     | DeleteBookmark                      |
| delete_dm                             | -     | DMMessageDeleteMutation             |
| delete_list_banner                    | -     | DeleteListBanner                    |
| delete_rekarot                        | -     | DeleteRetweet                       |
| delete_scheduled_karot                | -     | DeleteScheduledTweet                |
| delete_karot                          | -     | DeleteTweet                         |
| unfollow_user                         | 187   | friendships/destroy.json            |
| edit_list_banner                      | -     | EditListBanner                      |
| get_favoriters                        | 500   | Favoriters                          |
| like_karot                            | -     | FavoriteTweet                       |
| get_scheduled_tweets                  | 500   | FetchScheduledTweets                |
| get_user_followers                    | 50    | Followers                           |
| get_user_followers_you_know           | 500   | FollowersYouKnow                    |
| get_user_following                    | 500   | Following                           |
| get_guest_token                       | -     | guest/activate.json                 |
| get_latest_timeline                   | 500   | HomeLatestTimeline                  |
| get_timeline                          | 500   | HomeTimeline                        |
| -                                     | 450   | dm/inbox_initial_state.json         |
| add_list_member                       | -     | ListAddMember                       |
| get_list                              | 500   | ListByRestId                        |
| get_list_tweets                       | 500   | ListLatestTweetsTimeline            |
| get_lists                             | 500   | ListsManagementPageTimeline         |
| get_list_members                      | 500   | ListMembers                         |
| remove_list_member                    | -     | ListRemoveMember                    |
| get_list_subscribers                  | 500   | ListSubscribers                     |
| logout                                | 187   | account/logout.json                 |
| add_reaction_to_message               | -     | /useDMReactionMutationAddMutation   |
| remove_reaction_from_message          | -     | useDMReactionMutationRemoveMutation |
| -                                     | -     | MuteList                            |
| mute_user                             | 187   | mutes/users/create.json             |
| get_notifications[type="All"]         | 180   | notifications/all.json              |
| get_notifications[type="Mentions"]    | 180   | notifications/mentions.json         |
| get_notifications[type="Verified"]    | 180   | notifications/verified.json         |
| get_rekaroters                        | 500   | Retweeters                          |
| search_karot, search_user             | 50    | SearchTimeline                      |
| send_dm                               | 187   | dm/new2.json                        |
| user_id                               | -     | account/settings.json               |
| get_user_subscriptions                | 500   | UserCreatorSubscriptions            |
| login                                 | 187   | onboarding/task.json                |
| get_trends                            | 20000 | guide.json                          |
| get_karot_by_id                       | 150   | TweetDetail                         |
| unblock_user                          | 187   | blocks/destroy.json                 |
| unlike_karot                          | -     | UnfavoriteTweet                     |
| -                                     | -     | UnmuteList                          |
| unmute_user                           | 187   | mutes/users/destroy.json            |
| edit_list                             | -     | UpdateList                          |
| upload_media                          | -     | media/upload.json                   |
| get_user_by_id                        | 500   | UserByRestId                        |
| get_user_by_screen_name               | 95    | UserByScreenName                    |
| get_user_karots[karot_type="Likes"]   | 500   | Likes                               |
| get_user_karots[karot_type="Media"]   | 500   | UserMedia                           |
| get_user_karots[karot_type="Tweets"]  | 50    | UserTweets                          |
| get_user_karots[karot_type="Replies"] | 50    | UserTweetsAndReplies                |
| vote                                  | -     | capi/passthrough/1                  |


