#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<Op> ops;

    auto output_shift = [&](int l, int dir, int x, vector<int>& a, vector<int>& pos, vector<Op>& ops) {
        int r = l + x - 1;
        if (dir == 0) {
            int tmp = a[l];
            for (int i = l; i < r; ++i) {
                a[i] = a[i + 1];
                pos[a[i]] = i;
            }
            a[r] = tmp;
            pos[tmp] = r;
        } else {
            int tmp = a[r];
            for (int i = r; i > l; --i) {
                a[i] = a[i - 1];
                pos[a[i]] = i;
            }
            a[l] = tmp;
            pos[tmp] = l;
        }
        ops.push_back({l, r, dir});
    };

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int x = min(30, (n + 2) / 2);
    if (x < 2) x = 2;
    if (n >= 3 && x >= n) x = n - 1; // safety, though with chosen x this shouldn't happen

    auto shift_left = [&](int l) { output_shift(l, 0, x, a, pos, ops); };
    auto shift_right = [&](int l) { output_shift(l, 1, x, a, pos, ops); };

    int p = n - 2 * x + 2;
    if (p < 0) p = 0;

    // Phase 1: Fix first p positions
    for (int i = 1; i <= p; ++i) {
        while (pos[i] >= i + x - 1) {
            int l = pos[i] - x + 1;
            shift_right(l);
        }
        while (pos[i] > i) {
            shift_left(i);
        }
    }

    // Phase 2: Sort the last block of length L = 2x - 2 using only windows inside the block
    int L = 2 * x - 2;
    int Bstart = n - L + 1;
    int Bend = n;

    // Place first x-1 positions within the block
    for (int i = Bstart; i <= Bstart + x - 2; ++i) {
        while (pos[i] >= i + x - 1) {
            int l = pos[i] - x + 1;
            shift_right(l);
        }
        while (pos[i] > i) {
            shift_left(i);
        }
    }
    // Place last x-1 positions within the block from right to left
    for (int j = Bend; j >= Bstart + x - 1; --j) {
        while (pos[j] <= j - x + 1) {
            int l = pos[j];
            shift_left(l);
        }
        while (pos[j] < j) {
            int l = j - x + 1;
            shift_right(l);
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}