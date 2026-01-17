#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        T sign = 1;
        if constexpr (is_signed<T>::value) {
            if (c == '-') {
                sign = -1;
                c = read();
            }
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = val * sign;
        return true;
    }
};

struct RNG {
    uint64_t x;
    explicit RNG(uint64_t seed = 88172645463325252ull) : x(seed) {}
    inline uint64_t nextU64() {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        return x * 2685821657736338717ull;
    }
    inline uint32_t nextU32() { return (uint32_t)(nextU64() >> 32); }
    inline int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    if (n <= 0) return 0;

    vector<int> U(m), V(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    vector<int> ofs(n + 1, 0);
    for (int i = 0; i < n; i++) ofs[i + 1] = ofs[i] + deg[i];
    vector<int> cur = ofs;
    vector<int> adj(2LL * m);
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) putchar_unlocked(' ');
            putchar_unlocked('1');
        }
        putchar_unlocked('\n');
        return 0;
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)(&seed) * 0x9e3779b97f4a7c15ull;
    RNG rng(seed);

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return deg[a] > deg[b];
    });

    vector<int> col(n, 0);
    for (int v : order) {
        int cntc[4] = {0, 0, 0, 0};
        for (int ei = ofs[v]; ei < ofs[v + 1]; ei++) {
            int u = adj[ei];
            int cu = col[u];
            if (cu) cntc[cu]++;
        }
        int best = 1;
        int bestVal = cntc[1];
        for (int c = 2; c <= 3; c++) {
            int val = cntc[c];
            if (val < bestVal || (val == bestVal && (rng.nextU32() & 1))) {
                bestVal = val;
                best = c;
            }
        }
        col[v] = best;
    }

    vector<array<int, 4>> cnt(n);
    for (int i = 0; i < n; i++) cnt[i] = {0, 0, 0, 0};
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        cnt[u][col[v]]++;
        cnt[v][col[u]]++;
    }

    long long conflicts = 0;
    for (int i = 0; i < n; i++) conflicts += cnt[i][col[i]];
    conflicts /= 2;

    vector<int> bestCol = col;
    long long bestConf = conflicts;

    auto doMove = [&](int v, int newC) {
        int oldC = col[v];
        if (oldC == newC) return;
        long long delta = (long long)cnt[v][newC] - (long long)cnt[v][oldC];
        conflicts += delta;
        for (int ei = ofs[v]; ei < ofs[v + 1]; ei++) {
            int u = adj[ei];
            cnt[u][oldC]--;
            cnt[u][newC]++;
        }
        col[v] = newC;
    };

    vector<int> randOrder(n);
    iota(randOrder.begin(), randOrder.end(), 0);

    auto start = chrono::steady_clock::now();
    const double LIMIT = 1.92;
    int noImprovePasses = 0;

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed >= LIMIT) break;

        // shuffle vertices
        for (int i = n - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            swap(randOrder[i], randOrder[j]);
        }

        int moved = 0;
        for (int idx = 0; idx < n; idx++) {
            int v = randOrder[idx];
            int oldC = col[v];

            int bestC = oldC;
            int bestVal = cnt[v][oldC];
            for (int c = 1; c <= 3; c++) {
                int val = cnt[v][c];
                if (val < bestVal || (val == bestVal && c != bestC && (rng.nextU32() & 1))) {
                    bestVal = val;
                    bestC = c;
                }
            }

            if (bestC != oldC) {
                int oldVal = cnt[v][oldC];
                if (bestVal < oldVal) {
                    doMove(v, bestC);
                    moved++;
                } else if (bestVal == oldVal) {
                    // small probability side-move to escape plateaus
                    if ((rng.nextU32() % 1000u) < 20u) {
                        doMove(v, bestC);
                        moved++;
                    }
                }
            }
        }

        if (conflicts < bestConf) {
            bestConf = conflicts;
            bestCol = col;
        }

        if (conflicts == 0) break;

        if (moved == 0) noImprovePasses++;
        else noImprovePasses = 0;

        if (noImprovePasses >= 3) {
            int K = max(1, n / 200); // ~0.5%
            for (int t = 0; t < K; t++) {
                int v = rng.nextInt(n);
                for (int tries = 0; tries < 6; tries++) {
                    if (cnt[v][col[v]] > 0) break;
                    v = rng.nextInt(n);
                }
                int newC = rng.nextInt(3) + 1;
                if (newC == col[v]) newC = newC % 3 + 1;
                doMove(v, newC);
            }
            noImprovePasses = 0;
        }
    }

    // output best
    for (int i = 0; i < n; i++) {
        if (i) putchar_unlocked(' ');
        int c = bestCol[i];
        putchar_unlocked(char('0' + c));
    }
    putchar_unlocked('\n');
    return 0;
}