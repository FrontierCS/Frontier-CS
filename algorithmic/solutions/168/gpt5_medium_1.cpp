#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    const int L = H + 1;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<vector<int>> adj(N);
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> x(N), y(N);
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];
    
    auto bfs = [&](int s, vector<int>& parent, vector<int>& dist) {
        parent.assign(N, -1);
        dist.assign(N, -1);
        queue<int> q;
        dist[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
    };
    
    auto farthest_from = [&](int s) {
        vector<int> par, dist;
        bfs(s, par, dist);
        int best = s;
        for (int i = 0; i < N; ++i) {
            if (dist[i] > dist[best]) best = i;
        }
        return best;
    };
    
    // Prepare candidate roots
    vector<int> candidates;
    auto add_cand = [&](int v) {
        if (v < 0 || v >= N) return;
        candidates.push_back(v);
    };
    add_cand(0);
    // Max/min A
    int idx_maxA = max_element(A.begin(), A.end()) - A.begin();
    int idx_minA = min_element(A.begin(), A.end()) - A.begin();
    add_cand(idx_maxA);
    add_cand(idx_minA);
    // Degree extremes
    int idx_degmax = 0;
    for (int i = 1; i < N; ++i) if (adj[i].size() > adj[idx_degmax].size()) idx_degmax = i;
    add_cand(idx_degmax);
    // Coordinate extremes
    int idx_minx = 0, idx_maxx = 0, idx_miny = 0, idx_maxy = 0;
    for (int i = 1; i < N; ++i) {
        if (x[i] < x[idx_minx]) idx_minx = i;
        if (x[i] > x[idx_maxx]) idx_maxx = i;
        if (y[i] < y[idx_miny]) idx_miny = i;
        if (y[i] > y[idx_maxy]) idx_maxy = i;
    }
    add_cand(idx_minx); add_cand(idx_maxx);
    add_cand(idx_miny); add_cand(idx_maxy);
    // Double sweep for far nodes
    int fu1 = farthest_from(0);
    int fv1 = farthest_from(fu1);
    int fw1 = farthest_from(fv1);
    add_cand(fu1); add_cand(fv1); add_cand(fw1);
    int fu2 = farthest_from(idx_degmax);
    add_cand(fu2);
    int fu3 = farthest_from(idx_maxA);
    add_cand(fu3);
    // Top-K by A
    vector<int> idxs(N);
    iota(idxs.begin(), idxs.end(), 0);
    nth_element(idxs.begin(), idxs.begin() + min(20, N), idxs.end(), [&](int i, int j){ return A[i] > A[j]; });
    int Ktop = min(20, N);
    for (int i = 0; i < Ktop; ++i) add_cand(idxs[i]);
    
    // Deduplicate candidates
    vector<int> uniq;
    vector<char> used(N, 0);
    for (int v : candidates) {
        if (!used[v]) {
            used[v] = 1;
            uniq.push_back(v);
        }
    }
    candidates.swap(uniq);
    
    long long bestScore = LLONG_MIN;
    int bestRoot = candidates.empty() ? 0 : candidates[0];
    int bestS = 0;
    vector<int> bestParentBFS, bestDist;
    
    for (int c : candidates) {
        vector<int> parent, dist;
        bfs(c, parent, dist);
        // Compute B[r]
        vector<long long> B(L, 0);
        for (int i = 0; i < N; ++i) {
            int r = dist[i] % L;
            B[r] += A[i];
        }
        // Try all s
        for (int s = 0; s < L; ++s) {
            long long score = 0;
            for (int r = 0; r < L; ++r) {
                int rem = r - s;
                if (rem < 0) rem += L;
                score += B[r] * (rem + 1);
            }
            if (score > bestScore) {
                bestScore = score;
                bestRoot = c;
                bestS = s;
                bestParentBFS = parent;
                bestDist = dist;
            }
        }
    }
    
    if (bestParentBFS.empty()) {
        bfs(bestRoot, bestParentBFS, bestDist);
    }
    
    vector<int> parentOut(N, -1);
    for (int i = 0; i < N; ++i) {
        int rem = bestDist[i] - bestS;
        rem %= L;
        if (rem < 0) rem += L;
        if (rem == 0) {
            parentOut[i] = -1;
        } else {
            parentOut[i] = bestParentBFS[i];
        }
    }
    
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << parentOut[i];
    }
    cout << '\n';
    return 0;
}