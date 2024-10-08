# -*- coding: utf-8 -*-
"""BaseLine_0814.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/17dWb89U8l2PKLMBJMZamGeXaXG2sVPb0

### 베이스라인
"""

from google.colab import drive
drive.mount('/content/drive')

import keras
from keras import ops
from keras import layers
from keras import regularizers

# Transformer Block Definition (unchanged)
class TransformerBlock(layers.Layer):
    def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1):
        super().__init__()
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = keras.Sequential(
            [
                layers.Dense(ff_dim, activation="relu"),
                layers.Dense(embed_dim),
            ]
        )
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = layers.Dropout(rate)
        self.dropout2 = layers.Dropout(rate)

    def call(self, inputs):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output)
        out1 = self.layernorm1(inputs + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output)
        return self.layernorm2(out1 + ffn_output)

# Token and Position Embedding Definition (unchanged)
class TokenAndPositionEmbedding(layers.Layer):
    def __init__(self, maxlen, vocab_size, embed_dim):
        super().__init__()
        self.token_emb = layers.Embedding(input_dim=vocab_size, output_dim=embed_dim)
        self.pos_emb = layers.Embedding(input_dim=maxlen, output_dim=embed_dim)

    def call(self, x):
        maxlen = ops.shape(x)[-1]
        positions = ops.arange(start=0, stop=maxlen, step=1)
        positions = self.pos_emb(positions)
        x = self.token_emb(x)
        return x + positions

# Hyperparameters (can be adjusted)
input_shape = (128, 128, 3)  # Example shape of images (128x128 RGB images)
vocab_size = 20000  # Not used for images, placeholder
maxlen = 200  # Not used for images, placeholder
embed_dim = 64  # Embedding size for each token
num_heads = 4  # Number of attention heads
ff_dim = 128  # Hidden layer size in feed forward network inside transformer
dropout_rate = 0.2  # Dropout rate
l2_reg = 0.01  # L2 regularization strength
learning_rate = 1e-4  # Learning rate

"""#### 일단 이미지 손으로 올리기"""

import os
import numpy as np
from PIL import Image

# 이미지 크기 설정 (모델의 입력 크기와 일치해야 함)
img_height = 128
img_width = 128

# 이미지 로딩 함수
def load_images_from_directory(directory, img_height, img_width, label):
    images = []
    labels = []
    for img_file in os.listdir(directory):
        img_path = os.path.join(directory, img_file)
        try:
            img = Image.open(img_path).convert('RGB')
            img = img.resize((img_width, img_height))
            img_array = np.array(img)
            images.append(img_array)
            labels.append(label)  # Given label (0 or 1)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
    return np.array(images), np.array(labels)

# 데이터 디렉토리 설정
train_dir_mental = 'train/mental'
train_dir_non_mental = 'train/non mental'
val_dir_mental = 'val/mental'
val_dir_non_mental = 'val/non mental'

# 훈련 데이터셋 로드
x_train_mental, y_train_mental = load_images_from_directory(train_dir_mental, img_height, img_width, label=1)
x_train_non_mental, y_train_non_mental = load_images_from_directory(train_dir_non_mental, img_height, img_width, label=0)

# 검증 데이터셋 로드
x_val_mental, y_val_mental = load_images_from_directory(val_dir_mental, img_height, img_width, label=1)
x_val_non_mental, y_val_non_mental = load_images_from_directory(val_dir_non_mental, img_height, img_width, label=0)

# np.concatenate를 사용하기 전에 각 x_train_mental, x_train_non_mental이 4차원 배열인지 확인
print(f"x_train_mental shape: {x_train_mental.shape}")  # Should be (num_images, img_height, img_width, 3)
print(f"x_train_non_mental shape: {x_train_non_mental.shape}")  # Should be (num_images, img_height, img_width, 3)

# 데이터셋 합치기
x_train = np.concatenate((x_train_mental, x_train_non_mental), axis=0)
y_train = np.concatenate((y_train_mental, y_train_non_mental), axis=0)
x_val = np.concatenate((x_val_mental, x_val_non_mental), axis=0)
y_val = np.concatenate((y_val_mental, y_val_non_mental), axis=0)

# 데이터를 섞기 (optional)
train_indices = np.random.permutation(len(x_train))
x_train = x_train[train_indices]
y_train = y_train[train_indices]

val_indices = np.random.permutation(len(x_val))
x_val = x_val[val_indices]
y_val = y_val[val_indices]

"""#### 이어서"""

# Model Definition
inputs = layers.Input(shape=input_shape)

