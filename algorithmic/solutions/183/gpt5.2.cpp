#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
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

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
};

static int N, M;
static vector<vector<int>> adj;
static vector<int> degv;

static vector<int> makeDegreeOrder(const vector<uint64_t> &rnd, bool randomTie) {
    vector<int> order(N);
    for (int i = 0; i < N; i++) order[i] = i + 1;
    if (!randomTie) {
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (degv[a] != degv[b]) return degv[a] < degv[b];
            return a < b;
        });
    } else {
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (degv[a] != degv[b]) return degv[a] < degv[b];
            if (rnd[a] != rnd[b]) return rnd[a] < rnd[b];
            return a < b;
        });
    }
    return order;
}

static void maximalizeByConflict(vector<uint8_t> &inSet, vector<int> &conflict, const vector<int> &order) {
    auto addV = [&](int x) {
        inSet[x] = 1;
        for (int y : adj[x]) conflict[y]++;
    };
    for (int v : order) {
        if (!inSet[v] && conflict[v] == 0) addV(v);
    }
}

static vector<uint8_t> improveSolution(vector<uint8_t> inSet, const vector<int> &order, int maxPasses) {
    vector<int> conflict(N + 1, 0);

    auto addV = [&](int x) {
        inSet[x] = 1;
        for (int y : adj[x]) conflict[y]++;
    };
    auto remV = [&](int x) {
        inSet[x] = 0;
        for (int y : adj[x]) conflict[y]--;
    };

    for (int v = 1; v <= N; v++) {
        if (!inSet[v]) continue;
        for (int u : adj[v]) conflict[u]++;
    }

    maximalizeByConflict(inSet, conflict, order);

    vector<int> cand;
    for (int pass = 0; pass < maxPasses; pass++) {
        bool any = false;
        for (int v : order) {
            if (inSet[v] || conflict[v] != 1) continue;

            int u = -1;
            for (int nei : adj[v]) {
                if (inSet[nei]) { u = nei; break; }
            }
            if (u == -1) continue;
            if (inSet[v] || conflict[v] != 1) continue;

            remV(u);
            if (conflict[v] != 0) {
                addV(u);
                continue;
            }
            addV(v);

            cand.clear();
            for (int w : adj[u]) {
                if (!inSet[w] && conflict[w] == 0) cand.push_back(w);
            }
            sort(cand.begin(), cand.end(), [&](int a, int b) {
                if (degv[a] != degv[b]) return degv[a] < degv[b];
                return a < b;
            });
            for (int x : cand) {
                if (!inSet[x] && conflict[x] == 0) addV(x);
            }

            any = true;
        }
        if (!any) break;
    }

    maximalizeByConflict(inSet, conflict, order);
    return inSet;
}

static vector<uint8_t> buildMinDegreeDelete(const vector<uint64_t> &tie) {
    struct Node {
        int d;
        uint64_t t;
        int v;
    };
    struct Cmp {
        bool operator()(const Node &a, const Node &b) const {
            if (a.d != b.d) return a.d > b.d;
            if (a.t != b.t) return a.t > b.t;
            return a.v > b.v;
        }
    };

    vector<uint8_t> state(N + 1, 0); // 0=undecided,1=selected,2=removed
    vector<int> curDeg(N + 1, 0);
    for (int v = 1; v <= N; v++) curDeg[v] = degv[v];

    priority_queue<Node, vector<Node>, Cmp> pq;
    pq = priority_queue<Node, vector<Node>, Cmp>();

    for (int v = 1; v <= N; v++) pq.push({curDeg[v], tie[v], v});

    while (!pq.empty()) {
        Node nd = pq.top(); pq.pop();
        int v = nd.v;
        if (state[v] != 0) continue;
        if (nd.d != curDeg[v]) continue;

        state[v] = 1; // select
        for (int u : adj[v]) {
            if (state[u] != 0) continue;
            state[u] = 2; // remove neighbor
            for (int w : adj[u]) {
                if (state[w] == 0) {
                    curDeg[w]--;
                    pq.push({curDeg[w], tie[w], w});
                }
            }
        }
    }

    vector<uint8_t> inSet(N + 1, 0);
    for (int v = 1; v <= N; v++) inSet[v] = (state[v] == 1);
    return inSet;
}

