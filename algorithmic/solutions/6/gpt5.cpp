#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    // Handle trivial case
    if (N == 1) {
        return vector<vector<int>>(1, vector<int>(1, 1));
    }

    // Build adjacency list
    struct Edge { int u, v; };
    vector<Edge> edges(M);
    for (int i = 0; i < M; ++i) {
        edges[i] = {A[i], B[i]};
    }
    vector<vector<pair<int,int>>> adj(N+1);
    for (int i = 0; i < M; ++i) {
        int u = edges[i].u, v = edges[i].v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    // If graph might be disconnected or have isolated nodes, note:
    // For this construction, we assume there exists a valid map (connected or special case N=1).
    // We construct a long walk W over the graph edges (possibly repeating edges) to use diagonal fill.

    // Generate trails covering all edges once using greedy walks
    vector<char> used(M, 0);
    vector<vector<int>> trails; // each as a sequence of vertices
    // A helper to find a vertex with unused edges
    auto hasUnusedEdgeAt = [&](int v)->bool{
        for (auto &p : adj[v]) if (!used[p.second]) return true;
        return false;
    };

    // Make a list of all vertices with degree > 0
    vector<int> verticesWithDeg;
    for (int v = 1; v <= N; ++v) {
        if (!adj[v].empty()) verticesWithDeg.push_back(v);
    }
    if (verticesWithDeg.empty()) {
        // No edges but N>1 -> no valid map under constraints; return simple 1xN line with same color to satisfy existence only when possible
        // However, problem guarantees existence. We'll just place a 1x1 map per safest approach for N=1 already handled.
        // Fallback: create a simple 2x2 using first color.
        int K = max(1, min(240, N));
        vector<vector<int>> C(K, vector<int>(K, 1));
        return C;
    }

    // Greedy trail decomposition
    while (true) {
        int start = -1;
        for (int v = 1; v <= N; ++v) {
            if (hasUnusedEdgeAt(v)) { start = v; break; }
        }
        if (start == -1) break;
        vector<int> path;
        int cur = start;
        path.push_back(cur);
        while (true) {
            int picked = -1;
            int nxt = -1;
            for (auto &p : adj[cur]) {
                int nb = p.first, eid = p.second;
                if (!used[eid]) { picked = eid; nxt = nb; break; }
            }
            if (picked == -1) break;
            used[picked] = 1;
            cur = nxt;
            path.push_back(cur);
        }
        trails.push_back(path);
    }

    // Build connectivity graph for BFS paths
    vector<vector<int>> simpleAdj(N+1);
    for (int i = 0; i < M; ++i) {
        int u = edges[i].u, v = edges[i].v;
        simpleAdj[u].push_back(v);
        simpleAdj[v].push_back(u);
    }

    auto bfs_path = [&](int s, int t)->vector<int> {
        vector<int> prev(N+1, -1);
        queue<int>q;
        q.push(s);
        prev[s] = s;
        while (!q.empty()) {
            int x = q.front(); q.pop();
            if (x == t) break;
            for (int y : simpleAdj[x]) {
                if (prev[y] == -1) {
                    prev[y] = x;
                    q.push(y);
                }
            }
        }
        vector<int> path;
        if (prev[t] == -1) {
            // not connected; shouldn't happen if input guarantees existence
            // Return direct s->t (invalid if no edge); but keep s only to avoid breaking
            path.push_back(s);
            return path;
        }
        int cur = t;
        while (cur != s) {
            path.push_back(cur);
            cur = prev[cur];
        }
        path.push_back(s);
        reverse(path.begin(), path.end());
        return path; // includes both s and t
    };

    // Combine trails into a single long walk W
    vector<int> W;
    if (!trails.empty()) {
        W = trails[0]; // first trail
        for (size_t i = 1; i < trails.size(); ++i) {
            int endW = W.back();
            int startT = trails[i].front();
            vector<int> bridge = bfs_path(endW, startT);
            // append bridge excluding the first node (already at end of W)
            for (size_t k = 1; k < bridge.size(); ++k) W.push_back(bridge[k]);
            // append trail i (all vertices)
            for (size_t k = 1; k < trails[i].size(); ++k) W.push_back(trails[i][k]);
        }
    }

    // Ensure all vertices with degree>0 appear in W; if not, append them via BFS from last
    vector<char> seenV(N+1, 0);
    for (int x : W) if (x>=1 && x<=N) seenV[x] = 1;
    int lastV = W.empty() ? verticesWithDeg[0] : W.back();
    for (int v = 1; v <= N; ++v) {
        if (!adj[v].empty() && !seenV[v]) {
            vector<int> bridge = bfs_path(lastV, v);
            for (size_t k = 1; k < bridge.size(); ++k) W.push_back(bridge[k]);
            lastV = v;
            seenV[v] = 1;
        }
    }

    // If W is still empty (no edges), fallback handled earlier; but just in case
    if (W.empty()) {
        int K = min(240, max(1, N));
        vector<vector<int>> C(K, vector<int>(K, 1));
        return C;
    }

    // Determine K
    // We can realize at most 2*K - 2 distinct consecutive pairs (indices), so we need length of W <= 2*K - 1
    int maxK = 240;
    int L = (int)W.size();
    int K = min(maxK, max(N, (L + 1) / 2));
    int needLen = 2 * K - 1;
    if ((int)W.size() < needLen) {
        // pad with last vertex
        int padVal = W.back();
        while ((int)W.size() < needLen) W.push_back(padVal);
    } else if ((int)W.size() > needLen) {
        // truncate if too long
        W.resize(needLen);
    }

    // Build grid with diagonal fill: C[i][j] = W[i+j]
    vector<vector<int>> C(K, vector<int>(K, 1));
    for (int i = 0; i < K; ++i) {
        for (int j = 0; j < K; ++j) {
            int idx = i + j;
            if (idx >= 0 && idx < (int)W.size()) C[i][j] = W[idx];
            else C[i][j] = W.back();
        }
    }
    return C;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) cin >> A[i] >> B[i];
        auto C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size() << (i+1==P?'\n':' ');
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}