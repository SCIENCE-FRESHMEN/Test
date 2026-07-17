"""Lightweight PINN demonstration for a 1-D ECS tracer inverse problem.

It trains only on synthetic concentration data created inside this file.  The
estimated parameters are demonstration outputs, not measurements of brain ECS.
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import torch
from torch import nn

torch.manual_seed(7)
np.random.seed(7)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(2, 48), nn.Tanh(), nn.Linear(48, 48), nn.Tanh(), nn.Linear(48, 1))
    def forward(self, z): return self.net(z)

def analytic(x, t, d, v, alpha=1.0):
    """Gaussian tracer plume for C_t = D C_xx - v C_x on an open 1-D domain."""
    width = 0.03 + 2.0 * d * t
    return alpha * torch.exp(-((x - 0.25 - v*t)**2) / (2*width)) * torch.sqrt(0.03 / width)

def deriv(y, x): return torch.autograd.grad(y, x, torch.ones_like(y), create_graph=True)[0]

def main(epochs=1200):
    true_d, true_v, true_alpha = 0.018, 0.12, 0.20  # dimensionless synthetic ground truth
    model = MLP().to(DEVICE)
    log_d = nn.Parameter(torch.tensor([-3.5], device=DEVICE))
    velocity = nn.Parameter(torch.tensor([0.02], device=DEVICE))
    log_alpha = nn.Parameter(torch.tensor([-1.4], device=DEVICE))
    opt = torch.optim.Adam(list(model.parameters()) + [log_d, velocity, log_alpha], lr=2e-3)
    x_data = torch.rand(180, 1, device=DEVICE) * 0.9 + 0.05
    t_data = torch.rand(180, 1, device=DEVICE) * 0.8 + 0.05
    c_data = analytic(x_data, t_data, true_d, true_v, true_alpha).detach() + 0.01*torch.randn_like(x_data)
    for epoch in range(epochs):
        x_f = torch.rand(600, 1, device=DEVICE, requires_grad=True)
        t_f = torch.rand(600, 1, device=DEVICE, requires_grad=True)
        pred = model(torch.cat([x_f, t_f], 1))
        c_t = deriv(pred, t_f)
        c_x = deriv(pred, x_f)
        c_xx = deriv(c_x, x_f)
        d = torch.exp(log_d)
        physics = c_t - d*c_xx + velocity*c_x
        data_loss = ((model(torch.cat([x_data, t_data], 1)) - c_data)**2).mean()
        initial = model(torch.cat([x_f, torch.zeros_like(t_f)], 1))
        initial_loss = ((initial - analytic(x_f, torch.zeros_like(t_f), true_d, true_v, true_alpha))**2).mean()
        loss = data_loss + physics.square().mean() + initial_loss
        opt.zero_grad(); loss.backward(); opt.step()
        if epoch % 300 == 0: print(f"epoch={epoch:4d} loss={loss.item():.4e} D={d.item():.4f} v={velocity.item():.4f} alpha={torch.exp(log_alpha).item():.3f}")
    x = torch.linspace(0, 1, 200, device=DEVICE)[:, None]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    for time in (0.2, 0.5, 0.8):
        t = torch.full_like(x, time)
        with torch.no_grad(): y = model(torch.cat([x, t], 1)).cpu().numpy()
        ax.plot(x.cpu(), y, label=f"PINN t={time}")
    ax.set(xlabel="normalized distance", ylabel="tracer concentration", title="Synthetic ECS PINN result")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / "pinn_tracer_profiles.png", dpi=160)
    print(f"Synthetic estimate: D={torch.exp(log_d).item():.4f}, v={velocity.item():.4f}, alpha={torch.exp(log_alpha).item():.3f}")

if __name__ == "__main__": main()
