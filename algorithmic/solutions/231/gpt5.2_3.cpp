#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
};

static inline int codeOfAnswer(const string& s) {
    if (s == "Win") return 0;
    if (s == "Lose") return 1;
    return 2; // Draw
}

struct DesignedGraph {
    int n = 0;
    int L = 0;           // number of terminals
    int D = 0;           // outdegree for non-terminals
    vector<vector<int>> out, in;
    vector<int> outdeg;
    vector<pair<int,int>> edges; // directed edges (0-based)

    void init(int n_, int L_, int D_) {
        n = n_;
        L = L_;
        D = D_;
        out.assign(n, {});
        in.assign(n, {});
        outdeg.assign(n, 0);
        edges.clear();
    }

    void addEdge(int a, int b) {
        out[a].push_back(b);
        in[b].push_back(a);
        edges.push_back({a, b});
    }

    void finalize() {
        for (int i = 0; i < n; i++) outdeg[i] = (int)out[i].size();
    }
};

static vector<uint8_t> computeTwoTokenOutcomes(const DesignedGraph& g) {
    const int n = g.n;
    const int N = n * n;

    // status: 0 unknown, 1 win, 2 lose
    vector<uint8_t> st(N, 0);
    vector<uint8_t> rem(N, 0);

    vector<int> q;
    q.reserve(N);
    size_t qh = 0;

    for (int a = 0; a < n; a++) {
        const int da = g.outdeg[a];
        const int base = a * n;
        for (int b = 0; b < n; b++) {
            int id = base + b;
            int r = da + g.outdeg[b];
            rem[id] = (uint8_t)r;
            if (r == 0) {
                st[id] = 2; // lose
                q.push_back(id);
            }
        }
    }

    while (qh < q.size()) {
        int u = q[qh++];
        int a = u / n;
        int b = u - a * n;

        if (st[u] == 2) { // lose -> predecessors are win
            for (int pa : g.in[a]) {
                int p = pa * n + b;
                if (st[p] == 0) {
                    st[p] = 1;
                    q.push_back(p);
                }
            }
            for (int pb : g.in[b]) {
                int p = a * n + pb;
                if (st[p] == 0) {
                    st[p] = 1;
                    q.push_back(p);
                }
            }
        } else { // win -> decrement predecessors, possibly become lose
            for (int pa : g.in[a]) {
                int p = pa * n + b;
                if (st[p] == 0) {
                    uint8_t &rp = rem[p];
                    if (rp > 0) rp--;
                    if (rp == 0) {
                        st[p] = 2;
                        q.push_back(p);
                    }
                }
            }
            for (int pb : g.in[b]) {
                int p = a * n + pb;
                if (st[p] == 0) {
                    uint8_t &rp = rem[p];
                    if (rp > 0) rp--;
                    if (rp == 0) {
                        st[p] = 2;
                        q.push_back(p);
                    }
                }
            }
        }
    }

    // Map: win->0, lose->1, unknown(draw)->2
    for (int i = 0; i < N; i++) {
        uint8_t s = st[i];
        if (s == 0) st[i] = 2;
        else if (s == 1) st[i] = 0;
        else st[i] = 1;
    }
    return st; // now st is outcome code 0/1/2
}

static bool selectContexts(const vector<uint8_t>& outcome, int n, int maxQ,
                           vector<int>& contexts, vector<uint64_t>& sigFinal) {
    contexts.clear();
    vector<uint64_t> sig(n, 0), newSig(n, 0);
    vector<char> used(n, 0);

    auto distinctCount = [&](const vector<uint64_t>& v) -> int {
        vector<uint64_t> tmp = v;
        sort(tmp.begin(), tmp.end());
        tmp.erase(unique(tmp.begin(), tmp.end()), tmp.end());
        return (int)tmp.size();
    };

    int curDistinct = distinctCount(sig);
    for (int step = 0; step < maxQ && curDistinct < n; step++) {
        int bestC = -1;
        int bestDistinct = -1;

        vector<uint64_t> bestNew;
        bestNew.reserve(n);

        for (int c = 0; c < n; c++) if (!used[c]) {
            for (int v = 0; v < n; v++) {
                uint8_t code = outcome[c * n + v]; // query will be (context=c, hidden=v)
                newSig[v] = (sig[v] << 2) | (uint64_t)code;
            }
            int dcnt = distinctCount(newSig);
            if (dcnt > bestDistinct) {
                bestDistinct = dcnt;
                bestC = c;
                bestNew.assign(newSig.begin(), newSig.end());
                if (bestDistinct == n) break;
            }
        }

        if (bestC == -1) break;
        used[bestC] = 1;
        contexts.push_back(bestC);
        sig.swap(bestNew);
        curDistinct = bestDistinct;
    }

    if (curDistinct != n) return false;
    sigFinal = sig;
    return true;
}

