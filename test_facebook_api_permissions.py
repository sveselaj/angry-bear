import requests
import json

def test_facebook_api_permissions(page_id, post_id, access_token):
    # Test reading posts
    posts_url = f"https://graph.facebook.com/v13.0/{page_id}/posts?access_token={access_token}&fields=message,created_time,id"
    response = requests.get(posts_url)
    
    if response.status_code == 200:
        print("Permission to read posts: GRANTED")
        posts_data = json.loads(response.text)
        print("Post Message:", posts_data["data"][0]["message"])
    else:
        print("Permission to read posts: DENIED")
        print("Error:", response.text)

    # Test reading comments
    comments_url = f"https://graph.facebook.com/v13.0/{post_id}/comments?access_token={access_token}&fields=message,created_time,from"
    response = requests.get(comments_url)
    
    if response.status_code == 200:
        print("Permission to read comments: GRANTED")
        comments_data = json.loads(response.text)
        print("Comment Message:", comments_data["data"][0]["message"])
    else:
        print("Permission to read comments: DENIED")
        print("Error:", response.text)

FACEBOOK_PAGE_ACCESS_TOKEN="EAAVErAWeohwBPS6YTyzUmc7q1Ikw966DueOUi4CvhGnWC99ZAHw0dfv3uutKRZCZBkh442s0tkq9jjaPjXHhKhxqXgFFrkNG5dGQ0tq7byc8NO7OgEaFcZAbwnzOYQYpQm4sYL3oDZAtcn5IZB6l5GhPauavEJoGenCjMHLs7ur9EZAMF1G6iXsMsUik57dnf9ukQeWhkq0ZB9yNSlZC2JGmMKwZDZD"
FACEBOOK_PAGE_ID="659879557212706"

# Replace with your page ID, post ID, and access token
page_id = FACEBOOK_PAGE_ID
post_id = "659879557212706_122118078680924024"
access_token = FACEBOOK_PAGE_ACCESS_TOKEN
test_facebook_api_permissions(page_id, post_id, access_token)

#posts_url = f"https://graph.facebook.com/v13.0/{page_id}/posts?access_token={access_token}&fields=id,message"
#response = requests.get(posts_url)
#posts_data = json.loads(response.text)
#print(posts_data)
#for post in posts_data["data"]:
    #post_id = post["id"]
    #test_facebook_api_permissions(page_id, post_id, access_token)
    #print(f"Post ID: {post['id']}")
    #print(f"Post Message: {post['message']}")



