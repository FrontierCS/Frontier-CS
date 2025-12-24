import os
import math
import time
from typing import Optional, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class DiagonalQDA(nn.Module):
    def __init__(self, mean0: torch.Tensor, inv_var: torch.Tensor, a: torch.Tensor, const: torch.Tensor):
        super().__init__()
        self.register_buffer("mean0", mean0)
        self.register_buffer("inv_var", inv_var)  # [C, D]
        self.register_buffer("a", a)              # [C, D] = mu * inv_var
        self.register_buffer("const", const)      # [C]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=self.mean0.dtype)
        x = x - self.mean0
        x2 = x * x
        logits = x.matmul(self.a.t()) - 0.5 * x2.matmul(self.inv_var.t()) + self.const
        return logits


class StandardizedResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        mean0: torch.Tensor,
        std0: torch.Tensor,
        width: int = 512,
        bottleneck: int = 256,
        n_blocks: int = 2,
        dropout: float = 0.0,
    ):
        super().__init__()
        self.register_buffer("mean0", mean0)
        self.register_buffer("inv_std0", (1.0 / std0).clamp(max=1e6))

        self.stem = nn.Sequential(
            nn.Linear(input_dim, width, bias=True),
            nn.GELU(),
            nn.LayerNorm(width),
        )

        blocks = []
        for _ in range(n_blocks):
            blocks.append(_ResBlock(width, bottleneck, dropout))
        self.blocks = nn.Sequential(*blocks)

        self.head = nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, num_classes, bias=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=self.mean0.dtype)
        x = (x - self.mean0) * self.inv_std0
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head(x)
        return x


class _ResBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, bottleneck, bias=True)
        self.fc2 = nn.Linear(bottleneck, width, bias=True)
        self.dropout = nn.Dropout(dropout) if dropout and dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = F.gelu(self.fc1(h))
        h = self.fc2(h)
        h = self.dropout(h)
        return x + h


