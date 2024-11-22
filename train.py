import joblib
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import classification_report
from config import Training, EPOCH, LR, BATCH_SIZE
from dataset.dataset import Preprocessor
from model import ComplexTabularModel

# Preprocessor steps
preprocessor = Preprocessor(scaling=True)
raw_data = preprocessor.load_data("dataset/match_results_with_objectives.csv")
combined_data = preprocessor.combine_team_stats()
X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data()

# Convert to PyTorch tensors
X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train.values, dtype=torch.long)  # Ensure labels are integers
X_val = torch.tensor(X_val, dtype=torch.float32)
y_val = torch.tensor(y_val.values, dtype=torch.long)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_test = torch.tensor(y_test.values, dtype=torch.long)

# Create DataLoaders
train_dataset = TensorDataset(X_train, y_train)
val_dataset = TensorDataset(X_val, y_val)
test_dataset = TensorDataset(X_test, y_test)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)

# Model
input_dim = X_train.shape[1]  # Number of features
model = ComplexTabularModel(input_dim)

# Loss and optimizer
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
optimizer = torch.optim.Adam(model.parameters(), lr=LR)

if Training:
    for epoch in range(EPOCH):
        model.train()  # Switch to training mode
        epoch_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()

            # Forward pass
            y_pred = model(batch_X)
            loss = criterion(y_pred, batch_y)

            # Backward pass
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        print(f"Epoch {epoch + 1}/{EPOCH}, Loss: {epoch_loss:.4f}")

        # Evaluate on validation set
        model.eval()  # Switch to evaluation mode
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                y_pred_eval = model(batch_X)
                y_pred_labels = torch.argmax(y_pred_eval, dim=1)
                correct += (y_pred_labels == batch_y).sum().item()
                total += batch_y.size(0)

        val_accuracy = correct / total * 100
        print(f"Validation Accuracy: {val_accuracy:.2f}%")

    # Save the model after training
    joblib.dump(preprocessor.scaler, 'model/scaler.pkl')
    torch.save(model.state_dict(), "model/model.pth")
    print("Model saved!")

else:
    # Load trained model for evaluation
    model = ComplexTabularModel(input_dim=input_dim)
    model.load_state_dict(torch.load("model/model.pth"))
    model.eval()

    # Final testing on test set
    correct = 0
    total = 0
    y_pred_all = []
    y_test_all = []
    with torch.no_grad():
        for batch_X, batch_y in test_loader:
            y_pred_test = model(batch_X)
            y_pred_labels = torch.argmax(y_pred_test, dim=1)

            correct += (y_pred_labels == batch_y).sum().item()
            total += batch_y.size(0)
            y_pred_all.extend(y_pred_labels.cpu().numpy())
            y_test_all.extend(batch_y.cpu().numpy())

    test_accuracy = correct / total * 100
    print(f"Test Accuracy: {test_accuracy:.2f}%")

    # Print classification report
    print("\nClassification Report:")
    print(classification_report(y_test_all, y_pred_all, target_names=['Team 200 Wins', 'Team 100 Wins']))
