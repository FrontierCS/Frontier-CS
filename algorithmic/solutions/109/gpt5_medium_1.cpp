#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed) : x(seed) {}
    uint64_t next() {
        x += 0x9e3779b97f4a7c15ULL;
        uint64_t z = x;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    int n = N;
    int total = n * n;

    // Precompute neighbors for each cell
    vector<array<int, 8>> moves(total);
    vector<int> deg0(total, 0);
    auto idx = [n](int r, int c){ return r * n + c; };
    const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
    const int dc[8] = {-1,1,-2,2,-2,2,-1,1};
    vector<vector<int>> adj(total);
    adj.reserve(total);
    for(int r=0;r<n;r++){
        for(int c=0;c<n;c++){
            int id = idx(r,c);
            for(int k=0;k<8;k++){
                int nr = r + dr[k], nc = c + dc[k];
                if(nr>=0 && nr<n && nc>=0 && nc<n){
                    adj[id].push_back(idx(nr,nc));
                }
            }
            deg0[id] = (int)adj[id].size();
        }
    }

    auto attempt = [&](uint64_t seed) {
        RNG rng(seed);
        vector<uint32_t> key(total);
        for(int i=0;i<total;i++) key[i] = (uint32_t)rng.next();

        vector<int> path;
        path.reserve(total);
        vector<char> vis(total, 0);
        vector<int> deg = deg0;

        int cur = idx(r0, c0);
        vis[cur] = 1;
        path.push_back(cur);
        for(int w : adj[cur]) if(!vis[w]) --deg[w];

        for(int step = 1; step < total; ++step){
            int best = -1;
            int bestDeg = INT_MAX;
            int bestLook = INT_MAX;
            uint32_t bestKey = 0;
            // Choose next move by Warnsdorff + 1-step lookahead + random tie-breaker
            for(int v : adj[cur]){
                if(vis[v]) continue;
                int d = deg[v];
                int look = INT_MAX;
                // lookahead: minimal degree among unvisited neighbors of v
                for(int u : adj[v]){
                    if(!vis[u]){
                        look = min(look, deg[u]);
                    }
                }
                if(d < bestDeg ||
                   (d == bestDeg && look < bestLook) ||
                   (d == bestDeg && look == bestLook && key[v] < bestKey)) {
                    best = v;
                    bestDeg = d;
                    bestLook = look;
                    bestKey = key[v];
                }
            }
            if(best == -1) break; // dead end
            cur = best;
            vis[cur] = 1;
            path.push_back(cur);
            for(int w : adj[cur]) if(!vis[w]) --deg[w];
        }
        return path;
    };

    auto start_time = chrono::steady_clock::now();
    vector<int> bestPath;
    int bestLen = 0;

    // Multiple attempts with different seeds until success or time runs out
    uint64_t baseSeed = chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(r0 * 1000003 + c0 * 9176 + N * 1234567);
    for(int iter = 0; ; ++iter){
        uint64_t seed = baseSeed + (uint64_t)iter * 0x9e3779b97f4a7c15ULL;
        vector<int> path = attempt(seed);
        if((int)path.size() > bestLen){
            bestLen = (int)path.size();
            bestPath.swap(path);
            if(bestLen == total) break;
        }
        auto now = chrono::steady_clock::now();
        if(chrono::duration<double>(now - start_time).count() > 0.95) break;
    }

    cout << bestLen << '\n';
    for(int i=0;i<bestLen;i++){
        int id = bestPath[i];
        int r = id / n;
        int c = id % n;
        cout << (r+1) << ' ' << (c+1);
        if(i+1<bestLen) cout << '\n';
    }
    return 0;
}