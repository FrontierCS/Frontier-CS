#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getcharFast() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    int nextInt() {
        char c = getcharFast();
        while (c != '-' && (c < '0' || c > '9')) {
            if (c == EOF) return 0;
            c = getcharFast();
        }
        int sgn = 1;
        if (c == '-') { sgn = -1; c = getcharFast(); }
        int x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getcharFast();
        }
        return x * sgn;
    }
};

int n, m;
vector<vector<int>> G, R;
vector<int> degOut, degIn;

inline bool hasEdge(const vector<vector<int>>& adj, int u, int v) {
    const auto &vec = adj[u];
    int lo = 0, hi = (int)vec.size();
    while (lo < hi) {
        int mid = (lo + hi) >> 1;
        if (vec[mid] < v) lo = mid + 1;
        else hi = mid;
    }
    return (lo < (int)vec.size() && vec[lo] == v);
}

struct PathBuilder {
    int n;
    const vector<vector<int>> &G, &R;
    vector<int> pre, nxt;
    vector<unsigned char> inP;
    int head, tail;

    PathBuilder(int n, const vector<vector<int>> &G, const vector<vector<int>> &R)
        : n(n), G(G), R(R), pre(n+1, 0), nxt(n+1, 0), inP(n+1, 0), head(0), tail(0) {}

    inline void appendBack(int v) {
        inP[v] = 1;
        pre[v] = tail;
        nxt[v] = 0;
        if (tail) nxt[tail] = v;
        else head = v;
        tail = v;
    }

    inline void pushFront(int v) {
        inP[v] = 1;
        nxt[v] = head;
        pre[v] = 0;
        if (head) pre[head] = v;
        else tail = v;
        head = v;
    }

    inline void insertBefore(int t, int v) {
        int p = pre[t];
        inP[v] = 1;
        pre[v] = p;
        nxt[v] = t;
        pre[t] = v;
        if (p) nxt[p] = v;
        else head = v;
    }

    inline void insertAfter(int u, int v) {
        int s = nxt[u];
        inP[v] = 1;
        pre[v] = u;
        nxt[v] = s;
        nxt[u] = v;
        if (s) pre[s] = v;
        else tail = v;
    }

    void greedyExtend() {
        if (head == 0) return;
        int jt = 0, ih = 0;
        bool progress = true;
        while (progress) {
            progress = false;
            // extend at tail as much as possible
            while (true) {
                const auto &out = G[tail];
                while (jt < (int)out.size() && inP[out[jt]]) jt++;
                if (jt < (int)out.size()) {
                    int v = out[jt++];
                    if (!inP[v]) {
                        appendBack(v);
                        jt = 0; // new tail, reset pointer
                        progress = true;
                        continue;
                    }
                }
                break;
            }
            // extend at head as much as possible
            while (true) {
                const auto &in = R[head];
                while (ih < (int)in.size() && inP[in[ih]]) ih++;
                if (ih < (int)in.size()) {
                    int u = in[ih++];
                    if (!inP[u]) {
                        pushFront(u);
                        ih = 0; // new head, reset pointer
                        progress = true;
                        continue;
                    }
                }
                break;
            }
        }
    }