static DesignedGraph buildGraph(int n, uint64_t seed) {
    DesignedGraph g;
    int L = 30; // terminals
    int D = 3;  // outdegree for others
    g.init(n, L, D);

    SplitMix64 rng(seed);

    auto pickTarget = [&](int u) -> int {
        uint64_t r = rng.nextU64();
        int p = (int)(r % 100);
        int v;
        if (p < 12) v = (int)(r % (uint64_t)g.L);                  // terminals sometimes
        else if (p < 50) v = (int)(r % (uint64_t)n);               // anywhere
        else v = g.L + (int)(r % (uint64_t)(n - g.L));             // non-terminals
        if (v == u) v = (v + 1) % n;
        return v;
    };

    for (int u = 0; u < n; u++) {
        if (u < g.L) continue;

        int targets[3];
        int tcnt = 0;

        // Force a big directed cycle among non-terminals for guaranteed cycles.
        int cyc = g.L + ((u - g.L + 1) % (n - g.L));
        if (cyc == u) cyc = g.L + ((cyc - g.L + 1) % (n - g.L));
        targets[tcnt++] = cyc;

        while (tcnt < g.D) {
            int v = pickTarget(u);
            bool ok = true;
            for (int i = 0; i < tcnt; i++) if (targets[i] == v) { ok = false; break; }
            if (!ok) continue;
            targets[tcnt++] = v;
        }

        for (int i = 0; i < tcnt; i++) g.addEdge(u, targets[i]);
    }

    g.finalize();
    return g;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<pair<int,int>> initialEdges;
    initialEdges.reserve(m);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        initialEdges.push_back({a, b});
    }

    vector<int> contexts;
    vector<uint64_t> signatures;
    vector<uint8_t> outcome;
    DesignedGraph g;

    const int MAX_ATTEMPTS = 4;
    const int MAX_Q = 24; // keep within 64-bit signature (2 bits each => <=32)
    bool ok = false;

    for (int att = 0; att < MAX_ATTEMPTS && !ok; att++) {
        uint64_t seed = 0xC0FFEEULL + (uint64_t)att * 0x9E3779B97F4A7C15ULL;
        g = buildGraph(n, seed);
        outcome = computeTwoTokenOutcomes(g);
        ok = selectContexts(outcome, n, MAX_Q, contexts, signatures);

        if (!ok && att + 1 == MAX_ATTEMPTS) {
            // As a fallback, increase maxQ if needed (still keep <= 32).
            vector<int> ctx2;
            vector<uint64_t> sig2;
            ok = selectContexts(outcome, n, 32, ctx2, sig2);
            if (ok) {
                contexts = std::move(ctx2);
                signatures = std::move(sig2);
            }
        }
    }

    if (!ok) {
        // Extremely unlikely; fallback to querying all vertices (still within 64-bit? no).
        // Here, just choose a simple small context set; correctness not guaranteed without uniqueness.
        contexts.clear();
        for (int i = 0; i < min(n, 32); i++) contexts.push_back(i);
        // Build signatures for these contexts (may collide); we'll still build a map with first occurrence.
        signatures.assign(n, 0);
        for (int v = 0; v < n; v++) {
            uint64_t s = 0;
            for (int c : contexts) s = (s << 2) | (uint64_t)outcome[c * n + v];
            signatures[v] = s;
        }
    }

    unordered_map<uint64_t, int> sigToVertex;
    sigToVertex.reserve((size_t)n * 2);
    for (int v = 0; v < n; v++) {
        sigToVertex[signatures[v]] = v + 1; // 1-based
    }

    // Output modifications: remove all initial edges, then add our edges.
    long long K = (long long)m + (long long)g.edges.size();
    cout << K << "\n";
    for (auto [a, b] : initialEdges) {
        cout << "- " << (a + 1) << " " << (b + 1) << "\n";
    }
    for (auto [a, b] : g.edges) {
        cout << "+ " << (a + 1) << " " << (b + 1) << "\n";
    }
    cout.flush();

    const int q = (int)contexts.size();

    for (int tc = 0; tc < T; tc++) {
        uint64_t sig = 0;
        for (int i = 0; i < q; i++) {
            int c = contexts[i] + 1;
            cout << "? 1 " << c << "\n";
            cout.flush();

            string ans;
            cin >> ans;
            int code = codeOfAnswer(ans);
            sig = (sig << 2) | (uint64_t)code;
        }

        int guess = 1;
        auto it = sigToVertex.find(sig);
        if (it != sigToVertex.end()) guess = it->second;

        cout << "! " << guess << "\n";
        cout.flush();

        string verdict;
        cin >> verdict;
        if (verdict == "Wrong") return 0;
    }

    return 0;
}