static vector<uint8_t> buildGreedy(const vector<int> &order) {
    vector<uint8_t> inSet(N + 1, 0);
    for (int v : order) {
        bool ok = true;
        for (int u : adj[v]) {
            if (inSet[u]) { ok = false; break; }
        }
        if (ok) inSet[v] = 1;
    }
    return inSet;
}

static int setSize(const vector<uint8_t> &inSet) {
    int s = 0;
    for (int i = 1; i <= N; i++) s += (int)inSet[i];
    return s;
}

static vector<uint8_t> repairAndMaximalize(vector<uint8_t> inSet, const vector<int> &order) {
    // Repair conflicts by removing one endpoint
    for (int u = 1; u <= N; u++) {
        if (!inSet[u]) continue;
        for (int v : adj[u]) {
            if (v <= u) continue;
            if (inSet[v]) {
                if (degv[u] > degv[v]) inSet[u] = 0;
                else if (degv[v] > degv[u]) inSet[v] = 0;
                else inSet[max(u, v)] = 0;
            }
        }
    }
    // Maximalize with greedy additions
    for (int v : order) {
        if (inSet[v]) continue;
        bool ok = true;
        for (int u : adj[v]) {
            if (inSet[u]) { ok = false; break; }
        }
        if (ok) inSet[v] = 1;
    }
    return inSet;
}

int main() {
    FastScanner fs;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    adj.assign(N + 1, {});
    adj.shrink_to_fit();
    adj.assign(N + 1, {});

    adj.reserve(N + 1);
    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        if (u < 1 || u > N || v < 1 || v > N) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    degv.assign(N + 1, 0);
    for (int i = 1; i <= N; i++) {
        auto &g = adj[i];
        sort(g.begin(), g.end());
        g.erase(unique(g.begin(), g.end()), g.end());
        degv[i] = (int)g.size();
    }

    SplitMix64 rng(123456789ULL);
    vector<uint64_t> rnd(N + 1, 0);
    for (int i = 1; i <= N; i++) rnd[i] = rng.nextU64();

    // Prepare ties for min-degree deletion
    vector<uint64_t> tieDet(N + 1), tieRnd(N + 1);
    for (int i = 1; i <= N; i++) {
        tieDet[i] = (uint64_t)i;
        tieRnd[i] = rnd[i];
    }

    vector<uint8_t> best(N + 1, 0);
    int bestSz = -1;

    // Common improve order: degree order with random tie
    vector<int> improveOrder = makeDegreeOrder(rnd, true);
    vector<int> degreeOrder = makeDegreeOrder(rnd, false);

    auto consider = [&](vector<uint8_t> cand) {
        int sz = setSize(cand);
        if (sz > bestSz) {
            bestSz = sz;
            best = std::move(cand);
        }
    };

    // Run 1: Min-degree deletion, deterministic tie
    {
        auto inSet = buildMinDegreeDelete(tieDet);
        inSet = improveSolution(std::move(inSet), improveOrder, 10);
        consider(std::move(inSet));
    }
    // Run 2: Min-degree deletion, randomized tie
    {
        auto inSet = buildMinDegreeDelete(tieRnd);
        inSet = improveSolution(std::move(inSet), improveOrder, 10);
        consider(std::move(inSet));
    }
    // Run 3: Greedy by degree ascending
    {
        auto inSet = buildGreedy(degreeOrder);
        inSet = improveSolution(std::move(inSet), improveOrder, 10);
        consider(std::move(inSet));
    }
    // Run 4: Greedy by random order
    {
        vector<int> order(N);
        for (int i = 0; i < N; i++) order[i] = i + 1;
        // Fisher-Yates shuffle
        for (int i = N - 1; i >= 1; i--) {
            uint64_t r = rng.nextU64();
            int j = (int)(r % (uint64_t)(i + 1));
            swap(order[i], order[j]);
        }
        auto inSet = buildGreedy(order);
        inSet = improveSolution(std::move(inSet), improveOrder, 10);
        consider(std::move(inSet));
    }

    best = repairAndMaximalize(std::move(best), improveOrder);

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 1; i <= N; i++) {
        out.push_back(best[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}