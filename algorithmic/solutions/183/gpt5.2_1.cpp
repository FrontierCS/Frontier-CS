#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
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
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct State {
    int n = 0;
    int k = 0;
    vector<uint8_t> sel;
    vector<int> conf;
    vector<int> pos;
    vector<int> selVec;

    State() = default;
    explicit State(int n_) { init(n_); }

    void init(int n_) {
        n = n_;
        k = 0;
        sel.assign(n, 0);
        conf.assign(n, 0);
        pos.assign(n, -1);
        selVec.clear();
    }

    void clear() {
        k = 0;
        fill(sel.begin(), sel.end(), 0);
        fill(conf.begin(), conf.end(), 0);
        fill(pos.begin(), pos.end(), -1);
        selVec.clear();
    }

    inline void addVertex(int v, const vector<vector<int>> &adj) {
        sel[v] = 1;
        pos[v] = (int)selVec.size();
        selVec.push_back(v);
        k++;
        for (int nb : adj[v]) conf[nb]++;
    }

    inline void removeVertex(int v, const vector<vector<int>> &adj) {
        sel[v] = 0;
        k--;
        int idx = pos[v];
        int last = selVec.back();
        selVec[idx] = last;
        pos[last] = idx;
        selVec.pop_back();
        pos[v] = -1;
        for (int nb : adj[v]) conf[nb]--;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> deg(N, 0);

    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        edges.push_back({u, v});
        deg[u]++; deg[v]++;
    }

    vector<vector<int>> adj(N);
    for (int i = 0; i < N; i++) adj[i].reserve(deg[i]);

    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Deduplicate adjacency lists to handle multi-edges properly.
    for (int i = 0; i < N; i++) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
        deg[i] = (int)a.size();
    }

    vector<int> baseOrd(N);
    iota(baseOrd.begin(), baseOrd.end(), 0);
    sort(baseOrd.begin(), baseOrd.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] < deg[b];
        return a < b;
    });

    int W = max(5, min(200, max(1, N / 50)));

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> ord(N);

    auto generateOrder = [&](bool strongShuffle = false) {
        ord = baseOrd;
        for (int i = 0; i < N; i++) {
            int rem = N - i;
            int span = min(W, rem);
            int j = i + (int)(rng() % span);
            swap(ord[i], ord[j]);
        }
        if (strongShuffle || (rng() % 100) < 5) {
            shuffle(ord.begin(), ord.end(), rng);
        }
    };

    auto greedyFromCurrentOrd = [&](State &st) {
        st.clear();
        for (int v : ord) {
            if (!st.sel[v] && st.conf[v] == 0) st.addVertex(v, adj);
        }
    };

    auto extendMaximal = [&](State &st) {
        generateOrder(false);
        for (int v : ord) {
            if (!st.sel[v] && st.conf[v] == 0) st.addVertex(v, adj);
        }
    };

    vector<int> mark(N, 0);
    int token = 1;

    auto attemptExchangeImprove = [&](State &st) -> bool {
        if (st.selVec.empty()) return false;
        int u = st.selVec[rng() % st.selVec.size()];

        vector<int> cand;
        cand.reserve(adj[u].size());
        for (int v : adj[u]) {
            if (!st.sel[v] && st.conf[v] == 1) cand.push_back(v);
        }
        if (cand.size() < 2) return false;

        shuffle(cand.begin(), cand.end(), rng);
        if (++token == INT_MAX) {
            token = 1;
            fill(mark.begin(), mark.end(), 0);
        }
        int curTok = token;

        vector<int> chosen;
        chosen.reserve(6);
        for (int v : cand) {
            bool ok = true;
            for (int nb : adj[v]) {
                if (mark[nb] == curTok) { ok = false; break; }
            }
            if (ok) {
                mark[v] = curTok;
                chosen.push_back(v);
                if ((int)chosen.size() >= 6) break;
            }
        }
        if ((int)chosen.size() < 2) return false;

        st.removeVertex(u, adj);
        for (int v : chosen) {
            if (!st.sel[v] && st.conf[v] == 0) st.addVertex(v, adj);
        }
        return true;
    };

    auto perturb = [&](const State &src, State &dst, int R, bool strongShuffle) {
        dst = src;
        for (int i = 0; i < R && !dst.selVec.empty(); i++) {
            int idx = (int)(rng() % dst.selVec.size());
            int v = dst.selVec[idx];
            dst.removeVertex(v, adj);
        }
        generateOrder(strongShuffle);
        for (int v : ord) {
            if (!dst.sel[v] && dst.conf[v] == 0) dst.addVertex(v, adj);
        }
    };

    State best(N), current(N), tmp(N);

    ord = baseOrd;
    greedyFromCurrentOrd(current);
    best = current;

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1850);

    // Multi-start greedy
    for (int r = 0; r < 30 && chrono::steady_clock::now() < deadline; r++) {
        generateOrder(r % 10 == 0);
        greedyFromCurrentOrd(tmp);
        if (tmp.k > best.k) best = tmp;
    }
    current = best;

    // Local improvements
    while (chrono::steady_clock::now() < deadline) {
        int coin = (int)(rng() % 100);

        if (coin < 70) {
            bool improved = false;
            for (int t = 0; t < 8 && chrono::steady_clock::now() < deadline; t++) {
                if (attemptExchangeImprove(current)) {
                    extendMaximal(current);
                    if (current.k > best.k) best = current;
                    improved = true;
                    break;
                }
            }
            if (!improved && (rng() % 100) < 25) {
                int R = max(1, current.k / 90);
                R = min(R, 30);
                perturb(current, tmp, R, false);
                if (tmp.k > best.k) best = tmp;
                if (tmp.k >= current.k || (rng() % 100) < 5) current = tmp;
            }
        } else {
            int R = max(1, current.k / 55);
            R = min(R, 60);
            perturb(current, tmp, R, (rng() % 100) < 10);
            if (tmp.k > best.k) best = tmp;
            if (tmp.k >= current.k || (rng() % 100) < 10) current = tmp;
        }
    }

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(best.sel[i] ? '1' : '0');
        out.push_back('\n');
    }
    cout << out;
    return 0;
}