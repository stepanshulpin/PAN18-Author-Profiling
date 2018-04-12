# -*- coding: utf-8 -*-
#

# Imports
import torch
import torchvision
from torchvision import datasets, models, transforms
import dataset
import torch.nn as nn
from echotorch.transforms import text
from torch.autograd import Variable
from torch import optim
import argparse
import copy
import matplotlib.pyplot as plt
import numpy as np


def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1)
    plt.imshow(inp)
    plt.show()
# end imshow


# Settings
batch_size = 5
image_size = 224
min_length = 165
n_epoch = 1
voc_size = 1000

# Argument parser
parser = argparse.ArgumentParser(description="PAN18 Author Profiling CNN-C1")

# Argument
parser.add_argument("--output", type=str, help="Model output file", default='.')
parser.add_argument("--dim", type=int, help="Embedding dimension", default=300)
parser.add_argument("--no-cuda", action='store_true', default=False, help="Enables CUDA training")
parser.add_argument("--epoch", type=int, help="Epoch", default=300)
args = parser.parse_args()

# Use CUDA?
args.cuda = not args.no_cuda and torch.cuda.is_available()

# Image augmentation and normalization
data_transforms = {
    'train': transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        # transforms.Normalize([0.5, 0.5, 0.5], [1.0, 1.0, 1.0])
    ]),
    'val': transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        # transforms.Normalize([0.5, 0.5, 0.5], [1.0, 1.0, 1.0])
    ]),
}

# Image data set training
image_dataset_training = dataset.ImageDataset(root='./data', download=True, image_transform=data_transforms['train'],
                                              image_size=image_size, train=True)
pan18loader_training = torch.utils.data.DataLoader(image_dataset_training, batch_size=batch_size, shuffle=True)

# Image data set validation
image_dataset_validation = dataset.ImageDataset(root='./data', download=True, image_transform=data_transforms['val'],
                                                image_size=image_size, train=False)
pan18loader_validation = torch.utils.data.DataLoader(image_dataset_validation, batch_size=batch_size, shuffle=True)

# Loss function
loss_function = nn.CrossEntropyLoss()

# Model
model = models.resnet18(pretrained=True)
num_ftrs = model.fc.in_features
model.fc = nn.Linear(num_ftrs, 2)
if args.cuda:
    model.cuda()
# end if
best_model = copy.deepcopy(model.state_dict())
best_acc = 0.0

# Optimizer
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)

# Epoch
for epoch in range(n_epoch):
    # Total losses
    training_loss = 0.0
    training_total = 0.0
    test_loss = 0.0
    test_total = 0.0

    # For each training samples
    for data in pan18loader_training:
        # Inputs and labels
        images, label = data

        # Variable and CUDA
        inputs, labels = Variable(inputs), Variable(labels)
        if args.cuda:
            inputs, labels = inputs.cuda(), labels.cuda()
        # end if

        # Zero grad
        model.zero_grad()

        # Compute output
        log_probs = model(inputs)

        # Loss
        loss = loss_function(log_probs, labels)

        # Backward and step
        loss.backward()
        optimizer.step()

        # Add
        training_loss += loss.data[0]
        training_total += 1.0
    # end for

    # Counters
    total = 0.0
    success = 0.0

    # For each validation samples
    for data in pan18loader_validation:
        # Inputs and labels
        images, label = data

        # Variable and CUDA
        inputs, labels = Variable(inputs), Variable(labels)
        if args.cuda:
            inputs, labels = inputs.cuda(), labels.cuda()
        # end if

        # Forward
        model_outputs = model(inputs)

        # Compute loss
        loss = loss_function(model_outputs, labels)

        # Take the max as predicted
        _, predicted = torch.max(model_outputs.data, 1)

        # Add to correctly classified word
        success += (predicted == labels.data).sum()
        total += predicted.size(0)

        # Add loss
        test_loss += loss.data[0]
        test_total += 1.0
    # end for

    # Accuracy
    accuracy = success / total * 100.0

    # Print and save loss
    print(u"Epoch {}, training loss {}, test loss {}, accuracy {}".format(epoch, training_loss / training_total,
                                                                          test_loss / test_total, accuracy))

    # Save if better
    if accuracy > best_acc:
        best_acc = accuracy
        best_model = copy.deepcopy(model.state_dict())
    # end if
# end for

# Load best model
model.load_state_dict(best_model)

# Save
torch.save(model, open(args.output, 'wb'))