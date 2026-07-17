"""Shape-aware dual-branch ECS segmentation demo using generated toy images.

This is an educational ECS-Net-style baseline: it does not claim to reproduce a
published architecture or use a biological EM dataset.
"""
from pathlib import Path
import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

torch.manual_seed(9); np.random.seed(9)
OUT = Path(__file__).resolve().parent / "results"; OUT.mkdir(exist_ok=True)

def sample(n=64):
    image = np.zeros((n,n), np.float32); mask = np.zeros((n,n), np.float32)
    # Bright narrow corridors mimic ECS; dark ellipses mimic cellular profiles.
    image[:] = .72
    for _ in range(np.random.randint(5, 10)):
        c = tuple(np.random.randint(5, n-5, 2)); axes = tuple(np.random.randint(4, 12, 2))
        cv2.ellipse(image, c, axes, float(np.random.randint(180)), 0, 360, .18, -1)
        cv2.ellipse(mask, c, axes, float(np.random.randint(180)), 0, 360, 1, -1)
    ecs = 1-mask
    image += .08*np.random.randn(n,n).astype(np.float32)
    return np.clip(image,0,1), ecs

class ToyECS(Dataset):
    def __init__(self, count): self.items=[sample() for _ in range(count)]
    def __len__(self): return len(self.items)
    def __getitem__(self, i):
        a,b=self.items[i]; return torch.tensor(a)[None], torch.tensor(b)[None]

class ECSDualNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.ReLU(),nn.Conv2d(16,16,3,padding=1),nn.ReLU())
        self.mask=nn.Conv2d(16,1,1); self.edge=nn.Conv2d(16,1,1)
    def forward(self,x):
        f=self.encoder(x); return self.mask(f),self.edge(f)

def dice(logits, y):
    p=torch.sigmoid(logits); return 1-(2*(p*y).sum()+1)/((p+y).sum()+1)

def contrastive_feature_loss(features, mask):
    """Lightweight contrastive surrogate: separate mean ECS/cell feature vectors."""
    ecs = (features * mask).sum((0,2,3)) / (mask.sum((0,2,3))+1e-6)
    cell_mask = 1-mask
    cell = (features * cell_mask).sum((0,2,3)) / (cell_mask.sum((0,2,3))+1e-6)
    return torch.exp(-torch.norm(ecs-cell))

def main(epochs=10):
    device="cuda" if torch.cuda.is_available() else "cpu"; model=ECSDualNet().to(device)
    loader=DataLoader(ToyECS(96),batch_size=12,shuffle=True); opt=torch.optim.Adam(model.parameters(),1e-3)
    bce=nn.BCEWithLogitsLoss()
    for e in range(epochs):
        for x,y in loader:
            x,y=x.to(device),y.to(device)
            edge=(torch.abs(y[:,:,1:]-y[:,:,:-1])>0).float(); edge=torch.nn.functional.pad(edge,(0,0,0,1))
            seg,shape=model(x); features=model.encoder(x)
            loss=bce(seg,y)+dice(seg,y)+0.3*bce(shape,edge)+0.05*contrastive_feature_loss(features,y)
            opt.zero_grad();loss.backward();opt.step()
        print(f"epoch={e+1:02d} loss={loss.item():.4f}")
    x,y=ToyECS(1)[0];
    with torch.no_grad(): p=torch.sigmoid(model(x[None].to(device))[0])[0,0].cpu().numpy()
    fig,ax=plt.subplots(1,3,figsize=(8,2.6))
    for a,z,title in zip(ax,[x[0],y[0],p],["synthetic slice","ECS label","prediction"]): a.imshow(z,cmap="gray");a.set_title(title);a.axis("off")
    fig.tight_layout();fig.savefig(OUT/"ecs_net_segmentation.png",dpi=160)

if __name__ == "__main__": main()
