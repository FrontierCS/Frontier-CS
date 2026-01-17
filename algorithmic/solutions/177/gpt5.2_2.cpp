#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    unsigned char buf[BUFSIZE];

    inline unsigned char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        unsigned char c;
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

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)next(); }
    inline int nextInt(int bound) { return (int)(next() % (uint64_t)bound); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

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

    vector<int> off(n + 1, 0);
    for (int i = 0; i < n; i++) off[i + 1] = off[i] + deg[i];
    vector<int> ptr = off;
    vector<int> adj(2LL * m);
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        adj[ptr[u]++] = v;
        adj[ptr[v]++] = u;
    }

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)n * 1000003ULL + (uint64_t)m * 10007ULL;
    SplitMix64 rng(seed);

    vector<int> col(n, 0);
    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << "\n";
        return 0;
    }

    vector<uint64_t> key(n);
    for (int i = 0; i < n; i++) key[i] = rng.next();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return key[a] < key[b];
    });

    for (int v : order) {
        int cnt[3] = {0, 0, 0};
        for (int ei = off[v]; ei < off[v + 1]; ei++) {
            int u = adj[ei];
            int cu = col[u];
            if (cu) cnt[cu - 1]++;
        }
        int best = 0;
        int bestVal = cnt[0];
        if (cnt[1] < bestVal) bestVal = cnt[1], best = 1;
        else if (cnt[1] == bestVal && (rng.next() & 1ULL)) best = 1;
        if (cnt[2] < bestVal) bestVal = cnt[2], best = 2;
        else if (cnt[2] == bestVal && (rng.next() & 1ULL)) best = 2;
        col[v] = best + 1;
    }

    vector<array<int,3>> neighCnt(n);
    for (int i = 0; i < n; i++) neighCnt[i] = {0,0,0};

    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        neighCnt[u][col[v] - 1]++;
        neighCnt[v][col[u] - 1]++;
    }

    vector<int> conflictVal(n, 0);
    long long totalConf = 0;
    for (int i = 0; i < n; i++) {
        conflictVal[i] = neighCnt[i][col[i] - 1];
        totalConf += conflictVal[i];
    }
    totalConf /= 2;

    vector<int> clist;
    clist.reserve(n);
    vector<int> pos(n, -1);

    auto addConf = [&](int v) {
        if (pos[v] != -1) return;
        pos[v] = (int)clist.size();
        clist.push_back(v);
    };
    auto remConf = [&](int v) {
        int p = pos[v];
        if (p == -1) return;
        int last = clist.back();
        clist[p] = last;
        pos[last] = p;
        clist.pop_back();
        pos[v] = -1;
    };
    auto updateMember = [&](int v) {
        if (conflictVal[v] > 0) addConf(v);
        else remConf(v);
    };

    for (int i = 0; i < n; i++) updateMember(i);

    vector<int> bestCol = col;
    long long bestConf = totalConf;

    auto start = chrono::steady_clock::now();
    auto timeLimit = start + chrono::milliseconds(1700);

    long long maxIters = max(200000LL, 20LL * (long long)m);
    long long noImprove = 0;

    for (long long it = 0; it < maxIters && !clist.empty(); it++) {
        if ((it & 2047LL) == 0) {
            if (chrono::steady_clock::now() > timeLimit) break;
        }

        int sz = (int)clist.size();
        int v1 = clist[rng.nextInt(sz)];
        int v2 = clist[rng.nextInt(sz)];
        int v = (conflictVal[v2] > conflictVal[v1]) ? v2 : v1;

        int old = col[v] - 1;
        int vals[3] = {neighCnt[v][0], neighCnt[v][1], neighCnt[v][2]};

        int minVal = min(vals[0], min(vals[1], vals[2]));
        int cand[3], csz = 0;
        for (int c = 0; c < 3; c++) if (vals[c] == minVal) cand[csz++] = c;
        int neu = cand[rng.nextInt(csz)];

        if (neu == old) {
            if (csz > 1) {
                int idx = rng.nextInt(csz - 1);
                if (cand[idx] == old) idx = csz - 1;
                neu = cand[idx];
            } else {
                neu = (old + 1 + rng.nextInt(2)) % 3;
            }
        }

        int before = vals[old];
        int after = vals[neu];
        if (before == after && (rng.next() % 4ULL) != 0ULL) {
            // often skip equal moves to reduce oscillation
            continue;
        }

        totalConf += (after - before);
        col[v] = neu + 1;

        conflictVal[v] = neighCnt[v][neu];
        updateMember(v);

        for (int ei = off[v]; ei < off[v + 1]; ei++) {
            int u = adj[ei];
            neighCnt[u][old]--;
            neighCnt[u][neu]++;

            conflictVal[u] = neighCnt[u][col[u] - 1];
            updateMember(u);
        }

        if (totalConf < bestConf) {
            bestConf = totalConf;
            bestCol = col;
            noImprove = 0;
            if (bestConf == 0) break;
        } else {
            noImprove++;
            if (noImprove > 5LL * m) {
                // light random kick: recolor a random conflicted vertex randomly
                if (!clist.empty()) {
                    int w = clist[rng.nextInt((int)clist.size())];
                    int ow = bestCol[w] - 1;
                    int nw = (ow + 1 + rng.nextInt(2)) % 3;
                    (void)nw;
                }
                noImprove = 0;
            }
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << bestCol[i];
    }
    cout << "\n";
    return 0;
}