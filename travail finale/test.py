import torch

print("Version PyTorch :", torch.__version__)
print("CUDA disponible :", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU :", torch.cuda.get_device_name(0))
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

# créer deux matrices
a = torch.rand(3, 3).to(device)
b = torch.rand(3, 3).to(device)

# multiplication
c = torch.matmul(a, b)

print("Device utilisé :", device)
print("Résultat :")
print(c)