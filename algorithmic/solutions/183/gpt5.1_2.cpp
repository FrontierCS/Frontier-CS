#include <bits/stdc++.h>
using namespace std;

struct Node {
    int deg;
    uint32_t rk;
    int v;
};
struct NodeCmp {
    bool operator()(const Node &a, const Node &b) const {
        if (a.deg != b.deg) return a.deg > b.deg;      // smaller degree first
        if (a.rk != b.rk) return a.rk > b.rk;          // random tie-break
        return a.v > b.v;                              // smaller index first
    }
};

int N, M;
int WORDS;
vector<vector<int>> g;
vector<vector<uint64_t>> adjBit;
vector<int> degArr;
vector<char> removedFlag;
vector<char> inSet;
vector<uint32_t> randKey;

// For 2-swap improvement
mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
vector<int> countInS, uniqueInS, Svert;
vector<vector<int>> candOf;
vector<uint64_t> Sbit, maskC;

bool twoSwapImprove() {
    Svert.clear();
    for (int v = 0; v < N; ++v) if (inSet[v]) Svert.push_back(v);
    if (Svert.empty()) return false;

    // Build bitset of current independent set
    fill(Sbit.begin(), Sbit.end(), 0ULL);
    for (int v : Svert) {
        Sbit[v >> 6] |= (1ULL << (v & 63));
    }

    // Randomize order of vertices in the set
    shuffle(Svert.begin(), Svert.end(), rng);

    // Compute number of neighbours in S for each vertex not in S
    fill(countInS.begin(), countInS.end(), 0);
    fill(uniqueInS.begin(), uniqueInS.end(), -1);

    for (int v = 0; v < N; ++v) if (!inSet[v]) {
        int cnt = 0;
        int last = -1;
        for (int wIdx = 0; wIdx < WORDS; ++wIdx) {
            uint64_t w = adjBit[v][wIdx] & Sbit[wIdx];
            if (w) {
                int pc = __builtin_popcountll(w);
                cnt += pc;
                if (last == -1) {
                    last = (wIdx << 6) + __builtin_ctzll(w);
                }
                if (cnt > 1) break;
            }
        }
        countInS[v] = cnt;
        if (cnt == 1) uniqueInS[v] = last;
    }

    // Build candidate lists: vertices with exactly one neighbour in S
    for (int i = 0; i < N; ++i) candOf[i].clear();
    for (int v = 0; v < N; ++v) {
        if (!inSet[v] && countInS[v] == 1) {
            int u = uniqueInS[v];
            if (u >= 0) candOf[u].push_back(v);
        }
    }

    // Try to find a 2-swap improvement
    for (int u : Svert) {
        auto &cand = candOf[u];
        if ((int)cand.size() < 2) continue;

        fill(maskC.begin(), maskC.end(), 0ULL);
        for (int v : cand) {
            maskC[v >> 6] |= (1ULL << (v & 63));
        }

        shuffle(cand.begin(), cand.end(), rng);

        for (int ai = 0; ai < (int)cand.size(); ++ai) {
            int a = cand[ai];
            int aWord = a >> 6;
            uint64_t aBitMask = 1ULL << (a & 63);
            for (int wIdx = 0; wIdx < WORDS; ++wIdx) {
                uint64_t w = maskC[wIdx] & ~adjBit[a][wIdx];
                if (wIdx == aWord) w &= ~aBitMask;  // exclude a itself
                if (w) {
                    int off = __builtin_ctzll(w);
                    int b = (wIdx << 6) + off;
                    if (b >= N) continue;
                    // Perform 2-swap: remove u, add a and b
                    inSet[u] = 0;
                    inSet[a] = 1;
                    inSet[b] = 1;
                    return true;
                }
            }
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;

    g.assign(N, {});
    WORDS = (N + 63) >> 6;
    adjBit.assign(N, vector<uint64_t>(WORDS, 0ULL));

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
        adjBit[u][v >> 6] |= (1ULL << (v & 63));
        adjBit[v][u >> 6] |= (1ULL << (u & 63));
    }

    // Initial greedy MIS using min-degree heuristic
    degArr.assign(N, 0);
    removedFlag.assign(N, 0);
    inSet.assign(N, 0);
    randKey.assign(N, 0);

    for (int v = 0; v < N; ++v) {
        degArr[v] = (int)g[v].size();
        randKey[v] = (uint32_t)rng();
    }

    priority_queue<Node, vector<Node>, NodeCmp> pq;
    for (int v = 0; v < N; ++v) {
        pq.push(Node{degArr[v], randKey[v], v});
    }

    while (!pq.empty()) {
        Node cur = pq.top();
        pq.pop();
        int v = cur.v;
        if (removedFlag[v]) continue;
        if (cur.deg != degArr[v]) continue; // outdated entry

        inSet[v] = 1;
        removedFlag[v] = 1;
        for (int u : g[v]) {
            if (!removedFlag[u]) {
                removedFlag[u] = 1;
                for (int w : g[u]) {
                    if (!removedFlag[w]) {
                        --degArr[w];
                        pq.push(Node{degArr[w], randKey[w], w});
                    }
                }
            }
        }
    }

    // Prepare structures for 2-swap local search
    countInS.assign(N, 0);
    uniqueInS.assign(N, -1);
    candOf.assign(N, {});
    Svert.reserve(N);
    Sbit.assign(WORDS, 0ULL);
    maskC.assign(WORDS, 0ULL);

    const int MAX_PASSES = 20;
    for (int pass = 0; pass < MAX_PASSES; ++pass) {
        if (!twoSwapImprove()) break;
    }

    // Final re-maximization: greedily add vertices not adjacent to current set
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    shuffle(ord.begin(), ord.end(), rng);
    for (int v : ord) {
        if (inSet[v]) continue;
        bool conflict = false;
        for (int u : g[v]) {
            if (inSet[u]) {
                conflict = true;
                break;
            }
        }
        if (!conflict) inSet[v] = 1;
    }

    // Output solution
    for (int v = 0; v < N; ++v) {
        cout << (inSet[v] ? 1 : 0) << '\n';
    }

    return 0;
}