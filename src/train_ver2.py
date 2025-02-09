# -*- coding: utf-8 -*-
"""train_ver2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ccCOW0QE9XPnx1XkBgtMaB5B-KmEyf8b
"""

!pip install torch_geometric
!pip install torch

import pandas as pd
import torch
from torch_geometric.data import HeteroData

# 데이터 로드 및 전처리
users = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/non_fraud_user.csv')
users_fraud = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/fraud_user.csv')
users = pd.concat([users, users_fraud], ignore_index=True)

merchants = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/non_fraud_merchant.csv')
merchants_fraud = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/fraud_merchant.csv')
merchants = pd.concat([merchants, merchants_fraud], ignore_index=True)

non_fraud_transactions = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/non_fraud_transaction.csv')
fraud_transactions = pd.read_csv('/content/drive/MyDrive/Colab Notebooks/KB AI/최종/case1_(Is_Fraud?분리)/dataset/original/chunk1/fraud_transaction.csv')
transactions = pd.concat([non_fraud_transactions, fraud_transactions], ignore_index=True)



#HeteroData 객체 생성
data = HeteroData()

#사용자 노드 추가(+feature)
data['user'].x=torch.tensor(users[['User']].values, dtype=torch.float)
data['user'].card = torch.tensor(users[['Card']].values, dtype=torch.float)
data['user'].chip = torch.tensor(users[['Use Chip']].values, dtype=torch.float)

#판매자 노드 추가(+feature)
data['merchant'].x=torch.tensor(merchants[['Merchant Name']].values, dtype=torch.float)
data['merchant'].city = torch.tensor(merchants[['Merchant City']].values, dtype=torch.float)
data['merchant'].mcc = torch.tensor(merchants[['MCC']].values, dtype=torch.float)

# 엣지 추가
user_ids = transactions['User'].values
merchant_ids = transactions['Merchant Name'].values

edge_index = torch.tensor([user_ids, merchant_ids], dtype=torch.long)
data['user', 'transaction', 'merchant'].edge_index = edge_index

# 역방향 엣지 추가
reverse_edge_index = torch.tensor([merchant_ids, user_ids], dtype=torch.long)
reverse_edge_index = reverse_edge_index[:, :edge_index.size(1)]
data['merchant', 'reverse_transaction', 'user'].edge_index = reverse_edge_index

# 엣지 특성 추가 (개수를 맞추기 위해 transactions 데이터프레임을 사용)
data['user', 'transaction', 'merchant'].amount = torch.tensor(transactions['Amount'].values[:len(edge_index[0])], dtype=torch.float)
data['user', 'transaction', 'merchant'].fraud = torch.tensor(transactions['Is Fraud?'].values[:len(edge_index[0])], dtype=torch.float)
data['user', 'transaction', 'merchant'].time = torch.tensor(transactions['Datetime_As_Float'].values[:len(edge_index[0])], dtype=torch.float)

# 역방향 엣지에도 동일한 특성 추가
data['merchant', 'reverse_transaction', 'user'].amount = torch.tensor(transactions['Amount'].values[:len(reverse_edge_index[0])], dtype=torch.float)
data['merchant', 'reverse_transaction', 'user'].fraud = torch.tensor(transactions['Is Fraud?'].values[:len(reverse_edge_index[0])], dtype=torch.float)
data['merchant', 'reverse_transaction', 'user'].time = torch.tensor(transactions['Datetime_As_Float'].values[:len(reverse_edge_index[0])], dtype=torch.float)

print(data)

from torch_geometric.loader import DataLoader
import numpy as np
from sklearn.model_selection import train_test_split

# 전체 트랜잭션 인덱스 얻기
total_indices = transactions.index

# 70% 지점 계산
# 데이터를 위에서부터 7:3 으로 나눠서 7은 학습 3은 테스트 데이터로 구성했습니다.
split_point = int(len(total_indices) * 0.7)

# 순차적으로 데이터 분할
train_indices = total_indices[:split_point]
test_indices = total_indices[split_point:]

# edge_index
edge_index = data['user', 'transaction', 'merchant'].edge_index
train_edge_index = edge_index[:, :split_point]
test_edge_index = edge_index[:, split_point:]

