#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t &x) {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct RNG {
    uint64_t x;
    RNG(uint64_t seed = 1) : x(seed) {}
    uint64_t nextU64() { return splitmix64(x); }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
};

struct Item {
    int depthNew;
    int beauty;
    uint32_t rnd;
    int v;
    int parent;
};

struct ItemCmp {
    bool operator()(Item const& a, Item const& b) const {
        if (a.depthNew != b.depthNew) return a.depthNew < b.depthNew;
        if (a.beauty != b.beauty) return a.beauty < b.beauty;
        return a.rnd < b.rnd;
    }
};

static long long computeScore(const vector<int>& depth, const vector<int>& A) {
    long long s = 0;
    for (int i = 0; i < (int)A.size(); i++) s += 1LL * (depth[i] + 1) * A[i];
    return s;
}

static void normalizeAndRepair(int N, int H, vector<int>& parent, vector<int>& depth) {
    // Break cycles / unreachable by forcing them to roots
    for (int it = 0; it < 5; it++) {
        vector<vector<int>> ch(N);
        vector<int> roots;
        roots.reserve(N);
        for (int v = 0; v < N; v++) {
            int p = parent[v];
            if (p == -1) roots.push_back(v);
            else if (p >= 0 && p < N) ch[p].push_back(v);
            else parent[v] = -1;
        }
        vector<int> nd(N, -1);
        deque<int> dq;
        for (int r : roots) {
            nd[r] = 0;
            dq.push_back(r);
        }
        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            for (int c : ch[v]) {
                if (nd[c] != -1) continue;
                nd[c] = nd[v] + 1;
                dq.push_back(c);
            }
        }
        bool changed = false;
        for (int v = 0; v < N; v++) {
            if (nd[v] == -1) {
                parent[v] = -1;
                changed = true;
            }
        }
        if (!changed) {
            depth = nd;
            break;
        }
    }

    // Enforce height constraint by cutting too-deep nodes as new roots until stable
    for (int it = 0; it < 8; it++) {
        vector<vector<int>> ch(N);
        vector<int> roots;
        roots.reserve(N);
        for (int v = 0; v < N; v++) {
            int p = parent[v];
            if (p == -1) roots.push_back(v);
            else ch[p].push_back(v);
        }
        vector<int> nd(N, -1);
        deque<int> dq;
        for (int r : roots) {
            nd[r] = 0;
            dq.push_back(r);
        }
        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            for (int c : ch[v]) {
                if (nd[c] != -1) continue;
                nd[c] = nd[v] + 1;
                dq.push_back(c);
            }
        }
        bool changed = false;
        for (int v = 0; v < N; v++) {
            if (nd[v] == -1) { // should not happen but safe
                parent[v] = -1;
                changed = true;
            } else if (nd[v] > H) {
                parent[v] = -1;
                changed = true;
            }
        }
        if (!changed) {
            depth = nd;
            break;
        }
    }
}

struct Solver {
    int N, M, H;
    vector<int> A;
    vector<vector<int>> adj;
    vector<vector<int>> ball; // vertices within distance <= H in full graph
    vector<int> orderAscA, orderDescA;

