import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, stride=1, dropout=0.1):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(in_dim)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv1 = nn.Linear(in_dim, out_dim)
        self.bn2 = nn.BatchNorm1d(out_dim)
        self.relu2 = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)
        self.conv2 = nn.Linear(out_dim, out_dim)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_dim != out_dim:
            self.shortcut = nn.Sequential(
                nn.Linear(in_dim, out_dim, bias=False),
                nn.BatchNorm1d(out_dim)
            )
    
    def forward(self, x):
        identity = x
        out = self.bn1(x)
        out = self.relu1(out)
        out = self.conv1(out)
        out = self.bn2(out)
        out = self.relu2(out)
        out = self.dropout(out)
        out = self.conv2(out)
        out += self.shortcut(identity)
        return out

class EfficientNet200K(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.expansion = 4
        hidden_dims = [128, 256, 384]
        
        self.initial = nn.Sequential(
            nn.Linear(input_dim, hidden_dims[0]),
            nn.BatchNorm1d(hidden_dims[0]),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
        
        self.layer1 = self._make_layer(hidden_dims[0], hidden_dims[0], blocks=2, stride=1, dropout=0.15)
        self.layer2 = self._make_layer(hidden_dims[0], hidden_dims[1], blocks=2, stride=2, dropout=0.15)
        self.layer3 = self._make_layer(hidden_dims[1], hidden_dims[2], blocks=2, stride=2, dropout=0.2)
        
        self.final_bn = nn.BatchNorm1d(hidden_dims[2])
        self.final_relu = nn.ReLU(inplace=True)
        self.final_dropout = nn.Dropout(0.25)
        
        self.classifier = nn.Linear(hidden_dims[2], num_classes)
        
        self._initialize_weights()
        
    def _make_layer(self, in_dim, out_dim, blocks, stride, dropout):
        layers = [ResidualBlock(in_dim, out_dim, stride, dropout)]
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_dim, out_dim, 1, dropout))
        return nn.Sequential(*layers)
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        x = self.initial(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.final_bn(x)
        x = self.final_relu(x)
        x = self.final_dropout(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get('device', 'cpu'))
        num_classes = metadata['num_classes']
        input_dim = metadata['input_dim']
        
        model = EfficientNet200K(input_dim, num_classes).to(device)
        
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > 200000:
            model = self._create_fallback_model(input_dim, num_classes).to(device)
        
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0005)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
        
        best_acc = 0
        patience = 10
        patience_counter = 0
        best_state = None
        
        num_epochs = 100
        
        for epoch in range(num_epochs):
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                total_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * correct / total
            
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * val_correct / val_total
            
            scheduler.step()
            
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        if best_state is not None:
            model.load_state_dict(best_state)
        
        return model
    
    def _create_fallback_model(self, input_dim, num_classes):
        class FallbackModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Linear(input_dim, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    nn.Linear(256, 384),
                    nn.BatchNorm1d(384),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    nn.Linear(384, 512),
                    nn.BatchNorm1d(512),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.25),
                    nn.Linear(512, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                )
                self.classifier = nn.Linear(256, num_classes)
                
                total = sum(p.numel() for p in self.parameters() if p.requires_grad)
                if total > 200000:
                    self.features = nn.Sequential(
                        nn.Linear(input_dim, 192),
                        nn.BatchNorm1d(192),
                        nn.ReLU(inplace=True),
                        nn.Dropout(0.2),
                        nn.Linear(192, 256),
                        nn.BatchNorm1d(256),
                        nn.ReLU(inplace=True),
                        nn.Dropout(0.25),
                    )
                    self.classifier = nn.Linear(256, num_classes)
            
            def forward(self, x):
                x = self.features(x)
                x = self.classifier(x)
                return x
        
        return FallbackModel(input_dim, num_classes)