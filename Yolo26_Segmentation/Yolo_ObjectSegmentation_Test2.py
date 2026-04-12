from ultralytics import YOLO

# Load a model. Current model is nano segmentation.
model = YOLO("yolo26n-seg.pt")  # load an official model from https://docs.ultralytics.com/models/

results = model("https://ultralytics.com/images/bus.jpg", save = True)  # predict on an image & save image

for r in results:
    # This allows you to specify any valid system path and filename
    r.save(filename="bus_result.jpg")

print("yay")