#include <bits/stdc++.h>
using namespace std;

struct Line {
    long long px, py, qx, qy;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<int> a(11);
    for (int i = 1; i <= 10; i++) cin >> a[i];
    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) cin >> x[i] >> y[i];

    // Precompute forbidden intercept sets to avoid passing exactly through strawberry centers
    unordered_set<int> sx, sy, splus, sminus;
    sx.reserve(N*2); sy.reserve(N*2); splus.reserve(N*2); sminus.reserve(N*2);
    sx.max_load_factor(0.7); sy.max_load_factor(0.7); splus.max_load_factor(0.7); sminus.max_load_factor(0.7);
    for (int i = 0; i < N; i++) {
        sx.insert(x[i]);
        sy.insert(y[i]);
        splus.insert(y[i] - x[i]);   // for y = x + c
        sminus.insert(y[i] + x[i]);  // for y = -x + c
    }

    const int R = 10000;
    const int VHLIM = R - 5; // limit for vertical/horizontal intercepts
    const int DLIM = (int)(floor(R * sqrt(2.0)) - 5); // limit for diag intercepts
    const long long M = 900000000LL; // far endpoints to represent infinite line, within [-1e9, 1e9]

    // Allocate counts among 4 families: vertical, horizontal, diag+, diag-
    array<int, 4> cnt = {0, 0, 0, 0};
    for (int i = 0; i < K; i++) cnt[i % 4]++;

    auto pick_intercept = [&](int base, int lo, int hi, unordered_set<int> &used, const unordered_set<int> &forb)->int{
        if (base < lo) base = lo;
        if (base > hi) base = hi;
        int maxd = max(base - lo, hi - base);
        for (int d = 0; d <= maxd; d++) {
            int c1 = base + d;
            if (c1 >= lo && c1 <= hi) {
                if (!used.count(c1) && !forb.count(c1)) {
                    used.insert(c1);
                    return c1;
                }
            }
            if (d == 0) continue;
            int c2 = base - d;
            if (c2 >= lo && c2 <= hi) {
                if (!used.count(c2) && !forb.count(c2)) {
                    used.insert(c2);
                    return c2;
                }
            }
        }
        // Fallback (should rarely happen): find any available
        for (int c = lo; c <= hi; c++) {
            if (!used.count(c) && !forb.count(c)) {
                used.insert(c);
                return c;
            }
        }
        // As a last resort, allow even forbidden/used (to ensure output size K)
        int c = max(lo, min(base, hi));
        used.insert(c);
        return c;
    };

    vector<Line> lines;
    lines.reserve(K);

    // Vertical lines: x = c
    if (cnt[0] > 0) {
        int n = cnt[0];
        int space = 2 * VHLIM + 1;
        int step = max(1, space / (n + 1));
        unordered_set<int> used;
        used.reserve(n*2);
        used.max_load_factor(0.7);
        for (int i = 1; i <= n; i++) {
            int cand = -VHLIM + i * step;
            int c = pick_intercept(cand, -VHLIM, VHLIM, used, sx);
            Line L;
            L.px = c; L.py = -M;
            L.qx = c; L.qy = M;
            lines.push_back(L);
        }
    }

    // Horizontal lines: y = c
    if (cnt[1] > 0) {
        int n = cnt[1];
        int space = 2 * VHLIM + 1;
        int step = max(1, space / (n + 1));
        unordered_set<int> used;
        used.reserve(n*2);
        used.max_load_factor(0.7);
        for (int i = 1; i <= n; i++) {
            int cand = -VHLIM + i * step;
            int c = pick_intercept(cand, -VHLIM, VHLIM, used, sy);
            Line L;
            L.px = -M; L.py = c;
            L.qx = M;  L.qy = c;
            lines.push_back(L);
        }
    }

    // Diagonal +: y = x + c
    if (cnt[2] > 0) {
        int n = cnt[2];
        int space = 2 * DLIM + 1;
        int step = max(1, space / (n + 1));
        unordered_set<int> used;
        used.reserve(n*2);
        used.max_load_factor(0.7);
        for (int i = 1; i <= n; i++) {
            int cand = -DLIM + i * step;
            int c = pick_intercept(cand, -DLIM, DLIM, used, splus);
            Line L;
            L.px = -M; L.py = -M + c;
            L.qx = M;  L.qy =  M + c;
            // Ensure endpoints within [-1e9, 1e9]
            L.py = max(-1000000000LL, min(1000000000LL, L.py));
            L.qy = max(-1000000000LL, min(1000000000LL, L.qy));
            lines.push_back(L);
        }
    }

    // Diagonal -: y = -x + c
    if (cnt[3] > 0) {
        int n = cnt[3];
        int space = 2 * DLIM + 1;
        int step = max(1, space / (n + 1));
        unordered_set<int> used;
        used.reserve(n*2);
        used.max_load_factor(0.7);
        for (int i = 1; i <= n; i++) {
            int cand = -DLIM + i * step;
            int c = pick_intercept(cand, -DLIM, DLIM, used, sminus);
            Line L;
            L.px = -M; L.py = M + c;
            L.qx = M;  L.qy = -M + c;
            L.py = max(-1000000000LL, min(1000000000LL, L.py));
            L.qy = max(-1000000000LL, min(1000000000LL, L.qy));
            lines.push_back(L);
        }
    }

    // Safety: truncate or pad lines to exactly K
    if ((int)lines.size() > K) lines.resize(K);

    // If lines.size() < K (very unlikely), fill with random small lines across center
    while ((int)lines.size() < K) {
        int c = (int)lines.size();
        // Simple extra vertical line shifted slightly to avoid duplicates
        long long X = -5000 + c;
        if (X < -9999) X = -9999 + (c % 20000);
        Line L;
        L.px = X; L.py = -M;
        L.qx = X; L.qy = M;
        lines.push_back(L);
    }

    cout << (int)lines.size() << "\n";
    for (auto &L : lines) {
        cout << L.px << " " << L.py << " " << L.qx << " " << L.qy << "\n";
    }
    return 0;
}