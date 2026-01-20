import requests
import json

candidate_videos = [
    # Diabetes
    {'id': 'wZAjVQWbMlE', 'title': 'What is Diabetes? (CDC)'},
    {'id': 'JAjJoFj5-DA', 'title': 'Reverse Type 2 Diabetes Naturally'},
    {'id': 'X9ivR4y03DE', 'title': 'Understanding Diabetes (Animation)'},
    {'id': 'sV2dtA74Yx0', 'title': 'What is Type 2 Diabetes? (Diabetes UK)'},
    {'id': '_3q2e5e11193b', 'title': 'Invalid Test ID'}, # Test fail

    # Hypertension
    {'id': 'diG519dFVNs', 'title': 'High Blood Pressure (British Heart Foundation)'},
    {'id': 'S6fK0aQ1111', 'title': 'Invalid Test 2'},
    {'id': 'V0_dUVK0EJE', 'title': 'Managing High Blood Pressure (CDC)'},
    {'id': '9hR71q8F111', 'title': 'Invalid Test 3'},

    # Heart Health
    {'id': 'Cwf_1K21111', 'title': 'Invalid Test 4'},
    {'id': 'GMKroVqU111', 'title': 'Invalid Test 5'},
    
    # TED-Ed / Reliable
    {'id': 'WuyPuH9ojCE', 'title': 'How stress affects your brain'},
    {'id': 'gedoSfZvBgE', 'title': 'Benefits of good sleep'},
    {'id': 'z-IR48Mb3W0', 'title': 'What is depression?'},
    {'id': 'PSRJfaAYkW4', 'title': 'How your immune system works'},
    {'id': 'OyK0oE5rwFY', 'title': 'Benefits of good posture'},
    {'id': 'lEXBxijQREo', 'title': 'Sugar and the brain'},
    {'id': 'wUEl8KrMz14', 'title': 'Why sitting is bad'},
    {'id': 'Bw9zIThGWtc', 'title': 'How the body heals'},
    {'id': '50lFZHOyPzI', 'title': 'How the heart pumps blood'},
    {'id': 'X9ivR4y03DE', 'title': 'Diabetes Animation'},
    {'id': 'jL881bFqg5Q', 'title': 'What is Heart Failure? (AHA)'},
    {'id': 'H04d3rJCLCE', 'title': 'How the Heart Works (Mayo Clinic)'},
    {'id': '4b8oB757DKc', 'title': 'Understanding Heart Attack (BHF)'},
    {'id': 'f98GE_5r1Ag', 'title': 'Hypertension (Osmosis)'}
]

print("Verifying videos using YouTube oEmbed API...")
valid_videos = []

for vid in candidate_videos:
    vid_id = vid['id']
    url = f"https://www.youtube.com/watch?v={vid_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    
    try:
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ [VALID] {vid_id}: {vid['title']}")
            valid_videos.append(vid)
        else:
            print(f"❌ [INVALID/UNAVAILABLE] {vid_id}: {vid['title']} (Status: {response.status_code})")
    except Exception as e:
        print(f"⚠️ [ERROR] {vid_id}: {str(e)}")

print(f"\nTotal Valid Videos: {len(valid_videos)}")
print("Copying valid list for use...")
print(json.dumps(valid_videos, indent=4))
