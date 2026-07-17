"""Generate synthetic TB-MRI tracer arrays and ECS microscopy-like slices.

No animal, human, or public image is read.  Parameters are dimensionless
teaching settings derived from the ECS advection-diffusion formulation.
"""
from pathlib import Path
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parent

def tracer_series(nx=80, nt=24, diffusion=0.018, velocity=0.12, alpha=0.20, noise_std=0.015):
    """Return [time, distance] synthetic concentration with region-dependent D."""
    x = np.linspace(0, 1, nx); t = np.linspace(0.02, 0.9, nt)
    xx, tt = np.meshgrid(x, t)
    d_map = diffusion * np.where(xx < 0.5, 1.0, 0.72)  # two synthetic regions
    width = 0.03 + 2*d_map*tt
    c = alpha*np.exp(-(xx-0.25-velocity*tt)**2/(2*width))*np.sqrt(0.03/width)
    return x, t, np.clip(c + noise_std*np.random.randn(*c.shape), 0, None), d_map

def ecs_slice(size=64):
    """Create dark cell-like ellipses; remaining bright pixels are synthetic ECS."""
    image = np.full((size,size), .72, np.float32); cells = np.zeros_like(image)
    for _ in range(np.random.randint(5,10)):
        center = tuple(np.random.randint(6,size-6,2)); axes = tuple(np.random.randint(4,12,2))
        angle = float(np.random.randint(180))
        cv2.ellipse(image, center, axes, angle, 0, 360, .18, -1)
        cv2.ellipse(cells, center, axes, angle, 0, 360, 1, -1)
    return np.clip(image+.08*np.random.randn(size,size),0,1).astype(np.float32), 1-cells

def main():
    np.random.seed(20260718); out=ROOT/'synthetic_data'; out.mkdir(exist_ok=True)
    x,t,c,d=tracer_series(); np.savez(out/'tb_mri_synthetic.npz', x=x,t=t,concentration=c,diffusion_map=d)
    images,masks=zip(*(ecs_slice() for _ in range(120)))
    np.savez(out/'ecs_slices_synthetic.npz', images=np.stack(images), masks=np.stack(masks))
    print(f'Wrote synthetic datasets to {out}')

if __name__ == '__main__': main()
