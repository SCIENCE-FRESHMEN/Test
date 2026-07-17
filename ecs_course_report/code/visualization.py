"""Visualize only synthetic outputs created by this project."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import csv

ROOT=Path(__file__).resolve().parent
def main():
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    data=np.load(ROOT/'synthetic_data'/'tb_mri_synthetic.npz'); x,t,c,d=data['x'],data['t'],data['concentration'],data['diffusion_map']
    fig,ax=plt.subplots(1,2,figsize=(8,3))
    ax[0].imshow(d,aspect='auto',cmap='viridis'); ax[0].set(title='Synthetic D map',xlabel='distance',ylabel='time')
    for i in (0,len(t)//2,-1): ax[1].plot(x,c[i],label=f't={t[i]:.2f}')
    ax[1].set(title='Synthetic TB-MRI tracer',xlabel='normalized distance',ylabel='concentration'); ax[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out/'ecs_parameter_heatmap_and_series.png',dpi=160)
    result_path = out/'ablation_results.csv'
    if result_path.exists():
        with result_path.open(encoding='utf-8') as handle: rows=list(csv.DictReader(handle))
        names=list(dict.fromkeys(row['configuration'] for row in rows))
        means=[np.mean([float(row['d_relative_error']) for row in rows if row['configuration']==name]) for name in names]
        stds=[np.std([float(row['d_relative_error']) for row in rows if row['configuration']==name]) for name in names]
        fig,ax=plt.subplots(figsize=(7,3.4)); ax.bar(names,means,yerr=stds,capsize=3,color='#5B8FF9')
        ax.set(ylabel='relative error of synthetic D',title='Synthetic PINN ablation (mean +/- SD, n=3)'); ax.tick_params(axis='x',rotation=22)
        fig.tight_layout(); fig.savefig(out/'ablation_results.png',dpi=160)
    else:
        print('No ablation_results.csv found; run ablation_experiment.py first.')
if __name__=='__main__': main()
