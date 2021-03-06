# -*- coding: utf-8 -*-
"""Resnet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RbsOrUiGsvnMejYdkYofXpWJBG-hl-Ln
"""

import torch 
import numpy as np 
import torchvision.transforms as transforms 
import torchvision 
import torch.nn.functional as F

#Define what steps to take in a layer, i.e. convolution and batch norm
class Block(torch.nn.Module):
  
    def __init__(self,input_planes,planes,stride=1,size_change=None):
      #size_change is set to none by default and will change if we need to resize matrix before adding to output
        super(Block,self).__init__()
        #define convolution function
        self.conv1 = torch.nn.Conv2d(input_planes,planes,stride=stride,kernel_size=3,padding=1)
        self.bn1   = torch.nn.BatchNorm2d(planes)
        self.conv2 = torch.nn.Conv2d(planes,planes,stride=1,kernel_size=3,padding=1)
        self.bn2   = torch.nn.BatchNorm2d(planes)
        #change the depth of input if it has to be added with a tensor of different size
        self.size_change = size_change
        mn  
        
    #this function goes throgh a block (two layers) and then returns the output
    def forward(self,x):
        #Save the residue so it can be added later with output
        res = x
        #first block : conv -> batch norm -> Relu
        output = F.relu(self.bn1(self.conv1(x)))
        #second block, we stop after bn to change size if needed and then add the residue(x)
        output = self.bn2(self.conv2(output))
        
        #resize matrix if needed
        if self.size_change is not None:
            res = self.size_change(res)
        #add residue to input (H(x) = f(x) + x)
        output += res
        #Now do relu on H(x)
        output = F.relu(output)

        return output
 

class ResNet(torch.nn.Module):
  
    #we define the structure of resnet here, using function layer which outputs the tensor after operations from a block 
    def __init__(self,block,classes=10):
        super(ResNet,self).__init__()
        #defining structure
        self.input_planes = 64
        #first conv layer
        self.conv = torch.nn.Conv2d(3,64,kernel_size=3,stride=1,padding=1)
        self.bn   = torch.nn.BatchNorm2d(64)
        #define four types of layers
        #acc to resnet architecture, layers are repeated 3,4,6,3 time respectively
        self.layer1 = self._layer(block,64,3,stride=1)
        self.layer2 = self._layer(block,128,4,stride=2)
        self.layer3 = self._layer(block,256,6,stride=2) 
        self.layer4 = self._layer(block,512,3,stride=2)
        #average pooling over final output
        self.averagePool = torch.nn.AvgPool2d(kernel_size=4,stride=1)
        #fully connected layer
        self.fc    =  torch.nn.Linear(512,classes)
    
    def _layer(self,block,planes,num_layers,stride=1):
        size_change = None
        #conditions when size of tensor needs to be changed
        if stride!=1 or planes != self.input_planes:
          #we will use 1X1 convolution to resize the matrix and then batch normalize it
            size_change = torch.nn.Sequential(torch.nn.Conv2d(self.input_planes,planes,kernel_size=1,stride=stride),
                                             torch.nn.BatchNorm2d(planes))
        
        #layers is a list that contains all the layers in a block. Then we will use this list and create a sequential model
        #using pytorch's built in nn.sequential function.
        Layers =[]
        #if size needs to be changed, we will do it in the first layer by passing the size_change in Steps
        Layers.append(block(self.input_planes,planes,stride=stride,size_change=size_change))
        self.input_planes = planes
        #now we will append the rest of the layers. we start from 1 because we have already created the first layer in resizing above
        for i in range(1,num_layers):
            Layers.append(block(self.input_planes,planes))
            self.input_planes = planes
        
        #we use torch's built in fucntion to convert list Layers to a pytorch network
        return torch.nn.Sequential(*Layers)

    def forward(self,x):
      #x is the input matrix
        x = F.relu(self.bn(self.conv(x)))

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = F.avg_pool2d(x,4)
        #convert 3d matrix to 2d
        x = x.view(x.size(0),-1)
        x = self.fc(x)

        return x
   
  
