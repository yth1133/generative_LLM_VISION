import json
from urllib import request, parse
import random
import uuid
import websocket
import urllib
import os
from PIL import Image
import io


server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())


def open_websocket_connection():
    server_address = "127.0.0.1:8188"
    client_id = str(uuid.uuid4())  # 고유한 클라이언트 ID 생성
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")  # 서버에 웹소켓 연결
    return ws, server_address, client_id


def queue_prompt(prompt, client_id, server_address):
    p = {"prompt": prompt, "client_id": client_id}
    headers = {"Content-Type": "application/json"}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request(
        "http://{}/prompt".format(server_address), data=data, headers=headers
    )
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id, server_address):
    with urllib.request.urlopen(
        "http://{}/history/{}".format(server_address, prompt_id)
    ) as response:
        return json.loads(response.read())


def get_image(filename, subfolder, folder_type, server_address):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)

    with urllib.request.urlopen(
        "http://{}/view?{}".format(server_address, url_values)
    ) as response:
        return response.read()

def load_workflow(workflow_path):
    try:
        with open(workflow_path, "r") as file:
            workflow = json.load(file)
            return json.dumps(workflow)
    except FileNotFoundError:
        print(f"The file {workflow_path} was not found.")
        return None
    except json.JSONDecodeError:
        print(f"The file {workflow_path} contains invalid JSON.")
        return None


def prompt_to_image(workflow, positve_prompt, negative_prompt="", save_previews=False):
    prompt = json.loads(workflow)
    id_to_class_type = {id: details["class_type"] for id, details in prompt.items()}
    k_sampler = [key for key, value in id_to_class_type.items() if value == "KSampler"][
        0
    ]
    prompt.get(k_sampler)["inputs"]["seed"] = random.randint(10**14, 10**15 - 1)
    postive_input_id = prompt.get(k_sampler)["inputs"]["positive"][0]
    prompt.get(postive_input_id)["inputs"]["text"] = positve_prompt

    if negative_prompt != "":
        negative_input_id = prompt.get(k_sampler)["inputs"]["negative"][0]
        prompt.get(negative_input_id)["inputs"]["text"] = negative_prompt

    generate_image_by_prompt(prompt, "./output/", save_previews)


def generate_image_by_prompt(prompt, output_path, save_previews=False):
    try:
        ws, server_address, client_id = open_websocket_connection()
        prompt_id = queue_prompt(prompt, client_id, server_address)["prompt_id"]
        track_progress(prompt, ws, prompt_id)
        images = get_images(prompt_id, server_address, save_previews)
        save_image(images, output_path, save_previews)
    finally:
        ws.close()


def track_progress(prompt, ws, prompt_id):
    node_ids = list(prompt.keys())
    finished_nodes = []

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "progress":
                data = message["data"]
                current_step = data["value"]
                print("In K-Sampler -> Step: ", current_step, " of: ", data["max"])
            if message["type"] == "execution_cached":
                data = message["data"]
                for itm in data["nodes"]:
                    if itm not in finished_nodes:
                        finished_nodes.append(itm)
                        print(
                            "Progess: ",
                            len(finished_nodes),
                            "/",
                            len(node_ids),
                            " Tasks done",
                        )
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] not in finished_nodes:
                    finished_nodes.append(data["node"])
                    print(
                        "Progess: ",
                        len(finished_nodes),
                        "/",
                        len(node_ids),
                        " Tasks done",
                    )

                if data["node"] is None and data["prompt_id"] == prompt_id:
                    break  # Execution is done
        else:
            continue
    return


def get_images(prompt_id, server_address, allow_preview=False):
    output_images = []

    history = get_history(prompt_id, server_address)[prompt_id]
    for node_id in history["outputs"]:
        node_output = history["outputs"][node_id]
        output_data = {}
        if "images" in node_output:
            for image in node_output["images"]:
                if allow_preview and image["type"] == "temp":
                    preview_data = get_image(
                        image["filename"],
                        image["subfolder"],
                        image["type"],
                        server_address,
                    )
                    output_data["image_data"] = preview_data
                if image["type"] == "output":
                    image_data = get_image(
                        image["filename"],
                        image["subfolder"],
                        image["type"],
                        server_address,
                    )
                    output_data["image_data"] = image_data
        output_data["file_name"] = image["filename"]
        output_data["type"] = image["type"]
        output_images.append(output_data)

    return output_images


def save_image(images, output_path, save_previews):
    for itm in images:
        directory = (
            os.path.join(output_path, "temp/")
            if itm["type"] == "temp" and save_previews
            else output_path
        )
        os.makedirs(directory, exist_ok=True)
        try:
            image = Image.open(io.BytesIO(itm["image_data"]))
            image.save(os.path.join(directory, itm["file_name"]))
        except Exception as e:
            print(f"Failed to save image {itm['file_name']}: {e}")


#Commented out code to display the output images:
def generate_image_by_prompt_and_image(prompt, output_path, save_previews=False):
  try:
    ws, server_address, client_id = open_websocket_connection()
    prompt_id = queue_prompt(prompt, client_id, server_address)['prompt_id']
    track_progress(prompt, ws, prompt_id)
    images = get_images(prompt_id, server_address, save_previews)
    save_image(images, output_path, save_previews)
  finally:
    ws.close()

with open("./default_workflow_api.json", "r", encoding="utf-8") as f:
    workflow_data = f.read()

workflow = json.loads(workflow_data)
seed = random.randint(1, 1000000000)
workflow["3"]["inputs"]["seed"] = seed

output_path = "./"
generate_image_by_prompt_and_image(workflow, output_path)