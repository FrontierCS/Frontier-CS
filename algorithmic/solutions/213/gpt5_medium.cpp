#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, d; // d: 0 left, 1 right
};

int n, x;
vector<int> a, pos;
vector<Op> ops;

inline void record_shift_left(int l) {
    int r = l + x - 1;
    Op op{l, r, 0};
    ops.push_back(op);
    int temp = a[l];
    for (int i = l; i < r; ++i) {
        a[i] = a[i + 1];
        pos[a[i]] = i;
    }
    a[r] = temp;
    pos[temp] = r;
}

inline void record_shift_right(int l) {
    int r = l + x - 1;
    Op op{l, r, 1};
    ops.push_back(op);
    int temp = a[r];
    for (int i = r; i > l; --i) {
        a[i] = a[i - 1];
        pos[a[i]] = i;
    }
    a[l] = temp;
    pos[temp] = l;
}

// For buffer S = [L..n], define windows:
// c1: [L..n-1], c2: [L+1..n]
int L;

inline void c1_left() { record_shift_left(L); }
inline void c1_right() { record_shift_right(L); }
inline void c2_left() { record_shift_left(L + 1); }
inline void c2_right() { record_shift_right(L + 1); }

// π = c2 ∘ c1^{-1}: sequence apply c1^{-1} then c2
inline void apply_pi() { c1_left(); c2_right(); }
// π^{-1} = c1 ∘ c2^{-1}: sequence apply c2^{-1} then c1
inline void apply_pi_inv() { c2_left(); c1_right(); }

// Swap adjacent positions j and j+1 within S using only c1, c2 operations.
// j in [L .. n-1]
void swap_adj_S(int j) {
    int k = j - L; // 0-based index within S
    for (int t = 0; t < k; ++t) c1_left();
    apply_pi_inv();
    for (int t = 0; t < k; ++t) c1_right();
    for (int t = 0; t < k; ++t) c1_left();
    apply_pi();
    for (int t = 0; t < k; ++t) c1_right();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n;
    a.assign(n + 1, 0);
    pos.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    if (n == 1) {
        x = 1;
        cout << x << "\n" << 0 << "\n";
        return 0;
    }

    if (n <= 3) {
        x = 2;
        // Simple bubble sort using x=2 (adjacent swaps)
        for (int i = 1; i <= n; ++i) {
            for (int j = n - 1; j >= i; --j) {
                if (a[j] > a[j + 1]) {
                    // left shift on [j, j+1]
                    record_shift_left(j);
                }
            }
        }
        cout << x << "\n" << (int)ops.size() << "\n";
        for (auto &op : ops) cout << op.l << " " << op.r << " " << op.d << "\n";
        return 0;
    }

    x = min(n - 1, (int)floor(sqrt((long double)n)) + 1);
    L = n - x; // buffer S = [L..n], size x+1

    // Step 1: place positions 1..L-1
    for (int i = 1; i <= L - 1; ++i) {
        int p = pos[i];
        while (p - (x - 1) >= i) {
            int l = p - x + 1;
            record_shift_right(l);
            p = pos[i];
        }
        while ((p = pos[i]) > i) {
            record_shift_left(i);
        }
    }

    // Step 2: sort S = [L..n] using bubble sort with swap_adj_S
    for (int pass = L; pass <= n; ++pass) {
        for (int j = L; j <= n - 1; ++j) {
            if (a[j] > a[j + 1]) {
                swap_adj_S(j);
            }
        }
    }

    cout << x << "\n" << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}