# 학습 데이터 구성
# Edge
# 제 생각에는 학습할 때 edge_index 만 반영이 되고 그래프 특징들이 반영이 안되는 것 같아서 edge_attr를 따로 추가해줬습니다
# 그리고 학습할 때 is_fraud 를 같이 속성으로 주면 답을 주는 거니까 안되는 것 같아서 밑에 따로 라벨링 해서 넣어줬습니다(확실x)
train_data = data.clone()
train_data['user', 'transaction', 'merchant'].edge_index = train_edge_index
train_data['user', 'transaction', 'merchant'].edge_attr = torch.tensor(transactions.loc[train_indices, ['Amount', 'Datetime_As_Float']].values, dtype=torch.float)
train_data['merchant', 'reverse_transaction', 'user'].edge_index = train_edge_index
train_data['merchant', 'reverse_transaction', 'user'].edge_attr = torch.tensor(transactions.loc[train_indices, ['Amount', 'Datetime_As_Float']].values, dtype=torch.float)

test_data = data.clone()
test_data['user', 'transaction', 'merchant'].edge_index = test_edge_index
test_data['user', 'transaction', 'merchant'].edge_attr = test_edge_attr = torch.tensor(transactions.loc[test_indices, ['Amount', 'Datetime_As_Float']].values, dtype=torch.float)
test_data['merchant', 'reverse_transaction', 'user'].edge_index = test_edge_index
test_data['merchant', 'reverse_transaction', 'user'].edge_attr = test_edge_attr = torch.tensor(transactions.loc[test_indices, ['Amount', 'Datetime_As_Float']].values, dtype=torch.float)

# User Node
# users,merchant 노드도 .x 만 반영이 되고 나머지 card, chip 등 특징들은 반영이 안되고 있는 것 같습니다.(확실x) 따로 추가는 안했습니다.
train_user_features = users.loc[train_indices]
test_user_features = users.loc[test_indices]

train_data['user'].x = torch.tensor(train_user_features[['User']].values, dtype=torch.float)
train_data['user'].card = torch.tensor(train_user_features[['Card']].values, dtype=torch.float)
train_data['user'].chip = torch.tensor(train_user_features[['Use Chip']].values, dtype=torch.float)

test_data['user'].x = torch.tensor(test_user_features[['User']].values, dtype=torch.float)
test_data['user'].card = torch.tensor(test_user_features[['Card']].values, dtype=torch.float)
test_data['user'].chip = torch.tensor(test_user_features[['Use Chip']].values, dtype=torch.float)


# Merchant Node
train_merchant_features = merchants.loc[train_indices]
test_merchant_features = merchants.loc[test_indices]

train_data['merchant'].x = torch.tensor(train_merchant_features[['Merchant Name']].values, dtype=torch.float)
train_data['merchant'].city = torch.tensor(train_merchant_features[['Merchant City']].values, dtype=torch.float)
train_data['merchant'].mcc = torch.tensor(train_merchant_features[['MCC']].values, dtype=torch.float)

train_data['merchant'].x = torch.tensor(train_merchant_features[['Merchant Name']].values, dtype=torch.float)
train_data['merchant'].city = torch.tensor(train_merchant_features[['Merchant City']].values, dtype=torch.float)
train_data['merchant'].mcc = torch.tensor(train_merchant_features[['MCC']].values, dtype=torch.float)

# 위에서 말했던 is_fraud 따로 라벨링하는 부분입니다. 밑에 학습 코드에서 넣어줍니다.
train_labels = torch.tensor(transactions.loc[train_indices, 'Is Fraud?'].values, dtype=torch.float)
test_labels = torch.tensor(transactions.loc[test_indices, 'Is Fraud?'].values, dtype=torch.float)

# 데이터 로더
train_loader = DataLoader([train_data], batch_size=1, shuffle=False)
test_loader = DataLoader([test_data], batch_size=1, shuffle=False)

# 이거는 거의 gpt 가 다해줘서 뭔지 잘 모릅니다.

import torch
import torch.nn.functional as F
from torch_geometric.nn import MessagePassing

