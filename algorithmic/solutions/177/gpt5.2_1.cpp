#include <bits/stdc++.h>
#include <charconv>
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

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline int nextInt(int mod) { return (int)(next() % (uint64_t)mod); }
};

struct BadList {
    vector<int> lst;
    vector<int> pos;
    BadList() = default;
    explicit BadList(int n) { reset(n); }

    void reset(int n) {
        lst.clear();
        pos.assign(n, -1);
    }
    inline void add(int v) {
        if (pos[v] != -1) return;
        pos[v] = (int)lst.size();
        lst.push_back(v);
    }
    inline void remove(int v) {
        int i = pos[v];
        if (i == -1) return;
        int last = lst.back();
        lst[i] = last;
        pos[last] = i;
        lst.pop_back();
        pos[v] = -1;
    }
    inline int size() const { return (int)lst.size(); }
    inline int pick(SplitMix64 &rng) const { return lst[rng.nextInt((int)lst.size())]; }
};

struct Graph {
    int n = 0;
    int m = 0;
    vector<int> deg;
    vector<int> off;
    vector<int> to;
};

struct State {
    vector<uint8_t> color;             // 0..2
    vector<array<int, 3>> cnt;         // cnt[v][c] = #neighbors of color c
    BadList bad;
    long long confEdges = 0;           // number of conflicting edges
};

static inline State buildState(const Graph &g, const vector<uint8_t> &initColor) {
    State st;
    st.color = initColor;
    st.cnt.assign(g.n, array<int, 3>{0, 0, 0});
    st.bad.reset(g.n);

    for (int v = 0; v < g.n; v++) {
        for (int ei = g.off[v]; ei < g.off[v + 1]; ei++) {
            int u = g.to[ei];
            st.cnt[v][st.color[u]]++;
        }
    }

    long long sum = 0;
    for (int v = 0; v < g.n; v++) {
        int confV = st.cnt[v][st.color[v]];
        sum += confV;
        if (confV > 0) st.bad.add(v);
    }
    st.confEdges = sum / 2;
    return st;
}

static inline vector<uint8_t> greedyInit(const Graph &g, SplitMix64 &rng) {
    vector<int> order(g.n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (g.deg[a] != g.deg[b]) return g.deg[a] > g.deg[b];
        return a < b;
    });

    vector<uint8_t> color(g.n, 255);
    for (int v : order) {
        int ccount[3] = {0, 0, 0};
        for (int ei = g.off[v]; ei < g.off[v + 1]; ei++) {
            int u = g.to[ei];
            if (color[u] != 255) ccount[color[u]]++;
        }
        int mn = min({ccount[0], ccount[1], ccount[2]});
        int cand[3], cs = 0;
        for (int c = 0; c < 3; c++) if (ccount[c] == mn) cand[cs++] = c;
        color[v] = (uint8_t)cand[rng.nextInt(cs)];
    }
    for (int i = 0; i < g.n; i++) if (color[i] == 255) color[i] = (uint8_t)(rng.next() % 3);
    return color;
}

static inline vector<uint8_t> randomInit(const Graph &g, SplitMix64 &rng) {
    vector<uint8_t> color(g.n);
    for (int i = 0; i < g.n; i++) color[i] = (uint8_t)(rng.next() % 3);
    return color;
}

