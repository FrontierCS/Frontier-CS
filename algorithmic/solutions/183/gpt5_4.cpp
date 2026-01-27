#include <bits/stdc++.h>
using namespace std;

static inline bool areNeighbors(const vector<vector<int>>& adj, int u, int v) {
    if (u == v) return true;
    if (adj[u].size() < adj[v].size()) {
        return binary_search(adj[u].begin(), adj[u].end(), v);
    } else {
        return binary_search(adj[v].begin(), adj[v].end(), u);
    }
}

static vector<char> computeMISBucket(const vector<vector<int>>& adj, mt19937 &rng) {
    int n = (int)adj.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    vector<vector<int>> buckets(n + 1);
    vector<int> pos(n, -1);
    for (int i = 0; i < n; ++i) {
        buckets[deg[i]].push_back(i);
        pos[i] = (int)buckets[deg[i]].size() - 1;
    }

    vector<char> removed(n, false);
    vector<int> order;
    order.reserve(n);

    int curMin = 0;
    int removedCount = 0;

    while (removedCount < n) {
        while (curMin <= n && buckets[curMin].empty()) ++curMin;
        if (curMin > n) break;

        auto &b = buckets[curMin];
        int idx = (int)b.size() > 1 ? (int)(rng() % b.size()) : 0;
        int u = b[idx];
        int last = b.back();
        b[idx] = last;
        pos[last] = idx;
        b.pop_back();
        pos[u] = -1;

        removed[u] = true;
        ++removedCount;
        order.push_back(u);

        for (int v : adj[u]) {
            if (!removed[v]) {
                int old = deg[v];
                auto &bOld = buckets[old];
                int idxv = pos[v];
                int lastv = bOld.back();
                bOld[idxv] = lastv;
                pos[lastv] = idxv;
                bOld.pop_back();

                deg[v] = old - 1;
                auto &bNew = buckets[old - 1];
                pos[v] = (int)bNew.size();
                bNew.push_back(v);

                if (old - 1 < curMin) curMin = old - 1;
            }
        }
    }

    vector<char> inIS(n, 0);
    for (int i = n - 1; i >= 0; --i) {
        int u = order[i];
        bool ok = true;
        for (int v : adj[u]) {
            if (inIS[v]) { ok = false; break; }
        }
        if (ok) inIS[u] = 1;
    }
    return inIS;
}

static bool try_random_1for2_improve(vector<char>& sel,
                                     vector<int>& cntSelNei,
                                     vector<int>& idxInSel,
                                     vector<int>& selList,
                                     const vector<vector<int>>& adj,
                                     mt19937& rng,
                                     int maxAttempts = 2000,
                                     int perSMaxPairs = 200) {
    if (selList.empty()) return false;
    int nSel = (int)selList.size();
    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        if (selList.empty()) return false;
        int s = selList[(size_t)rng() % selList.size()];
        const auto& neighS = adj[s];
        if (neighS.empty()) continue;

        vector<int> L;
        L.reserve(8);
        for (int u : neighS) {
            if (!sel[u] && cntSelNei[u] == 1) L.push_back(u);
        }
        int k = (int)L.size();
        if (k < 2) continue;

        int tries = perSMaxPairs;
        long long totalPairs = 1LL * k * (k - 1) / 2;
        if (totalPairs < tries) tries = (int)totalPairs;
        if (tries <= 0) continue;

        for (int it = 0; it < tries; ++it) {
            int iu = (int)(rng() % k);
            int iv = (int)(rng() % k);
            if (iu == iv) continue;
            int u = L[iu], v = L[iv];
            if (u == v) continue;
            if (!areNeighbors(adj, u, v)) {
                // apply improvement: remove s, add u and v
                sel[s] = false;
                int idxS = idxInSel[s];
                int lastNode = selList.back();
                selList[idxS] = lastNode;
                idxInSel[lastNode] = idxS;
                selList.pop_back();
                idxInSel[s] = -1;

                for (int t : adj[s]) cntSelNei[t]--;

                sel[u] = true;
                idxInSel[u] = (int)selList.size();
                selList.push_back(u);
                for (int t : adj[u]) cntSelNei[t]++;

                sel[v] = true;
                idxInSel[v] = (int)selList.size();
                selList.push_back(v);
                for (int t : adj[v]) cntSelNei[t]++;

                return true;
            }
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<int>> adj(N);
    adj.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v || u < 0 || v < 0 || u >= N || v >= N) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    for (int i = 0; i < N; ++i) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)N * 1000003ULL + (uint64_t)M * 911382323ULL;
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1850);

    vector<char> bestSel(N, 0);
    int bestK = -1;

    // Multiple randomized MIS constructions within time
    for (;;) {
        vector<char> sel = computeMISBucket(adj, rng);
        int K = 0;
        for (int i = 0; i < N; ++i) if (sel[i]) ++K;
        if (K > bestK) {
            bestK = K;
            bestSel = move(sel);
        }
        auto now = chrono::steady_clock::now();
        if (now >= deadline || bestK == N) break;
        // Heuristic cutoff on number of runs
        // Do not run too many times if time is tight
        if (chrono::duration_cast<chrono::milliseconds>(now - start).count() > 1200) break;
    }

    // Try some random 1-for-2 improvements on the best solution
    {
        vector<int> cntSelNei(N, 0);
        vector<int> selList;
        selList.reserve(bestK > 0 ? bestK : N);
        vector<int> idxInSel(N, -1);
        for (int i = 0; i < N; ++i) if (bestSel[i]) {
            idxInSel[i] = (int)selList.size();
            selList.push_back(i);
            for (int v : adj[i]) cntSelNei[v]++;
        }

        // Attempt improvements until time runs out or no more improvements are easily found
        while (chrono::steady_clock::now() < deadline) {
            bool improved = try_random_1for2_improve(bestSel, cntSelNei, idxInSel, selList, adj, rng, 1200, 150);
            if (!improved) break;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }
    return 0;
}