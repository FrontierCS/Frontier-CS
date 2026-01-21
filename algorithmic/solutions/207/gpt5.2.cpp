#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
#if defined(_WIN32) || defined(_WIN64)
        return getchar();
#else
        return getchar_unlocked();
#endif
    }
    template <class T>
    bool readInt(T &out) {
        int c;
        do {
            c = gc();
            if (c == EOF) return false;
        } while (c <= ' ');
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = gc();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = gc();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct FastOutput {
    static const int BUFSZ = 1 << 20;
    int idx = 0;
    char buf[BUFSZ];

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
    inline void pc(char c) {
        if (idx >= BUFSZ) flush();
        buf[idx++] = c;
    }
    inline void writeInt(long long x) {
        if (x == 0) { pc('0'); return; }
        if (x < 0) { pc('-'); x = -x; }
        char s[24];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pc(s[n]);
    }
    inline void writeInt128(__int128 x) {
        if (x == 0) { pc('0'); return; }
        if (x < 0) { pc('-'); x = -x; }
        char s[64];
        int n = 0;
        while (x) { int d = int(x % 10); s[n++] = char('0' + d); x /= 10; }
        while (n--) pc(s[n]);
    }
    inline void writePair(int a, int b) {
        writeInt(a);
        pc(' ');
        writeInt(b);
        pc('\n');
    }
};

int main() {
    FastScanner fs;
    FastOutput fo;

    int N;
    if (!fs.readInt(N)) return 0;

    vector<int> S(N);
    for (int i = 0; i < N; i++) fs.readInt(S[i]);

    int M;
    fs.readInt(M);

    vector<int> X(M), Y(M);
    for (int i = 0; i < M; i++) {
        fs.readInt(X[i]);
        fs.readInt(Y[i]);
    }

    if (M == 0) {
        fo.writeInt(0);
        fo.pc('\n');
        fo.writeInt128(0);
        fo.pc('\n');
        return 0;
    }

    // Compute Jprod^{-1} by simulating Jerry swaps on labels at positions.
    vector<int> labels(N);
    iota(labels.begin(), labels.end(), 0);
    for (int i = 0; i < M; i++) {
        int a = X[i], b = Y[i];
        if (a != b) swap(labels[a], labels[b]);
    }

    // g = f ∘ Jprod^{-1}, where f(i)=S[i] and Jprod^{-1}(pos)=labels[pos]
    vector<int> g(N);
    for (int i = 0; i < N; i++) g[i] = S[labels[i]];

    // Decompose g into transpositions: g = F_{L-1} ... F_0 (composition), store F_0..F_{L-1}
    vector<char> vis(N, 0);
    vector<pair<int,int>> factors;
    factors.reserve(N);

    for (int i = 0; i < N; i++) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = g[cur];
        }
        if ((int)cyc.size() <= 1) continue;
        int c0 = cyc[0];
        for (int j = 1; j < (int)cyc.size(); j++) {
            factors.push_back({c0, cyc[j]});
        }
    }

    int L = (int)factors.size();
    // Guaranteed solvable: L <= M
    if (L > M) {
        // Fallback (should not happen with promised inputs): output something trivial.
        // Still must output valid format; cannot guarantee correctness.
        fo.writeInt(M);
        fo.pc('\n');
        for (int i = 0; i < M; i++) fo.writePair(0, 0);
        fo.writeInt128(0);
        fo.pc('\n');
        return 0;
    }

    vector<pair<int,int>> U(M, {0,0});

    // Maintain B = A_i^{-1} = J_{i+1}...J_{M-1} as mapping b[domain]=image and inverse binv[image]=domain
    vector<int> b(N), binv(N);
    iota(b.begin(), b.end(), 0);
    iota(binv.begin(), binv.end(), 0);

    for (int i = M - 1; i >= 0; i--) {
        if (i < L) {
            int p = factors[i].first;
            int q = factors[i].second;
            U[i] = {b[p], b[q]};
        } else {
            U[i] = {0, 0};
        }

        // Update B for next i-1: B := J_i ∘ B (swap outputs X[i],Y[i])
        int x = X[i], y = Y[i];
        if (x != y) {
            int px = binv[x];
            int py = binv[y];
            swap(b[px], b[py]);
            swap(binv[x], binv[y]);
        }
    }

    long long sumCost = 0;
    for (int i = 0; i < M; i++) {
        sumCost += llabs((long long)U[i].first - (long long)U[i].second);
    }
    __int128 V = (__int128)M * (__int128)sumCost;

    fo.writeInt(M);
    fo.pc('\n');
    for (int i = 0; i < M; i++) {
        fo.writePair(U[i].first, U[i].second);
    }
    fo.writeInt128(V);
    fo.pc('\n');
    fo.flush();
    return 0;
}