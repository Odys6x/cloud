import torch.nn as nn
import torch.nn.functional as F

class ComplexTabularModel(nn.Module):
    def __init__(self, input_dim):
        super(ComplexTabularModel, self).__init__()
        self.input_layer = nn.Linear(input_dim, 128)

        # Hidden layers
        self.hidden_layers = nn.Sequential(
            nn.Linear(128, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(),
            nn.Dropout(0.3),

            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(),
            nn.Dropout(0.3)
        )

        # Residual block
        self.residual_block = nn.Sequential(
            nn.Linear(64, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(),
            nn.Dropout(0.2)
        )

        # Output layer (2 output classes: win/lose)
        self.output_layer = nn.Linear(64, 2)

    def forward(self, x):
        x = F.leaky_relu(self.input_layer(x))
        x = self.hidden_layers(x)

        # Skip connection (residual block)
        residual = self.residual_block(x)
        x = x + residual

        # Output logits (do not apply softmax here)
        x = self.output_layer(x)
        return x
