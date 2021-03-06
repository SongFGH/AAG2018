# -*- coding: utf-8 -*-

# Import packages
from keras.applications.nasnet import preprocess_input
from keras.optimizers import Adam
from keras.utils.multi_gpu_utils import multi_gpu_model
from networks import NASNetL
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.utils import compute_class_weight
import argparse
import os
import numpy as np
import tensorflow as tf

# Set up argument parser
ap = argparse.ArgumentParser()

# Define arguments
ap.add_argument("-dd", "--data_dir", required=True,
                help="Path to the file where the data and labels are stored.")
ap.add_argument("-of", "--output_file", required=True,
                help="Path to the file where the trained model is saved.")

# Parse arguments
args = vars(ap.parse_args())

# Assign arguments to variables
path_to_data = args['data_dir']
path_to_output = args['output_file']

# Load images and labels
images, labels = np.load(os.path.join(path_to_data, 'data.npy')), \
                 np.load(os.path.join(path_to_data, 'labels.npy'))

# Calculate balanced class weights and cast into dictionary
class_weight = compute_class_weight('balanced', np.unique(labels), labels)
class_weight = dict(enumerate(class_weight))

# Preprocess images
images = preprocess_input(images)

# Split both images and texts into training and validation sets
X_train_img, X_test_img, y_train_img, y_test_img = train_test_split(images, labels,
                                                                    test_size=0.10,
                                                                    random_state=18)

# Use CPU to compile the model
with tf.device('/cpu:0'):

    # Build the model
    model = NASNetL.build(neurons=64, l2_penalty=0.000001, dropout=0.5)

# Parallelize the model
model = multi_gpu_model(model, gpus=None)

# Set up optimizer
optimizer = Adam()

# Compile the model
model.compile(loss='binary_crossentropy', optimizer=optimizer,
              metrics=['binary_accuracy'])

# Train the parallel model using GPUs
model.fit(X_train_img, y_train_img,
          epochs=2,
          batch_size=128,
          shuffle=True,
          validation_split=0.1,
          class_weight=class_weight,
          verbose=1)

with tf.device('/cpu:0'):

        # Make predictions and convert labels from one hot to sparse
        y_pred = model.predict(X_test_img, batch_size=64)

        # Round output from sigmoid activation
        y_pred[y_pred > 0.5] = 1
        y_pred[y_pred < 0.5] = 0

        # Get the classification report
        report = classification_report(y_test_img,
                                       y_pred,
                                       target_names=['activity',
                                                     'not_activity'])

        print(report)

# Save model
model.save(path_to_output)
