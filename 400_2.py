import twitter
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from functools import partial
from sys import maxint

#Joy White CIS 400 Assignment 2

def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print >> sys.stderr, 'Too many retries. Quitting.'
            raise e
    
        # See https://dev.twitter.com/docs/error-codes-responses for common codes
    
        if e.e.code == 401:
            print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
            return None
        elif e.e.code == 404:
            print >> sys.stderr, 'Encountered 404 Error (Not Found)'
            return None
        elif e.e.code == 429: 
            print >> sys.stderr, 'Encountered 429 Error (Rate Limit Exceeded)'
            if sleep_when_rate_limited:
                print >> sys.stderr, "Retrying in 15 minutes...ZzZ..."
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print >> sys.stderr, '...ZzZ...Awake now and trying again.'
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print >> sys.stderr, 'Encountered %i Error. Retrying in %i seconds' %                 (e.e.code, wait_period)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError, e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError, e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print >> sys.stderr, "URLError encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise
        except BadStatusLine, e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print >> sys.stderr, "BadStatusLine encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise

def get_user_profile(twitter_api, screen_names=None, user_ids=None):
   
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
    
    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:

        # Process 100 items at a time per the API specifications for /users/lookup.
        # See https://dev.twitter.com/docs/api/1.1/get/users/lookup for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"
    
    # See https://dev.twitter.com/docs/api/1.1/get/friends/ids and
    # https://dev.twitter.com/docs/api/1.1/get/followers/ids for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            print >> sys.stderr, 'Fetched {0} total {1} ids for {2}'.format(len(ids), 
                                                    label, (user_id or screen_name))
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

def oauth_login():
     CONSUMER_KEY = 'EaXbdLE20WPOVm3wpgu7S8J9s'
     CONSUMER_SECRET = 'xi0W19XbZdmV9dQHYwpn6MTIScNqSivhzE85lLy2g0NkEBxEWk'
     OAUTH_TOKEN = '837702453080502274-AqqoLrWqlULITQ6FuwurHeAJIRfaGFe'
     OAUTH_TOKEN_SECRET = 'il2Kp55wSGacaOh4YP88Z0iNpLxwQGaoXwHbuGQ280SWv'
     
     auth = twitter.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
             CONSUMER_KEY, CONSUMER_SECRET)
     twitter_api = twitter.Twitter(auth=auth)
     return twitter_api
    
twitter_api = oauth_login()

friends_ids, followers_ids = get_friends_followers_ids(twitter_api, 
                                                       screen_name="sammmhowardd",
                                                       friends_limit=30, 
                                                       followers_limit=30)
print "30 Friends IDs"
print friends_ids
print "30 Followers IDs"
print followers_ids

reciprocal_friends = set(friends_ids) & set(followers_ids)
reciprocal_friends = list(reciprocal_friends)
print "Reciprocal Friends"
print reciprocal_friends


rep_length = len(reciprocal_friends)
follow_count = {}
i = 0

#gets reciprocal friends userIDs and follower counts
while (i<= (rep_length-1)):
    rep_id = reciprocal_friends[i]
    rep_dict = get_user_profile(twitter_api, user_ids=[rep_id])
    rep_dict = rep_dict.get(rep_id)
    rep_follower_count = rep_dict.get('followers_count')
    follow_count[rep_id] = rep_follower_count
    i = i+1
print "Reciprocal Friends and Follower Count"
print follow_count

follow_count_length = len(follow_count)
i=0
top5 = []
#gets reciprocal friends with the five largest follower counts
while (i < 5):
       max_val = max(follow_count, key=follow_count.get)
       top5.append(max_val)
       del follow_count[max_val]
       i=i+1
print "Most Popular of Reciprocal Friends Anaylzed"
print top5

ids=next_queue= reciprocal_friends
level = 1
max_level = 3
i=0
while level < max_level:
    level+=1
    (queue, next_queue) = (next_queue, [])
    for id in queue:
        get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
        get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)
        reciprocal_friends = set(friends_ids) & set(followers_ids)
        reciprocal_friends = list(reciprocal_friends)
        next_queue+=reciprocal_friends
    ids+=next_queue
print "The IDs of the distance-1 friends, then distance-2 friends, etc."
print ids
          


    