static inline void localSearch(
    const Graph &g,
    State &st,
    long long &bestConf,
    vector<uint8_t> &bestColor,
    SplitMix64 &rng,
    chrono::steady_clock::time_point endTime,
    int iterLimit
) {
    const int PERTURB_PCT = 3; // 3% when stuck
    for (int iter = 0; iter < iterLimit; iter++) {
        if ((iter & 2047) == 0) {
            if (chrono::steady_clock::now() >= endTime) break;
        }
        if (st.bad.size() == 0) break;

        int v = st.bad.pick(rng);
        int cur = st.color[v];

        int cv0 = st.cnt[v][0], cv1 = st.cnt[v][1], cv2 = st.cnt[v][2];
        int curVal = (cur == 0 ? cv0 : (cur == 1 ? cv1 : cv2));
        int mn = min({cv0, cv1, cv2});

        int cand[3], cs = 0;
        if (cv0 == mn) cand[cs++] = 0;
        if (cv1 == mn) cand[cs++] = 1;
        if (cv2 == mn) cand[cs++] = 2;

        int newc = cur;

        if (mn < curVal) {
            newc = cand[rng.nextInt(cs)];
        } else {
            // sideways if possible
            if (cs > 1) {
                // pick candidate != cur
                int tmp[2], ts = 0;
                for (int i = 0; i < cs; i++) if (cand[i] != cur) tmp[ts++] = cand[i];
                if (ts > 0) newc = tmp[rng.nextInt(ts)];
            } else {
                // perturb occasionally
                if (rng.nextInt(100) < PERTURB_PCT) {
                    newc = (cur + 1 + rng.nextInt(2)) % 3;
                } else {
                    continue;
                }
            }
        }

        if (newc == cur) continue;

        int beforeConfV = curVal;
        int afterConfV = (newc == 0 ? cv0 : (newc == 1 ? cv1 : cv2));
        st.confEdges += (long long)(afterConfV - beforeConfV);

        // Update neighbors' counts and their bad status
        for (int ei = g.off[v]; ei < g.off[v + 1]; ei++) {
            int u = g.to[ei];
            int colU = st.color[u];
            int beforeConfU = st.cnt[u][colU];

            // v was color cur, becomes newc
            st.cnt[u][cur]--;
            st.cnt[u][newc]++;

            int afterConfU = beforeConfU;
            if (colU == cur) afterConfU--;
            else if (colU == newc) afterConfU++;

            if (beforeConfU == 0) {
                if (afterConfU > 0) st.bad.add(u);
            } else {
                if (afterConfU == 0) st.bad.remove(u);
            }
        }

        // Update v bad status
        if (beforeConfV == 0) {
            if (afterConfV > 0) st.bad.add(v);
        } else {
            if (afterConfV == 0) st.bad.remove(v);
        }

        st.color[v] = (uint8_t)newc;

        if (st.confEdges < bestConf) {
            bestConf = st.confEdges;
            bestColor = st.color;
            if (bestConf == 0) break;
        }
    }
}

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    Graph g;
    g.n = n;
    g.m = m;
    g.deg.assign(n, 0);

    vector<int> U(m), V(m);
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        g.deg[u]++; g.deg[v]++;
    }

    if (m == 0) {
        string out;
        out.reserve((size_t)n * 2 + 2);
        for (int i = 0; i < n; i++) {
            out += '1';
            out += (i + 1 == n ? '\n' : ' ');
        }
        fwrite(out.data(), 1, out.size(), stdout);
        return 0;
    }

    g.off.assign(n + 1, 0);
    for (int i = 0; i < n; i++) g.off[i + 1] = g.off[i] + g.deg[i];
    g.to.assign(g.off[n], 0);
    vector<int> cur = g.off;

    for (int i = 0; i < m; i++) {
        int a = U[i], b = V[i];
        g.to[cur[a]++] = b;
        g.to[cur[b]++] = a;
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&g;
    SplitMix64 rng(seed);

    auto start = chrono::steady_clock::now();
    auto endTime = start + chrono::milliseconds(1800);

    long long bestConf = (1LL << 60);
    vector<uint8_t> bestColor;

    // Trial 1: greedy
    {
        vector<uint8_t> init = greedyInit(g, rng);
        State st = buildState(g, init);
        bestConf = st.confEdges;
        bestColor = st.color;

        int iterLimit = min(5000000, max(200000, 40 * n));
        localSearch(g, st, bestConf, bestColor, rng, endTime, iterLimit);
    }

    // Trial 2-3: random restarts if time allows
    for (int t = 0; t < 2; t++) {
        if (chrono::steady_clock::now() >= endTime) break;
        vector<uint8_t> init = randomInit(g, rng);
        State st = buildState(g, init);

        if (st.confEdges < bestConf) {
            bestConf = st.confEdges;
            bestColor = st.color;
        }
        int iterLimit = min(4000000, max(150000, 25 * n));
        localSearch(g, st, bestConf, bestColor, rng, endTime, iterLimit);
        if (bestConf == 0) break;
    }

    // Output best coloring (1..3)
    string out;
    out.reserve((size_t)n * 2 + 16);
    char buf[16];
    for (int i = 0; i < n; i++) {
        int val = (int)bestColor[i] + 1;
        auto res = to_chars(buf, buf + 16, val);
        out.append(buf, res.ptr);
        out.push_back(i + 1 == n ? '\n' : ' ');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}