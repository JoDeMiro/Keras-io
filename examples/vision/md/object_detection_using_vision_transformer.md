# Object detection with Vision Transformers

**Author:** [Karan V. Dave](https://www.linkedin.com/in/karan-dave-811413164/)<br>
**Date created:** 2022/03/27<br>
**Last modified:** 2022/03/27<br>
**Description:** A simple Keras implementation of object detection using Vision Transformers.


<img class="k-inline-icon" src="https://colab.research.google.com/img/colab_favicon.ico"/> [**View in Colab**](https://colab.research.google.com/github/keras-team\keras-io\blob\master\examples\vision/ipynb/object_detection_using_vision_transformer.ipynb)  <span class="k-dot">•</span><img class="k-inline-icon" src="https://github.com/favicon.ico"/> [**GitHub source**](https://github.com/keras-team\keras-io\blob\master\examples\vision/object_detection_using_vision_transformer.py)


---
## Introduction

The article
[Vision Transformer (ViT)](https://arxiv.org/abs/2010.11929)
architecture by Alexey Dosovitskiy et al.
demonstrates that a pure transformer applied directly to sequences of image
patches can perform well on object detection tasks.

In this Keras example, we implement an object detection ViT
and we train it on the
[Caltech 101 dataset](http://www.vision.caltech.edu/datasets/)
to detect an airplane in the given image.

This example requires TensorFlow 2.4 or higher, and
[TensorFlow Addons](https://www.tensorflow.org/addons/overview),
from which we import the `AdamW` optimizer.

TensorFlow Addons can be installed via the following command:

```
pip install -U tensorflow-addons
```

---
## Imports and setup


```python
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import tensorflow_addons as tfa
import matplotlib.pyplot as plt
import numpy as np
import cv2
import os
import scipy.io
import shutil
```

---
## Prepare dataset

We use the [Caltech 101 Dataset](http://www.vision.caltech.edu/Image_Datasets/Caltech101/).


```python
# Path to images and annotations
path_images = "/101_ObjectCategories/airplanes/"
path_annot = "/Annotations/Airplanes_Side_2/"

path_to_downloaded_file = keras.utils.get_file(
    fname="caltech_101_zipped",
    origin="https://data.caltech.edu/tindfiles/serve/e41f5188-0b32-41fa-801b-d1e840915e80/",
    extract=True,
    archive_format="zip",  # downloaded file format
    cache_dir="/",  # cache and extract in current directory
)

# Extracting tar files found inside main zip file
shutil.unpack_archive("/datasets/caltech-101/101_ObjectCategories.tar.gz", "/")
shutil.unpack_archive("/datasets/caltech-101/Annotations.tar", "/")

# list of paths to images and annotations
image_paths = [
    f for f in os.listdir(path_images) if os.path.isfile(os.path.join(path_images, f))
]
annot_paths = [
    f for f in os.listdir(path_annot) if os.path.isfile(os.path.join(path_annot, f))
]

image_paths.sort()
annot_paths.sort()

image_size = 224  # resize input images to this size

images, targets = [], []

# loop over the annotations and images, preprocess them and store in lists
for i in range(0, len(annot_paths)):
    # Access bounding box coordinates
    annot = scipy.io.loadmat(path_annot + annot_paths[i])["box_coord"][0]

    top_left_x, top_left_y = annot[2], annot[0]
    bottom_right_x, bottom_right_y = annot[3], annot[1]

    image = keras.utils.load_img(
        path_images + image_paths[i],
    )
    (w, h) = image.size[:2]

    # resize train set images
    if i < int(len(annot_paths) * 0.8):
        # resize image if it is for training dataset
        image = image.resize((image_size, image_size))

    # convert image to array and append to list
    images.append(keras.utils.img_to_array(image))

    # apply relative scaling to bounding boxes as per given image and append to list
    targets.append(
        (
            float(top_left_x) / w,
            float(top_left_y) / h,
            float(bottom_right_x) / w,
            float(bottom_right_y) / h,
        )
    )

# Convert the list to numpy array, split to train and test dataset
(x_train), (y_train) = (
    np.asarray(images[: int(len(images) * 0.8)]),
    np.asarray(targets[: int(len(targets) * 0.8)]),
)
(x_test), (y_test) = (
    np.asarray(images[int(len(images) * 0.8) :]),
    np.asarray(targets[int(len(targets) * 0.8) :]),
)
```


---
## Implement multilayer-perceptron (MLP)

We use the code from the Keras example
[Image classification with Vision Transformer](https://keras.io/examples/vision/image_classification_with_vision_transformer/)
as a reference.


```python

def mlp(x, hidden_units, dropout_rate):
    for units in hidden_units:
        x = layers.Dense(units, activation=tf.nn.gelu)(x)
        x = layers.Dropout(dropout_rate)(x)
    return x

```

---
## Implement the patch creation layer


```python

class Patches(layers.Layer):
    def __init__(self, patch_size):
        super(Patches, self).__init__()
        self.patch_size = patch_size

    #     Override function to avoid error while saving model
    def get_config(self):
        config = super().get_config().copy()
        config.update(
            {
                "input_shape": input_shape,
                "patch_size": patch_size,
                "num_patches": num_patches,
                "projection_dim": projection_dim,
                "num_heads": num_heads,
                "transformer_units": transformer_units,
                "transformer_layers": transformer_layers,
                "mlp_head_units": mlp_head_units,
            }
        )
        return config

    def call(self, images):
        batch_size = tf.shape(images)[0]
        patches = tf.image.extract_patches(
            images=images,
            sizes=[1, self.patch_size, self.patch_size, 1],
            strides=[1, self.patch_size, self.patch_size, 1],
            rates=[1, 1, 1, 1],
            padding="VALID",
        )
        # return patches
        return tf.reshape(patches, [batch_size, -1, patches.shape[-1]])

```

---
## Display patches for an input image


```python
patch_size = 32  # Size of the patches to be extracted from the input images

plt.figure(figsize=(4, 4))
plt.imshow(x_train[0].astype("uint8"))
plt.axis("off")

patches = Patches(patch_size)(tf.convert_to_tensor([x_train[0]]))
print(f"Image size: {image_size} X {image_size}")
print(f"Patch size: {patch_size} X {patch_size}")
print(f"{patches.shape[1]} patches per image \n{patches.shape[-1]} elements per patch")


n = int(np.sqrt(patches.shape[1]))
plt.figure(figsize=(4, 4))
for i, patch in enumerate(patches[0]):
    ax = plt.subplot(n, n, i + 1)
    patch_img = tf.reshape(patch, (patch_size, patch_size, 3))
    plt.imshow(patch_img.numpy().astype("uint8"))
    plt.axis("off")
```

<div class="k-default-codeblock">
```
Image size: 224 X 224
Patch size: 32 X 32
49 patches per image 
3072 elements per patch
```
</div>
    


    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_11_1.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_11_2.png)
    


---
## Implement the patch encoding layer

The `PatchEncoder` layer linearly transforms a patch by projecting it into a
vector of size `projection_dim`. It also adds a learnable position
embedding to the projected vector.


```python

class PatchEncoder(layers.Layer):
    def __init__(self, num_patches, projection_dim):
        super(PatchEncoder, self).__init__()
        self.num_patches = num_patches
        self.projection = layers.Dense(units=projection_dim)
        self.position_embedding = layers.Embedding(
            input_dim=num_patches, output_dim=projection_dim
        )

    # Override function to avoid error while saving model
    def get_config(self):
        config = super().get_config().copy()
        config.update(
            {
                "input_shape": input_shape,
                "patch_size": patch_size,
                "num_patches": num_patches,
                "projection_dim": projection_dim,
                "num_heads": num_heads,
                "transformer_units": transformer_units,
                "transformer_layers": transformer_layers,
                "mlp_head_units": mlp_head_units,
            }
        )
        return config

    def call(self, patch):
        positions = tf.range(start=0, limit=self.num_patches, delta=1)
        encoded = self.projection(patch) + self.position_embedding(positions)
        return encoded

```

---
## Build the ViT model

The ViT model has multiple Transformer blocks.
The `MultiHeadAttention` layer is used for self-attention,
applied to the sequence of image patches. The encoded patches (skip connection)
and self-attention layer outputs are normalized and fed into a
multilayer perceptron (MLP).
The model outputs four dimensions representing
the bounding box coordinates of an object.


```python

def create_vit_object_detector(
    input_shape,
    patch_size,
    num_patches,
    projection_dim,
    num_heads,
    transformer_units,
    transformer_layers,
    mlp_head_units,
):
    inputs = layers.Input(shape=input_shape)
    # Create patches
    patches = Patches(patch_size)(inputs)
    # Encode patches
    encoded_patches = PatchEncoder(num_patches, projection_dim)(patches)

    # Create multiple layers of the Transformer block.
    for _ in range(transformer_layers):
        # Layer normalization 1.
        x1 = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
        # Create a multi-head attention layer.
        attention_output = layers.MultiHeadAttention(
            num_heads=num_heads, key_dim=projection_dim, dropout=0.1
        )(x1, x1)
        # Skip connection 1.
        x2 = layers.Add()([attention_output, encoded_patches])
        # Layer normalization 2.
        x3 = layers.LayerNormalization(epsilon=1e-6)(x2)
        # MLP
        x3 = mlp(x3, hidden_units=transformer_units, dropout_rate=0.1)
        # Skip connection 2.
        encoded_patches = layers.Add()([x3, x2])

    # Create a [batch_size, projection_dim] tensor.
    representation = layers.LayerNormalization(epsilon=1e-6)(encoded_patches)
    representation = layers.Flatten()(representation)
    representation = layers.Dropout(0.3)(representation)
    # Add MLP.
    features = mlp(representation, hidden_units=mlp_head_units, dropout_rate=0.3)

    bounding_box = layers.Dense(4)(
        features
    )  # Final four neurons that output bounding box

    # return Keras model.
    return keras.Model(inputs=inputs, outputs=bounding_box)

```

---
## Run the experiment


```python

def run_experiment(model, learning_rate, weight_decay, batch_size, num_epochs):

    optimizer = tfa.optimizers.AdamW(
        learning_rate=learning_rate, weight_decay=weight_decay
    )

    # Compile model.
    model.compile(optimizer=optimizer, loss=keras.losses.MeanSquaredError())

    checkpoint_filepath = "logs/"
    checkpoint_callback = keras.callbacks.ModelCheckpoint(
        checkpoint_filepath,
        monitor="val_loss",
        save_best_only=True,
        save_weights_only=True,
    )

    history = model.fit(
        x=x_train,
        y=y_train,
        batch_size=batch_size,
        epochs=num_epochs,
        validation_split=0.1,
        callbacks=[
            checkpoint_callback,
            keras.callbacks.EarlyStopping(monitor="val_loss", patience=10),
        ],
    )

    return history


input_shape = (image_size, image_size, 3)  # input image shape
learning_rate = 0.001
weight_decay = 0.0001
batch_size = 32
num_epochs = 100
num_patches = (image_size // patch_size) ** 2
projection_dim = 64
num_heads = 4
# Size of the transformer layers
transformer_units = [
    projection_dim * 2,
    projection_dim,
]
transformer_layers = 4
mlp_head_units = [2048, 1024, 512, 64, 32]  # Size of the dense layers


history = []
num_patches = (image_size // patch_size) ** 2

vit_object_detector = create_vit_object_detector(
    input_shape,
    patch_size,
    num_patches,
    projection_dim,
    num_heads,
    transformer_units,
    transformer_layers,
    mlp_head_units,
)

# Train model
history = run_experiment(
    vit_object_detector, learning_rate, weight_decay, batch_size, num_epochs
)

```

<div class="k-default-codeblock">
```
Epoch 1/100
18/18 [==============================] - 17s 537ms/step - loss: 0.9240 - val_loss: 0.3514
Epoch 2/100
18/18 [==============================] - 9s 530ms/step - loss: 0.3749 - val_loss: 0.3061
Epoch 3/100
18/18 [==============================] - 10s 568ms/step - loss: 0.3072 - val_loss: 0.2586
Epoch 4/100
18/18 [==============================] - 9s 512ms/step - loss: 0.2443 - val_loss: 0.2153
Epoch 5/100
18/18 [==============================] - 9s 487ms/step - loss: 0.2023 - val_loss: 0.1768
Epoch 6/100
18/18 [==============================] - 8s 476ms/step - loss: 0.1630 - val_loss: 0.1428
Epoch 7/100
18/18 [==============================] - 9s 517ms/step - loss: 0.1298 - val_loss: 0.1124
Epoch 8/100
18/18 [==============================] - 9s 497ms/step - loss: 0.1015 - val_loss: 0.0860
Epoch 9/100
18/18 [==============================] - 9s 481ms/step - loss: 0.0793 - val_loss: 0.0638
Epoch 10/100
18/18 [==============================] - 8s 463ms/step - loss: 0.0569 - val_loss: 0.0457
Epoch 11/100
18/18 [==============================] - 8s 461ms/step - loss: 0.0437 - val_loss: 0.0316
Epoch 12/100
18/18 [==============================] - 9s 491ms/step - loss: 0.0322 - val_loss: 0.0213
Epoch 13/100
18/18 [==============================] - 10s 585ms/step - loss: 0.0233 - val_loss: 0.0141
Epoch 14/100
18/18 [==============================] - 12s 675ms/step - loss: 0.0181 - val_loss: 0.0091
Epoch 15/100
18/18 [==============================] - 10s 545ms/step - loss: 0.0136 - val_loss: 0.0059
Epoch 16/100
18/18 [==============================] - 9s 498ms/step - loss: 0.0124 - val_loss: 0.0040
Epoch 17/100
18/18 [==============================] - 10s 581ms/step - loss: 0.0106 - val_loss: 0.0029
Epoch 18/100
18/18 [==============================] - 10s 545ms/step - loss: 0.0098 - val_loss: 0.0023
Epoch 19/100
18/18 [==============================] - 11s 648ms/step - loss: 0.0094 - val_loss: 0.0019
Epoch 20/100
18/18 [==============================] - 9s 506ms/step - loss: 0.0089 - val_loss: 0.0016
Epoch 21/100
18/18 [==============================] - 9s 504ms/step - loss: 0.0091 - val_loss: 0.0015
Epoch 22/100
18/18 [==============================] - 9s 505ms/step - loss: 0.0081 - val_loss: 0.0015
Epoch 23/100
18/18 [==============================] - 9s 501ms/step - loss: 0.0086 - val_loss: 0.0015
Epoch 24/100
18/18 [==============================] - 9s 479ms/step - loss: 0.0087 - val_loss: 0.0015
Epoch 25/100
18/18 [==============================] - 9s 494ms/step - loss: 0.0081 - val_loss: 0.0014
Epoch 26/100
18/18 [==============================] - 9s 502ms/step - loss: 0.0088 - val_loss: 0.0014
Epoch 27/100
18/18 [==============================] - 9s 507ms/step - loss: 0.0083 - val_loss: 0.0014
Epoch 28/100
18/18 [==============================] - 9s 490ms/step - loss: 0.0084 - val_loss: 0.0014
Epoch 29/100
18/18 [==============================] - 8s 472ms/step - loss: 0.0088 - val_loss: 0.0014
Epoch 30/100
18/18 [==============================] - 9s 494ms/step - loss: 0.0087 - val_loss: 0.0014
Epoch 31/100
18/18 [==============================] - 9s 506ms/step - loss: 0.0077 - val_loss: 0.0013
Epoch 32/100
18/18 [==============================] - 8s 473ms/step - loss: 0.0080 - val_loss: 0.0013
Epoch 33/100
18/18 [==============================] - 9s 490ms/step - loss: 0.0081 - val_loss: 0.0013
Epoch 34/100
18/18 [==============================] - 8s 474ms/step - loss: 0.0080 - val_loss: 0.0013
Epoch 35/100
18/18 [==============================] - 9s 504ms/step - loss: 0.0086 - val_loss: 0.0013
Epoch 36/100
18/18 [==============================] - 9s 519ms/step - loss: 0.0075 - val_loss: 0.0013
Epoch 37/100
18/18 [==============================] - 9s 507ms/step - loss: 0.0075 - val_loss: 0.0013
Epoch 38/100
18/18 [==============================] - 9s 476ms/step - loss: 0.0076 - val_loss: 0.0013
Epoch 39/100
18/18 [==============================] - 8s 463ms/step - loss: 0.0076 - val_loss: 0.0014
Epoch 40/100
18/18 [==============================] - 8s 463ms/step - loss: 0.0076 - val_loss: 0.0013
Epoch 41/100
18/18 [==============================] - 9s 481ms/step - loss: 0.0074 - val_loss: 0.0013
Epoch 42/100
18/18 [==============================] - 8s 469ms/step - loss: 0.0077 - val_loss: 0.0013
Epoch 43/100
18/18 [==============================] - 9s 478ms/step - loss: 0.0080 - val_loss: 0.0013
Epoch 44/100
18/18 [==============================] - 8s 472ms/step - loss: 0.0075 - val_loss: 0.0013
Epoch 45/100
18/18 [==============================] - 11s 600ms/step - loss: 0.0071 - val_loss: 0.0013
Epoch 46/100
18/18 [==============================] - 14s 777ms/step - loss: 0.0075 - val_loss: 0.0012
Epoch 47/100
18/18 [==============================] - 12s 683ms/step - loss: 0.0073 - val_loss: 0.0012
Epoch 48/100
18/18 [==============================] - 10s 539ms/step - loss: 0.0071 - val_loss: 0.0012
Epoch 49/100
18/18 [==============================] - 9s 485ms/step - loss: 0.0069 - val_loss: 0.0012
Epoch 50/100
18/18 [==============================] - 9s 481ms/step - loss: 0.0064 - val_loss: 0.0013
Epoch 51/100
18/18 [==============================] - 8s 470ms/step - loss: 0.0074 - val_loss: 0.0013
Epoch 52/100
18/18 [==============================] - 9s 477ms/step - loss: 0.0069 - val_loss: 0.0013
Epoch 53/100
18/18 [==============================] - 8s 472ms/step - loss: 0.0069 - val_loss: 0.0012
Epoch 54/100
18/18 [==============================] - 10s 586ms/step - loss: 0.0070 - val_loss: 0.0012
Epoch 55/100
18/18 [==============================] - 11s 646ms/step - loss: 0.0073 - val_loss: 0.0012
Epoch 56/100
18/18 [==============================] - 9s 519ms/step - loss: 0.0065 - val_loss: 0.0012
Epoch 57/100
18/18 [==============================] - 10s 540ms/step - loss: 0.0069 - val_loss: 0.0012
Epoch 58/100
18/18 [==============================] - 10s 563ms/step - loss: 0.0066 - val_loss: 0.0013
Epoch 59/100
18/18 [==============================] - 10s 577ms/step - loss: 0.0070 - val_loss: 0.0012
Epoch 60/100
18/18 [==============================] - 9s 499ms/step - loss: 0.0066 - val_loss: 0.0012
Epoch 61/100
18/18 [==============================] - 9s 485ms/step - loss: 0.0062 - val_loss: 0.0012
Epoch 62/100
18/18 [==============================] - 10s 539ms/step - loss: 0.0065 - val_loss: 0.0012
Epoch 63/100
18/18 [==============================] - 9s 527ms/step - loss: 0.0069 - val_loss: 0.0012
Epoch 64/100
18/18 [==============================] - 8s 469ms/step - loss: 0.0063 - val_loss: 0.0013
Epoch 65/100
18/18 [==============================] - 8s 470ms/step - loss: 0.0064 - val_loss: 0.0012
Epoch 66/100
18/18 [==============================] - 8s 466ms/step - loss: 0.0069 - val_loss: 0.0012
Epoch 67/100
18/18 [==============================] - 8s 464ms/step - loss: 0.0064 - val_loss: 0.0012
Epoch 68/100
18/18 [==============================] - 8s 465ms/step - loss: 0.0068 - val_loss: 0.0012
Epoch 69/100
18/18 [==============================] - 8s 464ms/step - loss: 0.0057 - val_loss: 0.0012
Epoch 70/100
18/18 [==============================] - 8s 472ms/step - loss: 0.0064 - val_loss: 0.0012
```
</div>
    

---
## Evaluate the model


```python
import matplotlib.patches as patches

# Saves the model in current path
vit_object_detector.save("vit_object_detector.h5", save_format="h5")

# To calculate IoU (intersection over union, given two bounding boxes)
def bounding_box_intersection_over_union(box_predicted, box_truth):
    # get (x, y) coordinates of intersection of bounding boxes
    top_x_intersect = max(box_predicted[0], box_truth[0])
    top_y_intersect = max(box_predicted[1], box_truth[1])
    bottom_x_intersect = min(box_predicted[2], box_truth[2])
    bottom_y_intersect = min(box_predicted[3], box_truth[3])

    # calculate area of the intersection bb (bounding box)
    intersection_area = max(0, bottom_x_intersect - top_x_intersect + 1) * max(
        0, bottom_y_intersect - top_y_intersect + 1
    )

    # calculate area of the prediction bb and ground-truth bb
    box_predicted_area = (box_predicted[2] - box_predicted[0] + 1) * (
        box_predicted[3] - box_predicted[1] + 1
    )
    box_truth_area = (box_truth[2] - box_truth[0] + 1) * (
        box_truth[3] - box_truth[1] + 1
    )

    # calculate intersection over union by taking intersection
    # area and dividing it by the sum of predicted bb and ground truth
    # bb areas subtracted by  the interesection area

    # return ioU
    return intersection_area / float(
        box_predicted_area + box_truth_area - intersection_area
    )


i, mean_iou = 0, 0

# Compare results for 10 images in the test set
for input_image in x_test[:10]:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 15))
    im = input_image

    # Display the image
    ax1.imshow(im.astype("uint8"))
    ax2.imshow(im.astype("uint8"))

    input_image = cv2.resize(
        input_image, (image_size, image_size), interpolation=cv2.INTER_AREA
    )
    input_image = np.expand_dims(input_image, axis=0)
    preds = vit_object_detector.predict(input_image)[0]

    (h, w) = (im).shape[0:2]

    top_left_x, top_left_y = int(preds[0] * w), int(preds[1] * h)

    bottom_right_x, bottom_right_y = int(preds[2] * w), int(preds[3] * h)

    box_predicted = [top_left_x, top_left_y, bottom_right_x, bottom_right_y]
    # Create the bounding box
    rect = patches.Rectangle(
        (top_left_x, top_left_y),
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y,
        facecolor="none",
        edgecolor="red",
        linewidth=1,
    )
    # Add the bounding box to the image
    ax1.add_patch(rect)
    ax1.set_xlabel(
        "Predicted: "
        + str(top_left_x)
        + ", "
        + str(top_left_y)
        + ", "
        + str(bottom_right_x)
        + ", "
        + str(bottom_right_y)
    )

    top_left_x, top_left_y = int(y_test[i][0] * w), int(y_test[i][1] * h)

    bottom_right_x, bottom_right_y = int(y_test[i][2] * w), int(y_test[i][3] * h)

    box_truth = top_left_x, top_left_y, bottom_right_x, bottom_right_y

    mean_iou += bounding_box_intersection_over_union(box_predicted, box_truth)
    # Create the bounding box
    rect = patches.Rectangle(
        (top_left_x, top_left_y),
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y,
        facecolor="none",
        edgecolor="red",
        linewidth=1,
    )
    # Add the bounding box to the image
    ax2.add_patch(rect)
    ax2.set_xlabel(
        "Target: "
        + str(top_left_x)
        + ", "
        + str(top_left_y)
        + ", "
        + str(bottom_right_x)
        + ", "
        + str(bottom_right_y)
        + "\n"
        + "IoU"
        + str(bounding_box_intersection_over_union(box_predicted, box_truth))
    )
    i = i + 1

print("mean_iou: " + str(mean_iou / len(x_test[:10])))
plt.show()
```

<div class="k-default-codeblock">
```
mean_iou: 0.8711381770184013
```
</div>
    


    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_1.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_2.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_3.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_4.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_5.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_6.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_7.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_8.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_9.png)
    



    
![png](/img/examples/vision/object_detection_using_vision_transformer/object_detection_using_vision_transformer_19_10.png)
    


This example demonstrates that a pure Transformer can be trained
to predict the bounding boxes of an object in a given image,
thus extending the use of Transformers to object detection tasks.
The model can be improved further by tuning hyper-parameters and pre-training.
