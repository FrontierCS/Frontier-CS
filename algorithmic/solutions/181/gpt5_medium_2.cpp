#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const size_t BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
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
} in;

static inline long long deltaSwap(int a, int b, const vector<int>& p, const vector<uint8_t>& D, const vector<uint8_t>& F, int n) {
    int ka = p[a];
    int kb = p[b];
    if (ka == kb) return 0;
    long long s1 = 0, s2 = 0, s3 = 0, s4 = 0;
    const int an = a * n;
    const int bn = b * n;
    for (int j = 0; j < n; ++j) {
        int pj = p[j];
        uint8_t fa = F[an + j];
        uint8_t fb = F[bn + j];
        if (fa) s1 += (int)D[kb * n + pj] - (int)D[ka * n + pj];
        if (fb) s2 += (int)D[ka * n + pj] - (int)D[kb * n + pj];
    }
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        uint8_t fia = F[i * n + a];
        uint8_t fib = F[i * n + b];
        if (fia) s3 += (int)D[pi * n + kb] - (int)D[pi * n + ka];
        if (fib) s4 += (int)D[pi * n + ka] - (int)D[pi * n + kb];
    }
    long long corr = 0;
    // x in {a,b}, y in {a,b}
    // For x=a: old ka, new kb. For x=b: old kb, new ka.
    // For y=a: old ka, new kb. For y=b: old kb, new ka.
    {
        // (a,a)
        uint8_t f = F[an + a];
        if (f) {
            corr += (int)D[kb * n + kb] - (int)D[kb * n + ka] - (int)D[ka * n + kb] + (int)D[ka * n + ka];
        }
    }
    {
        // (a,b)
        uint8_t f = F[an + b];
        if (f) {
            corr += (int)D[kb * n + ka] - (int)D[kb * n + kb] - (int)D[ka * n + ka] + (int)D[ka * n + kb];
        }
    }
    {
        // (b,a)
        uint8_t f = F[bn + a];
        if (f) {
            corr += (int)D[ka * n + kb] - (int)D[ka * n + ka] - (int)D[kb * n + kb] + (int)D[kb * n + ka];
        }
    }
    {
        // (b,b)
        uint8_t f = F[bn + b];
        if (f) {
            corr += (int)D[ka * n + ka] - (int)D[ka * n + kb] - (int)D[kb * n + ka] + (int)D[kb * n + kb];
        }
    }
    return s1 + s2 + s3 + s4 + corr;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!in.nextInt(n)) return 0;

    vector<uint8_t> D((size_t)n * n);
    vector<uint8_t> F((size_t)n * n);
    vector<int> rowD(n, 0), colD(n, 0);
    vector<int> outF(n, 0), inF(n, 0);

    // Read D
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int v;
            in.nextInt(v);
            uint8_t b = (uint8_t)v;
            D[base + j] = b;
            if (b) {
                rowD[i]++; colD[j]++;
            }
        }
    }
    // Read F
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int v;
            in.nextInt(v);
            uint8_t b = (uint8_t)v;
            F[base + j] = b;
            if (b) {
                outF[i]++; inF[j]++;
            }
        }
    }

    // Compute weights
    vector<pair<long long,int>> wf(n), sd(n);
    for (int i = 0; i < n; ++i) {
        long long w = (long long)outF[i] + (long long)inF[i];
        wf[i] = {w, i};
    }
    for (int k = 0; k < n; ++k) {
        long long s = (long long)rowD[k] + (long long)colD[k];
        sd[k] = {s, k};
    }
    sort(wf.begin(), wf.end(), [](const auto& a, const auto& b){
        if (a.first != b.first) return a.first > b.first; // high to low
        return a.second < b.second;
    });
    sort(sd.begin(), sd.end(), [](const auto& a, const auto& b){
        if (a.first != b.first) return a.first < b.first; // low to high
        return a.second < b.second;
    });

    vector<int> p(n);
    for (int t = 0; t < n; ++t) {
        p[wf[t].second] = sd[t].second;
    }

    // Local search with time budget
    auto tstart = chrono::steady_clock::now();
    const double timeLimitSec = 0.9; // adjust if needed
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, n - 1);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - tstart).count();
        if (elapsed > timeLimitSec) break;
        // batch attempts
        for (int iter = 0; iter < 256; ++iter) {
            int a = dist(rng);
            int b = dist(rng);
            if (a == b) continue;
            long long d = deltaSwap(a, b, p, D, F, n);
            if (d < 0) {
                swap(p[a], p[b]);
            }
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