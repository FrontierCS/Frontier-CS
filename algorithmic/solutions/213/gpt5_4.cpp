#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir; // dir: 0 left, 1 right
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<Op> ops;
    auto add_op = [&](int l, int r, int dir) {
        ops.push_back({l, r, dir});
    };

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int x = max(2, min(n-1, (int)sqrt((double)n) + 1));
    vector<int> pos(n+1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    auto rotate_seg = [&](int l, int dir) {
        int r = l + x - 1;
        if (dir == 0) {
            int tmp = a[l];
            for (int i = l; i < r; ++i) {
                a[i] = a[i+1];
                pos[a[i]] = i;
            }
            a[r] = tmp;
            pos[tmp] = r;
        } else {
            int tmp = a[r];
            for (int i = r; i > l; --i) {
                a[i] = a[i-1];
                pos[a[i]] = i;
            }
            a[l] = tmp;
            pos[tmp] = l;
        }
        add_op(l, l + x - 1, dir);
    };

    // Phase 1: place positions 1..n-x+1
    int limit1 = n - x + 1;
    for (int i = 1; i <= max(0, limit1); ++i) {
        int p = pos[i];
        while (p - i >= x - 1) {
            rotate_seg(p - x + 1, 1);
            p -= (x - 1);
        }
        while (p > i) {
            rotate_seg(i, 0);
            --p;
        }
    }

    // Phase 2: sort the union region U = [n-x, n] using only A=[n-x+1..n], B=[n-x..n-1]
    if (x >= 2) {
        int L0 = n - x;
        if (L0 < 1) L0 = 1; // guard, though x<=n-1 so L0>=1
        int R0 = n;
        int Astart = max(1, n - x + 1);
        int Bstart = max(1, n - x);

        auto get_sub = [&]() {
            vector<int> b;
            for (int i = L0; i <= R0; ++i) b.push_back(a[i]);
            return b;
        };
        auto inv_count = [&](const vector<int>& b) -> long long {
            long long inv = 0;
            int m = (int)b.size();
            for (int i = 0; i < m; ++i) {
                for (int j = i+1; j < m; ++j) {
                    if (b[i] > b[j]) ++inv;
                }
            }
            return inv;
        };
        auto is_sorted_sub = [&]() {
            for (int i = L0; i < R0; ++i) if (a[i] > a[i+1]) return false;
            return true;
        };
        auto sim_rotate = [&](const vector<int>& b, int start_in_global, int dir) {
            // start_in_global is l, we need portion intersecting [L0..R0]
            // since we only simulate for A or B which are fully inside [L0..R0] or touching edges,
            // we'll map indices relative to L0
            vector<int> c = b;
            int l = start_in_global;
            int r = l + x - 1;
            // copy to temp
            int ll = max(l, L0), rr = min(r, R0);
            // but rotating a contiguous block [l..r] - strictly within [1..n]
            // We'll perform rotation on c for indices [l..r] relative to global.
            if (l < L0 || r > R0) {
                // should not happen for A/B in our phase, but guard by ignoring
                return c;
            }
            if (dir == 0) {
                int tmp = c[l - L0];
                for (int i = l; i < r; ++i) c[i - L0] = c[i + 1 - L0];
                c[r - L0] = tmp;
            } else {
                int tmp = c[r - L0];
                for (int i = r; i > l; --i) c[i - L0] = c[i - 1 - L0];
                c[l - L0] = tmp;
            }
            return c;
        };

        long long curInv = inv_count(get_sub());
        int maxIter = 200 * x * x + 5;
        int iter = 0;
        while (!is_sorted_sub() && iter < maxIter) {
            ++iter;
            vector<int> base = get_sub();
            long long bestInv = LLONG_MAX;
            int bestOp = -1; // 0: LA,1:RA,2:LB,3:RB
            vector<int> cand;
            // Try LA
            if (Astart >= L0 && Astart + x - 1 <= R0) {
                cand = sim_rotate(base, Astart, 0);
                long long inv = inv_count(cand);
                if (inv < bestInv) { bestInv = inv; bestOp = 0; }
            }
            // RA
            if (Astart >= L0 && Astart + x - 1 <= R0) {
                cand = sim_rotate(base, Astart, 1);
                long long inv = inv_count(cand);
                if (inv < bestInv) { bestInv = inv; bestOp = 1; }
            }
            // LB
            if (Bstart >= L0 && Bstart + x - 1 <= R0) {
                cand = sim_rotate(base, Bstart, 0);
                long long inv = inv_count(cand);
                if (inv < bestInv) { bestInv = inv; bestOp = 2; }
            }
            // RB
            if (Bstart >= L0 && Bstart + x - 1 <= R0) {
                cand = sim_rotate(base, Bstart, 1);
                long long inv = inv_count(cand);
                if (inv < bestInv) { bestInv = inv; bestOp = 3; }
            }
            if (bestInv <= curInv) {
                // apply best
                if (bestOp == 0) rotate_seg(Astart, 0);
                else if (bestOp == 1) rotate_seg(Astart, 1);
                else if (bestOp == 2) rotate_seg(Bstart, 0);
                else if (bestOp == 3) rotate_seg(Bstart, 1);
                curInv = bestInv;
            } else {
                // No improvement found; perform a heuristic step to escape local plateau
                // Alternate between A left and B right
                if (iter % 2 == 0) rotate_seg(Astart, 0);
                else rotate_seg(Bstart, 1);
                curInv = inv_count(get_sub());
            }
        }
        // If still not sorted, try a bounded fallback: brute passes
        if (!is_sorted_sub()) {
            int fallback = 5 * x * x;
            for (int k = 0; k < fallback && !is_sorted_sub(); ++k) {
                rotate_seg(Astart, 0);
                rotate_seg(Bstart, 1);
            }
        }
    }

    // Output
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }
    return 0;
}