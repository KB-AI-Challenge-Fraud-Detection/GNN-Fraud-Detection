# -*- coding: utf-8 -*-
"""train_ver1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Nbt9vNtuSmITkM5iGmaS9UwUiSOJpRQN
"""

!pip install torch-geometric

from google.colab import drive
drive.mount('/content/drive')

import pandas as pd
import torch
from torch_geometric.data import HeteroData
from torch_geometric.loader import DataLoader
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv
import torch.optim as optim

# 데이터 로드 및 전처리
users = pd.read_csv('/chunk1/non_fraud_user.csv')
users_fraud = pd.read_csv('/chunk1/fraud_user.csv')
users = pd.concat([users, users_fraud], ignore_index=True)

merchants = pd.read_csv('/chunk1/non_fraud_merchant.csv')
merchants_fraud = pd.read_csv('/chunk1/fraud_merchant.csv')
merchants = pd.concat([merchants, merchants_fraud], ignore_index=True)

non_fraud_transactions = pd.read_csv('/chunk1/non_fraud_transaction.csv')
fraud_transactions = pd.read_csv('/chunk1/fraud_transaction.csv')
all_transactions = pd.concat([non_fraud_transactions, fraud_transactions], ignore_index=True)

fraud_count = all_transactions[all_transactions['Is Fraud?'] == 1].shape[0]
# HeteroData 객체 생성
data = HeteroData()

# 사용자 노드 추가 (+ feature)
data['user'].x = torch.tensor(users[['User']].values, dtype=torch.float)
data['user'].card = torch.tensor(users[['Card']].values, dtype=torch.float)
data['user'].chip = torch.tensor(users[['Use Chip']].values, dtype=torch.float)

# 판매자 노드 추가 (+ feature)
data['merchant'].x = torch.tensor(merchants[['Merchant Name']].values, dtype=torch.float)
data['merchant'].city = torch.tensor(merchants[['Merchant City']].values, dtype=torch.float)
data['merchant'].mcc = torch.tensor(merchants[['MCC']].values, dtype=torch.float)

# 엣지 추가
user_ids = all_transactions['User'].values
merchant_ids = all_transactions['Merchant Name'].values
edge_index = torch.tensor([user_ids, merchant_ids], dtype=torch.long)
data['user', 'transaction', 'merchant'].edge_index = edge_index

# 엣지 특성 및 레이블 추가
data['user', 'transaction', 'merchant'].amount = torch.tensor(all_transactions['Amount'].values, dtype=torch.float)
data['user', 'transaction', 'merchant'].time = torch.tensor(all_transactions['Datetime_As_Float'].values, dtype=torch.float)
data['user', 'transaction', 'merchant'].fraud = torch.tensor(all_transactions['Is Fraud?'].values, dtype=torch.float)
print(data)

import torch.nn.functional as F
from torch_geometric.nn import SAGEConv

class GNN(torch.nn.Module):
    def __init__(self, in_channels_user, in_channels_merchant, hidden_channels, out_channels):
        super(GNN, self).__init__()
        self.conv1 = SAGEConv((in_channels_user, in_channels_merchant), hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        self.linear = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x_user, x_merchant, edge_index_user_to_merchant):
        # 사용자 -> 상점 방향으로 메시지 전달
        x_merchant = self.conv1((x_user, x_merchant), edge_index_user_to_merchant)
        x_merchant = F.relu(x_merchant)

        # 상점 -> 사용자 방향으로 메시지 전달
        x_user = self.conv2(x_merchant, edge_index_user_to_merchant.flip([0]))  # Reverse edge direction
        x_user = F.relu(x_user)

        # 엣지의 최종 임베딩을 얻기 위해 선형 레이어를 사용하여 예측값을 얻음
        edge_embedding = self.linear(x_user)

        return edge_embedding

# 모델 초기화
in_channels_user = data['user'].x.shape[1]  # 사용자 노드의 입력 채널 수
in_channels_merchant = data['merchant'].x.shape[1]  # 판매자 노드의 입력 채널 수
hidden_channels = 64  # 임의로 설정된 숨겨진 채널 크기
out_channels = 1  # 이진 분류를 위한 출력 채널 수

model = GNN(in_channels_user, in_channels_merchant, hidden_channels, out_channels)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.BCEWithLogitsLoss()

# 학습 루프
epochs = 20
for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()

    # 모델의 출력 예측값 계산
    out = model(
        data['user'].x,
        data['merchant'].x,
        data['user', 'transaction', 'merchant'].edge_index
    )

    # 레이블 (Is Fraud?)
    label = data['user', 'transaction', 'merchant'].fraud

    # 손실 계산
    loss = criterion(out.squeeze(), label)

    # 역전파 및 최적화
    loss.backward()
    optimizer.step()

    print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')

model.eval()
with torch.no_grad():
    out = model(
        data['user'].x,
        data['merchant'].x,
        data['user', 'transaction', 'merchant'].edge_index,
    )

    # 예측 확률 계산
    predictions = torch.sigmoid(out).squeeze()

    # 임계값을 넘는 경우를 이상치(사기 거래)로 간주
    threshold = 0.001  # 예: 0.5 이상인 경우 사기 거래로 간주
    anomalies = (predictions > threshold).float()

    print(f"Detected {anomalies.sum().item()} potential fraudulent transactions out of {len(anomalies)}")

