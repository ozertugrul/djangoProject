import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models
import numpy as np

class UpConv(nn.Module):
    def __init__(self, inc, outc, scale=2):
        super(UpConv, self).__init__()
        self.trans_conv = nn.ConvTranspose2d(inc, outc, kernel_size=4, stride=2, padding=1)
        self.se = CBAMBlock(outc)
        self.conv = nn.Conv2d(outc, outc, 3, stride=1, padding=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.trans_conv(x)
        x = self.se(x)
        x = self.conv(x)
        x = self.relu(x)
        return x

class ChannelAttention(nn.Module):
    def __init__(self, channel, reduction=16):
        super(ChannelAttention, self).__init__()
        self.maxpool = nn.AdaptiveMaxPool2d(1)
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.se = nn.Sequential(
            nn.Conv2d(channel, channel // reduction, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(channel // reduction, channel, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        max_result = self.maxpool(x)
        avg_result = self.avgpool(x)
        max_out = self.se(max_result)
        avg_out = self.se(avg_result)
        output = self.sigmoid(max_out + avg_out)
        return output

class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, padding=kernel_size // 2)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        max_result, _ = torch.max(x, dim=1, keepdim=True)
        avg_result = torch.mean(x, dim=1, keepdim=True)
        result = torch.cat([max_result, avg_result], 1)
        output = self.conv(result)
        output = self.sigmoid(output)
        return output

class CBAMBlock(nn.Module):
    def __init__(self, channel, reduction=16, kernel_size=7):
        super(CBAMBlock, self).__init__()
        self.ca = ChannelAttention(channel, reduction)
        self.sa = SpatialAttention(kernel_size)

    def forward(self, x):
        x_out = x * self.ca(x)
        x_out = x_out * self.sa(x_out)
        return x_out

class AOTBlock(nn.Module):
    def __init__(self, dim, rates):
        super(AOTBlock, self).__init__()
        self.rates = rates
        self.blocks = nn.ModuleList()
        for rate in rates:
            self.blocks.append(
                nn.Sequential(
                    nn.ReflectionPad2d(rate),
                    nn.Conv2d(dim, dim // 3, 3, padding=0, dilation=rate),
                    nn.ReLU(True)
                )
            )
        self.fuse = nn.Sequential(nn.ReflectionPad2d(1), nn.Conv2d(len(rates) * (dim // 3), dim, 3, padding=0, dilation=1))
        self.gate = nn.Sequential(nn.ReflectionPad2d(1), nn.Conv2d(dim, dim, 3, padding=0, dilation=1))
        self.cbam = CBAMBlock(channel=dim)

    def forward(self, x):
        out = torch.cat([block(x) for block in self.blocks], dim=1)
        out = self.fuse(out)
        mask = my_layer_norm(self.gate(x))
        mask = torch.sigmoid(mask)
        out = x * (1 - mask) + out * mask
        out = self.cbam(out)
        return out

def my_layer_norm(feat):
    mean = feat.mean((2, 3), keepdim=True)
    std = feat.std((2, 3), keepdim=True) + 1e-9
    feat = 2 * (feat - mean) / std - 1
    feat = 5 * feat
    return feat

class InpaintGenerator(nn.Module):
    def __init__(self):
        super(InpaintGenerator, self).__init__()
        block_num = 3
        rates = [1, 2, 4]

        self.encoder1 = nn.Sequential(
            nn.ReflectionPad2d(3),
            nn.Conv2d(1, 64, 7),
            nn.ReLU(True)
        )

        self.encoder2 = nn.Sequential(
            nn.Conv2d(64, 128, 4, stride=2, padding=1),
            nn.ReLU(True)
        )

        self.encoder3 = nn.Sequential(
            nn.Conv2d(128, 256, 4, stride=2, padding=1),
            nn.ReLU(True)
        )

        self.middle = nn.Sequential(*[AOTBlock(256, rates) for _ in range(block_num)])

        self.upconv1 = UpConv(256, 128)
        self.upconv2 = UpConv(128, 64)
        self.final_conv = nn.Conv2d(64, 3, 3, stride=1, padding=1)

    def forward(self, x):
        e1 = self.encoder1(x)
        e2 = self.encoder2(e1)
        e3 = self.encoder3(e2)

        m = self.middle(e3)

        d1 = self.upconv1(m) + e2
        d2 = self.upconv2(d1) + e1
        out = self.final_conv(d2)
        out = torch.tanh(out)

        return out

class Discriminator(nn.Module):
    def __init__(self, in_channels=4):
        super(Discriminator, self).__init__()

        def critic_block(in_filters, out_filters, normalization=True):
            layers = [nn.Conv2d(in_filters, out_filters, 4, stride=2, padding=1)]
            if normalization:
                layers.append(nn.InstanceNorm2d(out_filters))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *critic_block(in_channels, 64, normalization=False),
            *critic_block(64, 128),
            *critic_block(128, 256),
            *critic_block(256, 512),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(512, 1)
        )

    def forward(self, ab, l):
        img_input = torch.cat((ab, l), 1)
        output = self.model(img_input)
        return output

class CWGANNN(nn.Module):
    def __init__(self, in_channels=1, out_channels=3, learning_rate=0.00001, lambda_recon=100, lambda_gp=10, lambda_r1=10):
        super().__init__()
        self.generator = InpaintGenerator()
        self.critic = Discriminator(in_channels + out_channels)
        self.learning_rate = learning_rate
        self.lambda_recon = lambda_recon
        self.lambda_gp = lambda_gp
        self.lambda_r1 = lambda_r1

        self.recon_criterion = nn.L1Loss()
        self.perceptual_criterion = PerceptualLoss()
        self.style_criterion = StyleLoss()
        self.nsgan_criterion = NSGANLoss()
        self.smgan_criterion = SMGANLoss()

    def load_weights(self, generator_path, critic_path):
        self.generator.load_state_dict(torch.load(generator_path, map_location=torch.device('cpu')))
        self.critic.load_state_dict(torch.load(critic_path, map_location=torch.device('cpu')))
        print(f"Weights loaded from {generator_path} and {critic_path}")

    def forward(self, x):
        return self.generator(x)

# Yardımcı sınıflar (PerceptualLoss, StyleLoss, NSGANLoss, SMGANLoss) burada tanımlanmalı
# Bu sınıfların tanımları orijinal kodunuzda olmalı

class PerceptualLoss(nn.Module):
    def __init__(self):
        super(PerceptualLoss, self).__init__()
        # Perceptual Loss implementasyonu

    def forward(self, x, y):
        # Perceptual Loss hesaplaması
        return torch.tensor(0.0)  # Geçici olarak 0 döndürüyoruz

class StyleLoss(nn.Module):
    def __init__(self):
        super(StyleLoss, self).__init__()
        # Style Loss implementasyonu  

    def forward(self, x, y):
        # Style Loss hesaplaması 
        return torch.tensor(0.0)  # Geçici olarak 0 döndürüyoruz

class NSGANLoss(nn.Module):
    def __init__(self):
        super(NSGANLoss, self).__init__()
        # NSGAN Loss implementasyonu

    def forward(self, x, y):
        # NSGAN Loss hesaplaması
        return torch.tensor(0.0)  # Geçici olarak 0 döndürüyoruz

class SMGANLoss(nn.Module):
    def __init__(self):
        super(SMGANLoss, self).__init__()
        # SMGAN Loss implementasyonu

    def forward(self, x, y):
        # SMGAN Loss hesaplaması
        return torch.tensor(0.0)  # Geçici olarak 0 döndürüyoruz