# Add a few convolutional layers for image feature extraction
x = layers.Conv2D(32, kernel_size=(3, 3), activation='relu')(inputs)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)
x = layers.Conv2D(64, kernel_size=(3, 3), activation='relu')(x)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)
x = layers.Conv2D(128, kernel_size=(3, 3), activation='relu')(x)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)

# Flatten or GlobalAveragePooling2D to reduce to 1D tensor
x = layers.GlobalAveragePooling2D()(x)

# Adding multiple Transformer Blocks
for _ in range(2):  # Adding 2 transformer blocks for better representation learning
    x = layers.Reshape((1, -1))(x)  # Reshape to (1, feature_dim)
    transformer_block = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)(x, x)
    x = layers.Reshape((-1,))(transformer_block)  # Flatten again

# Dense layers with L2 regularization
x = layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(l2_reg))(x)
x = layers.Dropout(dropout_rate)(x)
outputs = layers.Dense(2, activation="softmax")(x)

# Model compilation with a different optimizer and learning rate
model = keras.Model(inputs=inputs, outputs=outputs)
optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
model.compile(optimizer=optimizer, loss="sparse_categorical_crossentropy", metrics=["accuracy"])

# Model training
history = model.fit(
    x_train, y_train, batch_size=32, epochs=100, validation_data=(x_val, y_val)
)

# 1. 모델 평가 (validation set 사용)
loss, accuracy = model.evaluate(x_val, y_val, verbose=2)
print(f"Validation Loss: {loss}")
print(f"Validation Accuracy: {accuracy}")

# 2. Confusion Matrix 및 Classification Report 출력
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# 모델을 사용하여 예측값 생성
y_pred = model.predict(x_val)
y_pred_classes = np.argmax(y_pred, axis=1)  # 확률을 클래스 레이블로 변환

# 혼동 행렬 출력
conf_matrix = confusion_matrix(y_val, y_pred_classes)
print("Confusion Matrix")
print(conf_matrix)

# 분류 보고서 출력
class_report = classification_report(y_val, y_pred_classes)
print("Classification Report")
print(class_report)

# 3. 학습 과정 시각화 (손실 및 정확도 그래프)
import matplotlib.pyplot as plt

# 손실 그래프
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

# 정확도 그래프
plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Accuracy Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.show()

"""### 하이퍼파라미터 파인튜닝"""

# Hyperparameters (can be adjusted)
input_shape = (128, 128, 3)  # Example shape of images (128x128 RGB images)
vocab_size = 20000  # Not used for images, placeholder
maxlen = 200  # Not used for images, placeholder
embed_dim = 64  # Embedding size for each token
num_heads = 4  # Number of attention heads
ff_dim = 128  # Hidden layer size in feed forward network inside transformer
dropout_rate = 0.3  # Dropout rate 높임(0.2)
l2_reg = 0.01  # L2 regularization strength
learning_rate = 1e-5  # Learning rate 낮춤(1e-4)

# 모델 재정의 및 컴파일
inputs = layers.Input(shape=input_shape)
x = layers.Conv2D(32, kernel_size=(3, 3), activation='relu')(inputs)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)
x = layers.Conv2D(64, kernel_size=(3, 3), activation='relu')(x)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)
x = layers.Conv2D(128, kernel_size=(3, 3), activation='relu')(x)
x = layers.MaxPooling2D(pool_size=(2, 2))(x)
x = layers.GlobalAveragePooling2D()(x)

for _ in range(2):
    x = layers.Reshape((1, -1))(x)
    transformer_block = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)(x, x)
    x = layers.Reshape((-1,))(transformer_block)

x = layers.Dense(64, activation="relu", kernel_regularizer=regularizers.l2(l2_reg))(x)
x = layers.Dropout(dropout_rate)(x)
outputs = layers.Dense(2, activation="softmax")(x)

model = keras.Model(inputs=inputs, outputs=outputs)
optimizer = keras.optimizers.Adam(learning_rate=learning_rate)
model.compile(optimizer=optimizer, loss="sparse_categorical_crossentropy", metrics=["accuracy"])

# 학습 및 평가
history = model.fit(x_train, y_train, batch_size=32, epochs=100, validation_data=(x_val, y_val))
loss, accuracy = model.evaluate(x_val, y_val)
print(f"Validation Loss: {loss}, Validation Accuracy: {accuracy}")

# 1. 모델 평가 (validation set 사용)
loss, accuracy = model.evaluate(x_val, y_val, verbose=2)
print(f"Validation Loss: {loss}")
print(f"Validation Accuracy: {accuracy}")

# 2. Confusion Matrix 및 Classification Report 출력
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# 3. 학습 과정 시각화 (손실 및 정확도 그래프)
import matplotlib.pyplot as plt

# 손실 그래프
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

# 정확도 그래프
plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Accuracy Over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.show()