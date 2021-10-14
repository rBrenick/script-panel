import skyhook.client

def run_script_in_blender(script_path):
    client = skyhook.client.BlenderClient()
    client.execute("run_script", parameters={"script_path": script_path})
