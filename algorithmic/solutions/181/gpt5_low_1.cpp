#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.readInt(n)) return 0;
    int W = (n + 63) >> 6;

    vector<vector<uint64_t>> D(n, vector<uint64_t>(W, 0));
    vector<vector<uint64_t>> F(n, vector<uint64_t>(W, 0));

    auto setBit = [&](vector<uint64_t> &row, int j) {
        row[j >> 6] |= (uint64_t(1) << (j & 63));
    };
    auto getBit = [&](const vector<uint64_t> &row, int j) -> int {
        return (row[j >> 6] >> (j & 63)) & 1ull;
    };

    vector<int> degD(n, 0), degF(n, 0);

    // Read D
    for (int i = 0; i < n; ++i) {
        for (int j = 0, x; j < n; ++j) {
            fs.readInt(x);
            if (x) {
                setBit(D[i], j);
                degD[i]++;
            }
        }
    }
    // Read F
    for (int i = 0; i < n; ++i) {
        for (int j = 0, x; j < n; ++j) {
            fs.readInt(x);
            if (x) {
                setBit(F[i], j);
                degF[i]++;
            }
        }
    }

    // Initial solution: map high-degree facilities to low-degree locations
    vector<int> facilities(n), locations(n);
    iota(facilities.begin(), facilities.end(), 0);
    iota(locations.begin(), locations.end(), 0);

    stable_sort(facilities.begin(), facilities.end(), [&](int a, int b){
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        return a < b;
    });
    stable_sort(locations.begin(), locations.end(), [&](int a, int b){
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });

    vector<int> p(n, -1);
    for (int i = 0; i < n; ++i) {
        p[facilities[i]] = locations[i];
    }

    auto getDij = [&](int i, int j) -> int {
        return getBit(D[i], j);
    };
    auto getFij = [&](int i, int j) -> int {
        return getBit(F[i], j);
    };

    // Compute initial cost
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        for (int j = 0; j < n; ++j) {
            if (getFij(i, j)) {
                cost += getDij(pi, p[j]);
            }
        }
    }

    // Local search with random swaps and delta evaluation
    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.8; // seconds (adjust if needed)
    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, n - 1);

    auto elapsed = [&]() -> double {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    // Try random swaps until time runs out
    while (elapsed() < TIME_LIMIT) {
        int a = dist(rng);
        int b = dist(rng);
        if (a == b) continue;
        if (a > b) swap(a, b);

        int A = p[a], B = p[b];
        if (A == B) continue;

        long long delta = 0;
        for (int k = 0; k < n; ++k) {
            int pk = p[k];
            if (getFij(a, k)) delta += getDij(B, pk) - getDij(A, pk);
            if (getFij(b, k)) delta += getDij(A, pk) - getDij(B, pk);
            if (getFij(k, a)) delta += getDij(pk, B) - getDij(pk, A);
            if (getFij(k, b)) delta += getDij(pk, A) - getDij(pk, B);
        }

        if (delta < 0) {
            swap(p[a], p[b]);
            cost += delta;
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}