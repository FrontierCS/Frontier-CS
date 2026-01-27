#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;
    
    int NN = N * N;
    vector<array<int, 8>> adj_index; // store indices; unused slots set to -1
    vector<uint8_t> adj_deg; // number of neighbors per node (0..8)
    adj_index.resize(NN);
    adj_deg.resize(NN);
    
    const int dr[8] = {2,2,1,1,-1,-1,-2,-2};
    const int dc[8] = {1,-1,2,-2,2,-2,1,-1};
    
    auto inside = [&](int r, int c){ return 0 <= r && r < N && 0 <= c && c < N; };
    auto id = [&](int r, int c){ return r * N + c; };
    
    // Build adjacency
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int u = id(r, c);
            uint8_t k = 0;
            for (int m = 0; m < 8; ++m) {
                int nr = r + dr[m], nc = c + dc[m];
                if (inside(nr, nc)) {
                    adj_index[u][k++] = id(nr, nc);
                }
            }
            for (int m = k; m < 8; ++m) adj_index[u][m] = -1;
            adj_deg[u] = k;
        }
    }
    
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    
    auto attempt = [&](int start)->vector<int> {
        vector<uint8_t> visited(NN, 0);
        vector<uint8_t> deg = adj_deg; // mutable degrees (unvisited neighbor counts)
        vector<int> path;
        path.reserve(NN);
        
        int cur = start;
        visited[cur] = 1;
        path.push_back(cur);
        // Update degrees after visiting start
        for (int i = 0; i < 8; ++i) {
            int v = adj_index[cur][i];
            if (v == -1) break;
            if (!visited[v] && deg[v] > 0) --deg[v];
        }
        
        while ((int)path.size() < NN) {
            int bestMin = 9;
            int candidates[8];
            int candCnt = 0;
            // gather candidates with minimal onward degree
            for (int i = 0; i < 8; ++i) {
                int v = adj_index[cur][i];
                if (v == -1) break;
                if (visited[v]) continue;
                int d = deg[v];
                if (d < bestMin) {
                    bestMin = d;
                    candCnt = 0;
                    candidates[candCnt++] = v;
                } else if (d == bestMin) {
                    candidates[candCnt++] = v;
                }
            }
            if (candCnt == 0) break; // stuck
            
            int next = -1;
            if (candCnt == 1) {
                next = candidates[0];
            } else {
                // secondary tiebreaker: minimal minimal-degree among next's neighbors
                int bestSec = 10;
                int secCands[8];
                int secCnt = 0;
                for (int idx = 0; idx < candCnt; ++idx) {
                    int v = candidates[idx];
                    int sec = 10;
                    for (int j = 0; j < 8; ++j) {
                        int w = adj_index[v][j];
                        if (w == -1) break;
                        if (!visited[w]) {
                            sec = min<int>(sec, deg[w]);
                        }
                    }
                    if (sec < bestSec) {
                        bestSec = sec;
                        secCnt = 0;
                        secCands[secCnt++] = v;
                    } else if (sec == bestSec) {
                        secCands[secCnt++] = v;
                    }
                }
                if (secCnt == 1) next = secCands[0];
                else {
                    uniform_int_distribution<int> dist(0, secCnt - 1);
                    next = secCands[dist(rng)];
                }
            }
            
            // move
            cur = next;
            visited[cur] = 1;
            path.push_back(cur);
            for (int i = 0; i < 8; ++i) {
                int v = adj_index[cur][i];
                if (v == -1) break;
                if (!visited[v] && deg[v] > 0) --deg[v];
            }
        }
        return path;
    };
    
    // Try multiple attempts with different randomness, keep best
    vector<int> bestPath;
    int start = id(r0, c0);
    auto deadline = chrono::steady_clock::now() + chrono::milliseconds(900);
    
    for (int tries = 0; tries < 5; ++tries) {
        vector<int> p = attempt(start);
        if ((int)p.size() > (int)bestPath.size()) bestPath.swap(p);
        if ((int)bestPath.size() == NN) break;
        if (chrono::steady_clock::now() > deadline) break;
    }
    
    cout << bestPath.size() << '\n';
    for (size_t i = 0; i < bestPath.size(); ++i) {
        int u = bestPath[i];
        int r = u / N;
        int c = u % N;
        cout << (r + 1) << ' ' << (c + 1);
        if (i + 1 < bestPath.size()) cout << '\n';
    }
    return 0;
}