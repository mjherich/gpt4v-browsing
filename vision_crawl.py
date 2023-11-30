from openai import OpenAI
import subprocess
import base64
import json
import os

model = OpenAI()
model.timeout = 10

this_file = os.path.abspath(__file__)
tmp_dir = os.path.dirname(this_file) + "/tmp"
os.makedirs(tmp_dir, exist_ok=True)


def image_b64(image):
    with open(image, "rb") as f:
        return base64.b64encode(f.read()).decode()


company_name = input("Enter company name or domain: ")
prompt = f"To identify customers of {company_name}, let's look for company logos and testimonials on the homepage of {company_name}'s website."

messages = [
    {
        "role": "system",
        "content": 'You are a web crawler. Your job is to give the user a URL to go to in order to find the answer to the question. Go to a direct URL that will likely have the answer to the user\'s question. Respond in the following JSON format: {"url": "<put url here>"}',
    },
    {
        "role": "user",
        "content": prompt,
    },
]

while True:
    while True:
        response = model.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=1024,
            response_format={"type": "json_object"},
            seed=2232,
        )

        message = response.choices[0].message
        message_json = json.loads(message.content)
        url = message_json["url"]

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
            }
        )

        print(f"Crawling {url}")

        if os.path.exists("screenshot.jpg"):
            os.remove("screenshot.jpg")

        result = subprocess.run(
            ["node", "screenshot.js", url], capture_output=True, text=True
        )

        exitcode = result.returncode
        output = result.stdout

        if not os.path.exists("screenshot.jpg"):
            print("ERROR: Trying different URL")
            messages.append(
                {
                    "role": "user",
                    "content": "I was unable to crawl that site. Please pick a different one.",
                }
            )
        else:
            website_domain = url.split("//")[-1].split("/")[0]
            screenshot_path = os.path.join(tmp_dir, f"{website_domain}.jpg")
            os.rename("screenshot.jpg", screenshot_path)
            break

    b64_image = image_b64(screenshot_path)

    response = model.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "system",
                "content": f"Your job is to identify company logos and customer testimonials found on the screenshot of {url}. Answer the user as an assistant, but don't tell that the information is from a screenshot or an image. Pretend it is information that you know. If you can't answer the question, simply respond with the code `ANSWER_NOT_FOUND` and nothing else.",
            }
        ]
        + messages[1:]
        + [
            {
                "role": "user",
                "content": [
                    # Future Idea: compare images from databricks sheet to screenshot...
                    # # company logo from databricks sheet
                    # {
                    #     "type": "image_url",
                    #     "image_url": f"data:image/jpeg;base64,{b64_image}",
                    # },
                    # # Screenshot from website does the company logo match?
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{b64_image}",
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        max_tokens=1024,
    )

    message = response.choices[0].message
    message_text = message.content

    if "ANSWER_NOT_FOUND" in message_text:
        print("ERROR: Answer not found")
        messages.append(
            {
                "role": "user",
                "content": "I was unable to find the answer on that website. Please pick another one",
            }
        )
    else:
        print(f"GPT: {message_text}")
        prompt = input("\nYou: ")
        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )
