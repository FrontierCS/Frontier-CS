#include <bits/stdc++.h>
using namespace std;

using uchar = unsigned char;

static inline long long computeCost(const vector<int>& p, const uchar* D, const uchar* F, int n) {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int locI = p[i];
        int Di_base = locI * n;
        int Fi_base = i * n;
        for (int j = 0; j < n; ++j) {
            if (F[Fi_base + j] && D[Di_base + p[j]]) {
                ++cost;
            }
        }
    }
    return cost;
}

static inline long long swapDelta(int a, int b, const vector<int>& p, const uchar* D, const uchar* F, int n) {
    if (a == b) return 0;
    int locA = p[a];
    int locB = p[b];
    long long delta = 0;

    // Interactions with other facilities k
    for (int k = 0; k < n; ++k) {
        if (k == a || k == b) continue;
        int locK = p[k];

        int Fa_k = F[a * n + k];
        int Fk_a = F[k * n + a];
        int Fb_k = F[b * n + k];
        int Fk_b = F[k * n + b];

        // Before swap
        int before =
            Fa_k * D[locA * n + locK] +
            Fk_a * D[locK * n + locA] +
            Fb_k * D[locB * n + locK] +
            Fk_b * D[locK * n + locB];

        // After swap
        int after =
            Fa_k * D[locB * n + locK] +
            Fk_a * D[locK * n + locB] +
            Fb_k * D[locA * n + locK] +
            Fk_b * D[locK * n + locA];

        delta += (after - before);
    }

    // Interactions among {a,b}
    int Faa = F[a * n + a];
    int Fab = F[a * n + b];
    int Fba = F[b * n + a];
    int Fbb = F[b * n + b];

    int before_inner =
        Faa * D[locA * n + locA] +
        Fab * D[locA * n + locB] +
        Fba * D[locB * n + locA] +
        Fbb * D[locB * n + locB];

    int after_inner =
        Faa * D[locB * n + locB] +
        Fab * D[locB * n + locA] +
        Fba * D[locA * n + locB] +
        Fbb * D[locA * n + locA];

    delta += (after_inner - before_inner);

    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int nn = n * n;
    vector<uchar> D(nn);
    vector<uchar> F(nn);

    vector<int> rowD(n, 0), colD(n, 0);
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            uchar v = (uchar)x;
            D[base + j] = v;
            rowD[i] += v;
            colD[j] += v;
        }
    }

    vector<int> rowF(n, 0), colF(n, 0);
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            uchar v = (uchar)x;
            F[base + j] = v;
            rowF[i] += v;
            colF[j] += v;
        }
    }

    vector<int> degD(n), degF(n);
    for (int i = 0; i < n; ++i) {
        degD[i] = rowD[i] + colD[i];
        degF[i] = rowF[i] + colF[i];
    }

    // Order facilities by descending flow degree
    vector<int> facOrder(n);
    iota(facOrder.begin(), facOrder.end(), 0);
    sort(facOrder.begin(), facOrder.end(), [&](int a, int b) {
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        return a < b;
    });

    // Order locations by ascending distance degree
    vector<int> locOrder(n);
    iota(locOrder.begin(), locOrder.end(), 0);
    sort(locOrder.begin(), locOrder.end(), [&](int a, int b) {
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });

    // Build initial permutation: p[facility] = location
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[facOrder[i]] = locOrder[i];
    }

    const uchar* Dd = D.data();
    const uchar* Fd = F.data();

    long long currentCost = computeCost(p, Dd, Fd, n);

    // Limited random swap local search
    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    int maxAttempts = 4000;
    for (int attempt = 0; attempt < maxAttempts; ) {
        int a = (int)(rng() % n);
        int b = (int)(rng() % n);
        if (a == b) continue;
        ++attempt;
        long long delta = swapDelta(a, b, p, Dd, Fd, n);
        if (delta < 0) {
            swap(p[a], p[b]);
            currentCost += delta;
        }
    }

    // Output permutation in 1-based indexing
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';

    return 0;
}