class CustomConv(MessagePassing):
    def __init__(self, in_channels, out_channels, edge_attr_dim):
        super().__init__(aggr='mean')  # "mean" aggregation for simplicity
        self.lin = torch.nn.Linear(in_channels + edge_attr_dim, out_channels)  # Adjust linear layer

    def forward(self, x, edge_index, edge_attr):
        size = (x.size(0), x.size(0))
        return self.propagate(edge_index, size=size, x=x, edge_attr=edge_attr)

    def message(self, x_j, edge_attr):
        #print(f"x_j.shape: {x_j.shape}, edge_attr.shape: {edge_attr.shape}")
        temp = torch.cat([x_j, edge_attr], dim=-1)
        return self.lin(temp)

class GNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        edge_attr_dim = 2  # Edge attribute dimension

        # 128, 64, 32, 16, 8일때 해봤는데 그때그때 loss 줄어드는게 많이 달라서 해봐야될것같습니다

        self.conv1_user_to_merchant = CustomConv(1, 16, edge_attr_dim)
        self.conv1_merchant_to_user = CustomConv(16, 16, edge_attr_dim)
        self.conv2_user_to_merchant = CustomConv(16, 16, edge_attr_dim)
        self.conv2_merchant_to_user = CustomConv(16, 16, edge_attr_dim)
        self.linear = torch.nn.Linear(16, 1)
        '''
        # Updated layer dimensions and added more Dropout layers
        self.conv1_user_to_merchant = CustomConv(1, 32, edge_attr_dim)
        self.bn1 = torch.nn.BatchNorm1d(32)
        self.dropout1 = torch.nn.Dropout(0.3)

        self.conv1_merchant_to_user = CustomConv(32, 32, edge_attr_dim)
        self.bn2 = torch.nn.BatchNorm1d(32)
        self.dropout2 = torch.nn.Dropout(0.3)

        self.conv2_user_to_merchant = CustomConv(32, 64, edge_attr_dim)
        self.bn3 = torch.nn.BatchNorm1d(64)
        self.dropout3 = torch.nn.Dropout(0.3)

        self.conv2_merchant_to_user = CustomConv(64, 64, edge_attr_dim)
        self.bn4 = torch.nn.BatchNorm1d(64)
        self.dropout4 = torch.nn.Dropout(0.3)

        self.linear = torch.nn.Linear(64, 1)
        '''

    def forward(self, x_user, x_merchant, edge_index_user_to_merchant, edge_index_merchant_to_user, edge_attr_user_to_merchant, edge_attr_merchant_to_user):
        x_merchant = F.relu(self.conv1_user_to_merchant(x_user, edge_index_user_to_merchant, edge_attr_user_to_merchant))
        x_user = F.relu(self.conv1_merchant_to_user(x_merchant, edge_index_merchant_to_user, edge_attr_merchant_to_user))
        x_merchant = F.relu(self.conv2_user_to_merchant(x_user, edge_index_user_to_merchant, edge_attr_user_to_merchant))
        x_user = F.relu(self.conv2_merchant_to_user(x_merchant, edge_index_merchant_to_user, edge_attr_merchant_to_user))

        x_edge = self.linear(x_user[edge_index_user_to_merchant[0]]).squeeze()
        return x_edge


def initialize_weights(m):
    if isinstance(m, torch.nn.Linear):
        torch.nn.init.xavier_uniform_(m.weight)
        if m.bias is not None:
            m.bias.data.fill_(0)


# Make sure to check if out_edge.shape matches the target shape correctly

model = GNN()
model.apply(initialize_weights)

optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
#추가한거임
#scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
criterion = torch.nn.BCEWithLogitsLoss()

# 가정: train_loader와 valid_loader가 이미 정의되어 있음
for epoch in range(20):
    model.train()
    total_loss = 0
    for batch in train_loader:
        optimizer.zero_grad()

        out_edge = model(batch['user'].x,
                         batch['merchant'].x,
                         batch['user', 'transaction', 'merchant'].edge_index,
                         batch['merchant', 'reverse_transaction', 'user'].edge_index,
                         batch['user', 'transaction', 'merchant'].edge_attr,
                         batch['merchant', 'reverse_transaction', 'user'].edge_attr)

        if out_edge.shape != train_labels.shape:
            print("Error: Output shape and target shape do not match!")
            continue  # 다음 배치로 이동

        loss = criterion(out_edge, train_labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch + 1}, Loss: {total_loss / len(train_loader)}")
    #if (total_loss / len(train_loader)) < 0.4:
     #   break