    void read() {
        cin >> N >> M >> H;
        A.resize(N);
        for (int i = 0; i < N; i++) cin >> A[i];
        adj.assign(N, {});
        for (int i = 0; i < M; i++) {
            int u, v; cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // coordinates, not used
        for (int i = 0; i < N; i++) {
            int x, y; cin >> x >> y;
        }

        orderAscA.resize(N);
        iota(orderAscA.begin(), orderAscA.end(), 0);
        sort(orderAscA.begin(), orderAscA.end(), [&](int i, int j) {
            if (A[i] != A[j]) return A[i] < A[j];
            return i < j;
        });
        orderDescA = orderAscA;
        reverse(orderDescA.begin(), orderDescA.end());

        precomputeBalls();
    }

    void precomputeBalls() {
        ball.assign(N, {});
        vector<int> dist(N, -1);
        deque<int> dq;
        for (int s = 0; s < N; s++) {
            fill(dist.begin(), dist.end(), -1);
            dq.clear();
            dist[s] = 0;
            dq.push_back(s);
            while (!dq.empty()) {
                int v = dq.front(); dq.pop_front();
                if (dist[v] == H) continue;
                for (int to : adj[v]) {
                    if (dist[to] != -1) continue;
                    dist[to] = dist[v] + 1;
                    dq.push_back(to);
                }
            }
            auto &b = ball[s];
            b.reserve(N);
            for (int v = 0; v < N; v++) if (dist[v] != -1) b.push_back(v);
        }
    }

    int selectRoot(const vector<char>& assigned, RNG& rng) {
        vector<int> cand;
        cand.reserve(100);
        vector<char> used(N, 0);

        // random unassigned samples
        for (int t = 0; t < 300 && (int)cand.size() < 40; t++) {
            int v = rng.nextInt(N);
            if (assigned[v] || used[v]) continue;
            used[v] = 1;
            cand.push_back(v);
        }
        // lowest beauty unassigned
        for (int i = 0; i < N && (int)cand.size() < 90; i++) {
            int v = orderAscA[i];
            if (assigned[v] || used[v]) continue;
            used[v] = 1;
            cand.push_back(v);
        }
        if (cand.empty()) {
            for (int i = 0; i < N; i++) if (!assigned[i]) return i;
            return 0;
        }

        long long bestScore = LLONG_MIN;
        int best = cand[0];
        for (int v : cand) {
            int cover = 0;
            for (int w : ball[v]) if (!assigned[w]) cover++;
            long long sc = 1000LL * cover - 10LL * A[v] + (int)(rng.nextU32() % 1000);
            if (sc > bestScore) {
                bestScore = sc;
                best = v;
            }
        }
        return best;
    }

    void buildForestOneRun(RNG& rng, vector<int>& parent, vector<int>& depth) {
        vector<char> assigned(N, 0);
        parent.assign(N, -2);
        depth.assign(N, -1);
        int remaining = N;

        vector<int> bestParDepth(N, -1);
        vector<int> bestParVertex(N, -1);
        priority_queue<Item, vector<Item>, ItemCmp> pq;

        while (remaining > 0) {
            int r = selectRoot(assigned, rng);
            assigned[r] = 1;
            parent[r] = -1;
            depth[r] = 0;
            remaining--;

            fill(bestParDepth.begin(), bestParDepth.end(), -1);
            fill(bestParVertex.begin(), bestParVertex.end(), -1);
            while (!pq.empty()) pq.pop();

            for (int v : adj[r]) {
                if (assigned[v]) continue;
                bestParDepth[v] = 0;
                bestParVertex[v] = r;
                pq.push(Item{1, A[v], rng.nextU32(), v, r});
            }

            while (!pq.empty()) {
                Item it = pq.top(); pq.pop();
                int v = it.v;
                if (assigned[v]) continue;
                if (bestParVertex[v] != it.parent) continue;
                if (bestParDepth[v] + 1 != it.depthNew) continue;

                int p = it.parent;
                int d = it.depthNew;
                parent[v] = p;
                depth[v] = d;
                assigned[v] = 1;
                remaining--;

                if (d == H) continue;
                for (int w : adj[v]) {
                    if (assigned[w]) continue;
                    if (d > bestParDepth[w]) {
                        bestParDepth[w] = d;
                        bestParVertex[w] = v;
                        pq.push(Item{d + 1, A[w], rng.nextU32(), w, v});
                    }
                }
            }
        }
    }

    void leafImprove(RNG& rng, vector<int>& parent, vector<int>& depth, int rounds) {
        vector<int> childCnt(N, 0);
        for (int v = 0; v < N; v++) {
            int p = parent[v];
            if (p != -1) childCnt[p]++;
        }

        for (int rep = 0; rep < rounds; rep++) {
            // slight random shuffle in processing order while mostly descending A
            vector<int> ord = orderDescA;
            for (int i = 0; i + 1 < N; i++) {
                if ((rng.nextU32() & 7u) == 0) {
                    int j = i + (rng.nextU32() % (unsigned)(min(10, N - i)));
                    if (j >= N) j = N - 1;
                    swap(ord[i], ord[j]);
                }
            }

            for (int v : ord) {
                if (childCnt[v] != 0) continue; // only leaves
                int bestU = -1;
                int bestD = -1;
                for (int u : adj[v]) {
                    if (depth[u] >= H) continue;
                    int nd = depth[u] + 1;
                    if (nd <= depth[v]) continue;
                    if (depth[u] > bestD) {
                        bestD = depth[u];
                        bestU = u;
                    } else if (depth[u] == bestD && bestU != -1) {
                        if (A[u] > A[bestU] && (rng.nextU32() & 1u)) bestU = u;
                    }
                }
                if (bestU == -1) continue;
                if (parent[v] == bestU) continue;

                int old = parent[v];
                if (old != -1) childCnt[old]--;
                parent[v] = bestU;
                depth[v] = bestD + 1;
                childCnt[bestU]++;
            }
        }
    }

    void rootMergeGreedy(vector<int>& parent, vector<int>& depth) {
        // Greedily attach entire trees (their roots) under deep vertices if edge exists from root.
        while (true) {
            vector<int> rootId(N, -1);
            for (int v = 0; v < N; v++) {
                int cur = v;
                while (parent[cur] != -1) cur = parent[cur];
                rootId[v] = cur;
            }

            vector<int> roots;
            roots.reserve(N);
            for (int v = 0; v < N; v++) if (parent[v] == -1) roots.push_back(v);

            vector<long long> sumA(N, 0);
            vector<int> maxD(N, 0);
            vector<vector<int>> nodes(N);
            for (int r : roots) {
                sumA[r] = 0;
                maxD[r] = 0;
                nodes[r].clear();
            }
            for (int v = 0; v < N; v++) {
                int r = rootId[v];
                nodes[r].push_back(v);
                sumA[r] += A[v];
                maxD[r] = max(maxD[r], depth[v]);
            }

            long long bestGain = 0;
            int bestR = -1, bestU = -1, bestDelta = 0;
            for (int r : roots) {
                for (int u : adj[r]) {
                    int ru = rootId[u];
                    if (ru == r) continue;
                    int delta = depth[u] + 1;
                    if (delta + maxD[r] > H) continue;
                    long long gain = 1LL * delta * sumA[r];
                    if (gain > bestGain) {
                        bestGain = gain;
                        bestR = r;
                        bestU = u;
                        bestDelta = delta;
                    }
                }
            }

            if (bestGain <= 0) break;

            parent[bestR] = bestU;
            for (int v : nodes[bestR]) depth[v] += bestDelta;
        }
    }

    pair<long long, vector<int>> runHeuristic(uint64_t seed) {
        RNG rng(seed);

        vector<int> parent, depth;
        buildForestOneRun(rng, parent, depth);

        leafImprove(rng, parent, depth, 2);
        rootMergeGreedy(parent, depth);
        leafImprove(rng, parent, depth, 2);

        normalizeAndRepair(N, H, parent, depth);
        long long sc = computeScore(depth, A);
        return {sc, parent};
    }

    void solve() {
        using Clock = chrono::steady_clock;
        auto t0 = Clock::now();

        long long bestScore = LLONG_MIN;
        vector<int> bestParent(N, -1);

        uint64_t baseSeed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        int runs = 0;
        while (true) {
            runs++;
            uint64_t seed = baseSeed + 10007ULL * runs;
            auto [sc, par] = runHeuristic(seed);
            if (sc > bestScore) {
                bestScore = sc;
                bestParent = std::move(par);
            }

            auto now = Clock::now();
            double elapsed = chrono::duration<double>(now - t0).count();
            if (elapsed > 1.85) break;
            if (runs >= 200) break;
        }

        for (int i = 0; i < N; i++) {
            if (i) cout << ' ';
            cout << bestParent[i];
        }
        cout << '\n';
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.read();
    s.solve();
    return 0;
}