def test():
        #to convert image to tensor
    transform = transforms.Compose(
        [transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
        )

    #Load train and test set:
    #load train data
    train = torchvision.datasets.CIFAR10(root='./data',train=True,download=True,transform=transform)
    #we use SGD with batch size = 256 acc to research paper
    trainset = torch.utils.data.DataLoader(train,batch_size=256,shuffle=True)
    #load test data
    test = torchvision.datasets.CIFAR10(root='./data',train=False,download=True,transform=transform)
    testset = torch.utils.data.DataLoader(test,batch_size=256,shuffle=False)
    #use gpu
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
  
    #create an object of ResNet
    net =  ResNet(Block)
    net.to(device)
    #define cost function
    costFunc = torch.nn.CrossEntropyLoss()
    #lr = learning rate
    lr = 0.1
    #define SGD
    optimizer =  torch.optim.SGD(net.parameters(),lr,momentum=0.9)
    #train for 100 epochs
    for epoch in range(100):
      #initialize continuous loss to 0
        closs = 0
        #loop through batches in training data and optimize the parameters
        for i,batch in enumerate(trainset,0):
            data,output = batch
            data,output = data.to(device),output.to(device)#send data to GPU
            prediction = net(data) #output tensor from resnet
            loss = costFunc(prediction,output) #calculates loss function
            closs = loss.item() 

            optimizer.zero_grad()
            loss.backward() #perform backpropagation
            optimizer.step()  #optimize using SGD
        #define correct and total hits to calculate accuracy on test data
        correctHits=0
        total=0
        #test accuracy on test batch
        for batches in testset:
            data,output = batches
            data,output = data.to(device),output.to(device)
            prediction = net(data)
            _,prediction = torch.max(prediction.data,1)  #returns max as well as its index
            total += output.size(0)
            correctHits += (prediction==output).sum().item()
        print('Accuracy on epoch ',epoch+1,'= ',str((correctHits/total)*100))
    
if __name__ == '__main__':
    test()

"""**Explanation of research paper**

1. We saw that just stacking more layers is not helpful due to problem of degradation
2. Degradation: with increase in layers, accuracy gets saturated and then starts decreasing.
3. Degradation is not due to overfitting as training error also increases with increased number of layers.
4. Theoretically, if we take a shallow network and add identity layers in between, then we see that the accuracy of this deeper network should not be no less than the shallower network.
5. To address the problem of degradation, we create a residual network.
6. We assume that it is easier to optimize a function f(x) = 0 by a stack of layers than to optimize an identity function h(x) = x.
7. Hence, we write output function h(x) = f(x) + x and call f(x) the residual function.
8. In ResNet, layers in the network calculate f(x) and then add the original input x to it to get the final output function h(x)
9. Shortcut connections: a connection in the network skipping a few layers and adding the original input x to the output of next few layers f(x).
10. Shortcut functions are identity functions and hence introduce no new parameters and add no computational complexity.
11. We finally observe through examples of CIFAR-10, ImageNet that ResNet is easier to optiimize than plain networks and has low training error. Also its accuracy can easily be increased by deepening the network.
12. When size of output does not match with x from shortcut connections, we use 1X1 convolusion to resize the depth of x.

**Implementation**
1. Block Class
  1. It represents a block in the resnet architecture.
  2. It takes an input matrix, does a 3x3 convolution with given stride, performs batch normalization on the matrix, activates it with relu,again does a 3x3 convolution and then batch norm, if size needs to be changed then it resizes input matrix 'x' and then adds output and x and performs relu function and returns the final output.
  
2. ResNet class:
	1.It contains the architecture of ResNet.
	2.It has layer function to stack together similar blocks.
	3.If input matrix needs to be resized, it will resize the matrix in the first block and then loops over rest of layers.
	4.These layers are stored in a list named Layers, and then converted to a fully connected pytorch network using torch.nn.Sequential() function. 
	5.There are 4 different types of layers in resnet, with depths 64, 128 256 and 512 respectively.
	6.We use ResNet-34 architecture from the research paper so layers are repeated 3,4,6,3 times respectively.
  7.We then do average pooling and created a fully connected layer to be used by loss function.
"""

!pip3 install http://download.pytorch.org/whl/cu80/torch-0.3.0.post4-cp36-cp36m-linux_x86_64.whl 
!pip3 install torchvision

!nvcc --version

!pip3 install https://download.pytorch.org/whl/cu100/torch-1.0.1.post2-cp36-cp36m-linux_x86_64.whl
!pip3 install torchvision