    vector<int> buildFromStart(int start, int maxPasses = 3) {
        // reset structures
        fill(pre.begin(), pre.end(), 0);
        fill(nxt.begin(), nxt.end(), 0);
        fill(inP.begin(), inP.end(), 0);
        head = tail = 0;

        // start
        pushFront(start);
        greedyExtend();

        vector<int> rem;
        rem.reserve(n);
        for (int i = 1; i <= n; ++i) if (!inP[i]) rem.push_back(i);

        int passes = 0;
        // random engine for shuffling remaining nodes per pass
        static uint64_t rng_state = 1469598103934665603ull ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        auto rng64 = [&]() {
            // xorshift64*
            uint64_t x = rng_state;
            x ^= x >> 12;
            x ^= x << 25;
            x ^= x >> 27;
            rng_state = x;
            return x * 2685821657736338717ULL;
        };

        while (!rem.empty() && passes < maxPasses) {
            passes++;
            // Shuffle remaining nodes to diversify insertion order
            for (int i = (int)rem.size() - 1; i > 0; --i) {
                int j = (int)(rng64() % (uint64_t)(i + 1));
                swap(rem[i], rem[j]);
            }
            bool changed = false;
            vector<int> newRem;
            newRem.reserve(rem.size());
            for (int v : rem) {
                if (inP[v]) continue;
                // quick append or prepend
                if (hasEdge(G, tail, v)) {
                    appendBack(v);
                    changed = true;
                    continue;
                }
                if (hasEdge(G, v, head)) {
                    pushFront(v);
                    changed = true;
                    continue;
                }

                bool ins = false;
                // choose smaller deg to scan first
                const auto &outv = G[v];
                const auto &inv = R[v];
                bool scanOutFirst = (outv.size() <= inv.size());
                if (scanOutFirst) {
                    // try insert before t (v -> t) with p -> v
                    for (int t : outv) {
                        if (!inP[t]) continue;
                        int p = pre[t];
                        if (p != 0 && hasEdge(G, p, v)) {
                            insertBefore(t, v);
                            ins = true;
                            changed = true;
                            break;
                        }
                    }
                    if (!ins) {
                        // try insert after u (u -> v) with v -> s (s = nxt[u])
                        for (int u : inv) {
                            if (!inP[u]) continue;
                            int s = nxt[u];
                            if (s != 0 && hasEdge(G, v, s)) {
                                insertAfter(u, v);
                                ins = true;
                                changed = true;
                                break;
                            }
                        }
                    }
                } else {
                    // scan in first
                    for (int u : inv) {
                        if (!inP[u]) continue;
                        int s = nxt[u];
                        if (s != 0 && hasEdge(G, v, s)) {
                            insertAfter(u, v);
                            ins = true;
                            changed = true;
                            break;
                        }
                    }
                    if (!ins) {
                        for (int t : outv) {
                            if (!inP[t]) continue;
                            int p = pre[t];
                            if (p != 0 && hasEdge(G, p, v)) {
                                insertBefore(t, v);
                                ins = true;
                                changed = true;
                                break;
                            }
                        }
                    }
                }
                if (!ins) {
                    newRem.push_back(v);
                } else {
                    // after any insertion, try to greedily extend from ends
                    greedyExtend();
                }
            }
            rem.swap(newRem);
            if (!changed) break;
        }

        // build final path
        vector<int> path;
        if (head == 0) return path;
        path.reserve(n);
        int u = head;
        while (u != 0) {
            path.push_back(u);
            u = nxt[u];
        }
        return path;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    n = fs.nextInt();
    m = fs.nextInt();
    // read scoring parameters (ignored)
    for (int i = 0; i < 10; ++i) { (void)fs.nextInt(); }

    G.assign(n + 1, {});
    R.assign(n + 1, {});
    degOut.assign(n + 1, 0);
    degIn.assign(n + 1, 0);

    G.reserve(n+1);
    R.reserve(n+1);

    for (int i = 0; i < m; ++i) {
        int u = fs.nextInt();
        int v = fs.nextInt();
        G[u].push_back(v);
        R[v].push_back(u);
        degOut[u]++;
        degIn[v]++;
    }

    for (int i = 1; i <= n; ++i) {
        sort(G[i].begin(), G[i].end());
        sort(R[i].begin(), R[i].end());
    }

    // Choose seeds
    int seed1 = 1;
    int maxOut = 0, idxOut = 1;
    int maxIn = 0, idxIn = 1;
    long long bestDiff = LLONG_MIN; int idxDiff = 1;
    int bestSumDeg = 0, idxSum = 1;
    for (int i = 1; i <= n; ++i) {
        if (degOut[i] > maxOut) { maxOut = degOut[i]; idxOut = i; }
        if (degIn[i] > maxIn) { maxIn = degIn[i]; idxIn = i; }
        long long diff = (long long)degOut[i] - (long long)degIn[i];
        if (diff > bestDiff) { bestDiff = diff; idxDiff = i; }
        int sumd = degOut[i] + degIn[i];
        if (sumd > bestSumDeg) { bestSumDeg = sumd; idxSum = i; }
    }

    vector<int> seeds;
    seeds.reserve(10);
    auto add_seed = [&](int x){
        if (x < 1 || x > n) return;
        for (int y : seeds) if (y == x) return;
        seeds.push_back(x);
    };
    add_seed(seed1);
    add_seed(idxOut);
    add_seed(idxIn);
    add_seed(idxDiff);
    add_seed(idxSum);

    // random seeds
    uint64_t rng_state = 88172645463393265ull ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng64 = [&]() {
        uint64_t x = rng_state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        rng_state = x;
        return x * 2685821657736338717ULL;
    };
    for (int i = 0; i < 5 && (int)seeds.size() < 8; ++i) {
        int r = (int)(rng64() % (uint64_t)n) + 1;
        add_seed(r);
    }

    PathBuilder builder(n, G, R);
    vector<int> bestPath;
    size_t bestLen = 0;

    for (int s : seeds) {
        vector<int> path = builder.buildFromStart(s, 3);
        if (path.size() > bestLen) {
            bestLen = path.size();
            bestPath.swap(path);
            if (bestLen == (size_t)n) break;
        }
    }

    if (bestPath.empty()) {
        // Fallback: output single vertex
        cout << 1 << "\n" << 1 << "\n";
        return 0;
    }

    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";

    return 0;
}