#include <bits/stdc++.h>
using namespace std;

struct MultiBFSResult {
    vector<int> parent;
    vector<int> dist;
    int maxDist;
    long long score;
};

int N, M, H;
vector<int> A;
vector<vector<int>> g;

vector<int> bfs_single(int s) {
    const int INF = 1e9;
    vector<int> d(N, INF);
    deque<int> q;
    d[s] = 0;
    q.push_back(s);
    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        for (int u : g[v]) {
            if (d[u] == INF) {
                d[u] = d[v] + 1;
                q.push_back(u);
            }
        }
    }
    return d;
}

MultiBFSResult multi_bfs(const vector<int>& roots) {
    const int INF = 1e9;
    MultiBFSResult res;
    res.parent.assign(N, -1);
    res.dist.assign(N, INF);
    res.maxDist = 0;
    res.score = 0;

    deque<int> q;
    vector<int> root_of(N, -1);
    for (int r : roots) {
        if (res.dist[r] > 0) {
            res.dist[r] = 0;
            res.parent[r] = -1;
            root_of[r] = r;
            q.push_back(r);
        }
    }

    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        for (int u : g[v]) {
            if (res.dist[u] == INF) {
                res.dist[u] = res.dist[v] + 1;
                res.parent[u] = v;
                root_of[u] = root_of[v];
                q.push_back(u);
            }
        }
    }

    for (int i = 0; i < N; i++) {
        if (res.dist[i] > res.maxDist) res.maxDist = res.dist[i];
        if (res.dist[i] < (int)1e9) res.score += 1LL * A[i] * res.dist[i];
    }
    return res;
}

vector<int> farthest_first_roots(int start) {
    const int INF = 1e9;
    vector<int> roots;
    vector<int> distMin(N, INF);

    vector<int> d0 = bfs_single(start);
    for (int i = 0; i < N; i++) distMin[i] = d0[i];
    roots.push_back(start);

    while (true) {
        int maxi = -1, idx = -1;
        for (int i = 0; i < N; i++) {
            if (distMin[i] > maxi) {
                maxi = distMin[i]; idx = i;
            }
        }
        if (maxi <= H) break;
        roots.push_back(idx);
        vector<int> d = bfs_single(idx);
        for (int i = 0; i < N; i++) distMin[i] = min(distMin[i], d[i]);
    }
    return roots;
}

vector<int> refine_remove(vector<int> roots) {
    bool changed = true;
    while (changed) {
        changed = false;
        for (int i = 0; i < (int)roots.size(); i++) {
            vector<int> cand;
            cand.reserve(roots.size()-1);
            for (int j = 0; j < (int)roots.size(); j++) if (j != i) cand.push_back(roots[j]);
            MultiBFSResult res = multi_bfs(cand);
            if (res.maxDist <= H) {
                roots = move(cand);
                changed = true;
                break;
            }
        }
    }
    return roots;
}

vector<int> refine_move(vector<int> roots, long long &bestScore, vector<int> &bestParent) {
    // perform a small local search: move each root to one of its neighbors if it improves score while keeping coverage
    int K = roots.size();
    vector<char> isRoot(N, 0);
    for (int r : roots) if (r >= 0) isRoot[r] = 1;

    MultiBFSResult baseRes = multi_bfs(roots);
    if (baseRes.maxDist > H) return roots;
    bestScore = baseRes.score;
    bestParent = baseRes.parent;

    bool improved = true;
    int maxPass = 2;
    for (int pass = 0; pass < maxPass && improved; pass++) {
        improved = false;
        for (int i = 0; i < K; i++) {
            int cur = roots[i];
            long long localBest = bestScore;
            int bestPos = cur;

            // Candidate positions: current and its neighbors
            vector<int> candidates;
            candidates.push_back(cur);
            for (int nb : g[cur]) candidates.push_back(nb);

            for (int candPos : candidates) {
                if (candPos == cur) continue;
                if (isRoot[candPos]) continue; // avoid duplicate roots
                int old = roots[i];
                roots[i] = candPos;
                isRoot[old] = 0;
                isRoot[candPos] = 1;

                MultiBFSResult res = multi_bfs(roots);
                if (res.maxDist <= H && res.score > localBest) {
                    localBest = res.score;
                    bestPos = candPos;
                    bestParent = res.parent;
                }

                // revert temporary
                isRoot[candPos] = 0;
                isRoot[old] = 1;
                roots[i] = old;
            }

            if (bestPos != cur) {
                // apply best move
                isRoot[cur] = 0;
                isRoot[bestPos] = 1;
                roots[i] = bestPos;
                bestScore = localBest;
                improved = true;
            }
        }
    }
    return roots;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M >> H;
    A.resize(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    g.assign(N, {});
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; i++) {
        int u, v; cin >> u >> v;
        edges[i] = {u, v};
        g[u].push_back(v);
        g[v].push_back(u);
    }
    // read coordinates but not used
    for (int i = 0; i < N; i++) {
        int x, y; cin >> x >> y;
        (void)x; (void)y;
    }

    // Random engine
    uint64_t seed = 0x9e3779b97f4a7c15ULL;
    for (int i = 0; i < N; i++) seed ^= (uint64_t)(A[i] + 0x9e3779b97f4a7c15ULL + (seed<<6) + (seed>>2));
    mt19937_64 rng(seed);

    long long globalBestScore = LLONG_MIN;
    vector<int> globalBestParent(N, -1);

    int TRIALS = 24;
    uniform_int_distribution<int> distN(0, N-1);

    for (int t = 0; t < TRIALS; t++) {
        int start = distN(rng);
        vector<int> roots = farthest_first_roots(start);
        roots = refine_remove(roots);

        // Local search moves
        long long bestScore = LLONG_MIN;
        vector<int> bestParent(N, -1);
        roots = refine_move(roots, bestScore, bestParent);

        // Ensure we have valid result; if not, compute once
        if (bestScore == LLONG_MIN) {
            MultiBFSResult res = multi_bfs(roots);
            if (res.maxDist > H) continue;
            bestScore = res.score;
            bestParent = res.parent;
        }

        if (bestScore > globalBestScore) {
            globalBestScore = bestScore;
            globalBestParent = bestParent;
        }
    }

    if (globalBestScore == LLONG_MIN) {
        // Fallback: trivial all roots (all -1) is invalid since each vertex must belong to exactly one tree, but we can choose a spanning tree with root depth unconstrained; ensure <= H by choosing many roots: each vertex as own root.
        // Set all vertices as roots (p[v] = -1)
        for (int i = 0; i < N; i++) {
            if (i) cout << ' ';
            cout << -1;
        }
        cout << '\n';
        return 0;
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << globalBestParent[i];
    }
    cout << '\n';
    return 0;
}