class Solution:
    def __init__(self):
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

    @staticmethod
    def _param_count(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    @staticmethod
    def _collect_from_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
        xs = []
        ys = []
        for xb, yb in loader:
            if xb.dim() != 2:
                xb = xb.view(xb.size(0), -1)
            xs.append(xb.detach().cpu().to(torch.float32))
            ys.append(yb.detach().cpu().to(torch.long))
        x = torch.cat(xs, dim=0) if xs else torch.empty(0)
        y = torch.cat(ys, dim=0) if ys else torch.empty(0, dtype=torch.long)
        return x, y

    @staticmethod
    def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, device: torch.device, batch_size: int = 512) -> float:
        if x.numel() == 0:
            return 0.0
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for i in range(0, x.size(0), batch_size):
                xb = x[i : i + batch_size].to(device)
                yb = y[i : i + batch_size].to(device)
                logits = model(xb)
                pred = logits.argmax(dim=1)
                correct += (pred == yb).sum().item()
                total += yb.numel()
        return correct / max(1, total)

    @staticmethod
    def _fit_qda(x: torch.Tensor, y: torch.Tensor, num_classes: int) -> DiagonalQDA:
        # Use float64 for stable statistics, then store float32 buffers
        x64 = x.to(torch.float64)
        y64 = y.to(torch.long)

        n, d = x64.shape
        mean0 = x64.mean(dim=0)
        xc = x64 - mean0

        counts = torch.bincount(y64, minlength=num_classes).to(torch.float64).clamp_min(1.0)  # [C]
        sums = torch.zeros((num_classes, d), dtype=torch.float64)
        sums.index_add_(0, y64, xc)
        mu = sums / counts[:, None]  # [C, D]

        mu_y = mu[y64]  # [N, D]
        diff = xc - mu_y
        var_sums = torch.zeros((num_classes, d), dtype=torch.float64)
        var_sums.index_add_(0, y64, diff * diff)
        var_c = var_sums / counts[:, None]  # [C, D]

        global_var = (var_sums.sum(dim=0) / max(1.0, float(n))).clamp_min(1e-12)  # [D]
        shrink = 0.5
        var_c = (1.0 - shrink) * var_c + shrink * global_var[None, :]

        eps = (global_var.mean() * 1e-4).item()
        if not math.isfinite(eps) or eps <= 0.0:
            eps = 1e-6
        var_c = (var_c + eps).clamp_min(eps)

        inv_var = 1.0 / var_c  # [C, D]
        logdet = torch.log(var_c).sum(dim=1)  # [C]
        prior = (counts / counts.sum()).clamp_min(1e-12)
        const = -0.5 * ((mu * mu * inv_var).sum(dim=1) + logdet) + torch.log(prior)

        model = DiagonalQDA(
            mean0=mean0.to(torch.float32),
            inv_var=inv_var.to(torch.float32),
            a=(mu * inv_var).to(torch.float32),
            const=const.to(torch.float32),
        )
        return model

    @staticmethod
    def _compute_mean_std(x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x64 = x.to(torch.float64)
        mean0 = x64.mean(dim=0)
        var0 = (x64 - mean0).pow(2).mean(dim=0)
        std0 = torch.sqrt(var0.clamp_min(1e-12))
        std0 = std0.clamp_min(1e-6)
        return mean0.to(torch.float32), std0.to(torch.float32)

    @staticmethod
    def _train_mlp(
        xtr: torch.Tensor,
        ytr: torch.Tensor,
        xva: torch.Tensor,
        yva: torch.Tensor,
        input_dim: int,
        num_classes: int,
        device: torch.device,
        param_limit: int,
        time_budget_s: float = 60.0,
    ) -> nn.Module:
        mean0, std0 = Solution._compute_mean_std(xtr)

        width = 512
        bottleneck = 256
        n_blocks = 2
        dropout = 0.0

        model = StandardizedResidualMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            mean0=mean0,
            std0=std0,
            width=width,
            bottleneck=bottleneck,
            n_blocks=n_blocks,
            dropout=dropout,
        ).to(device)

        # Ensure under parameter limit (if not, reduce width)
        def rebuild_if_needed():
            nonlocal model, width, bottleneck, n_blocks
            while Solution._param_count(model) > param_limit and width > 128:
                width = max(128, width - 64)
                bottleneck = max(64, width // 2)
                n_blocks = min(n_blocks, 2)
                model = StandardizedResidualMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    mean0=mean0,
                    std0=std0,
                    width=width,
                    bottleneck=bottleneck,
                    n_blocks=n_blocks,
                    dropout=dropout,
                ).to(device)

        rebuild_if_needed()

        # Full in-memory training with minibatches
        n = xtr.size(0)
        batch_size = 256 if n >= 256 else max(32, n)
        max_epochs = 120
        lr = 3e-3
        weight_decay = 2e-4
        label_smoothing = 0.06

        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max_epochs)

        best_acc = -1.0
        best_state = None
        patience = 18
        bad = 0

        start_t = time.time()
        xtr_dev = xtr.to(device)
        ytr_dev = ytr.to(device)
        xva_dev = xva.to(device) if xva.numel() else None
        yva_dev = yva.to(device) if yva.numel() else None

        for epoch in range(max_epochs):
            if time.time() - start_t > time_budget_s:
                break

            model.train()
            perm = torch.randperm(n, device=device)
            total_loss = 0.0
            steps = 0

            for i in range(0, n, batch_size):
                idx = perm[i : i + batch_size]
                xb = xtr_dev[idx]
                yb = ytr_dev[idx]

                opt.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()

                total_loss += float(loss.item())
                steps += 1

            scheduler.step()

            if xva_dev is not None:
                model.eval()
                with torch.no_grad():
                    logits = model(xva_dev)
                    pred = logits.argmax(dim=1)
                    acc = (pred == yva_dev).float().mean().item()
            else:
                acc = 0.0

            if acc > best_acc + 1e-4:
                best_acc = acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
            model.to(device)

        model.eval()
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        metadata = metadata or {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        baseline = float(metadata.get("baseline_accuracy", 0.85))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        xtr, ytr = self._collect_from_loader(train_loader)
        xva, yva = self._collect_from_loader(val_loader) if val_loader is not None else (torch.empty(0, input_dim), torch.empty(0, dtype=torch.long))

        # Primary: fast closed-form-ish diagonal QDA classifier
        qda = self._fit_qda(xtr, ytr, num_classes).to(device)
        qda_acc = self._accuracy(qda, xva, yva, device=device) if xva.numel() else 0.0

        # If QDA is good enough, return it (0 trainable params, very fast)
        if qda_acc >= max(baseline + 0.01, 0.86) or xva.numel() == 0:
            qda.eval()
            return qda

        # Fallback: train a small residual MLP (still under parameter limit)
        mlp = self._train_mlp(
            xtr=xtr,
            ytr=ytr,
            xva=xva,
            yva=yva,
            input_dim=input_dim,
            num_classes=num_classes,
            device=device,
            param_limit=param_limit,
            time_budget_s=75.0,
        )

        # Safety: if somehow exceeds limit, fall back to QDA
        if self._param_count(mlp) > param_limit:
            qda.eval()
            return qda

        mlp.eval()
        return mlp
