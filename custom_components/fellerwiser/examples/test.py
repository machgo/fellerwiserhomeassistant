import requests


ip = "192.168.0.18"
response = requests.get("http://"+ip+"/api/loads", headers= {'authorization':'Bearer 35c369b1-2f8c-4103-83dd-0188a565d3fc'})
loads = response.json()

for value in loads["data"]:
    if value["type"] == "dim":
        print (value)


response = requests.put("http://"+ip+"/api/loads/13/target_state", headers= {'authorization':'Bearer 35c369b1-2f8c-4103-83dd-0188a565d3fc'}, json={'bri': 5000})
print (response.json())
