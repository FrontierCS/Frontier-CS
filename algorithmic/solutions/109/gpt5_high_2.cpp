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

    const int dr[8] = {2, 1, -1, -2, -2, -1, 1, 2};
    const int dc[8] = {1, 2, 2, 1, -1, -2, -2, -1};

    const int V = N * N;

    auto inside = [&](int r, int c) {
        return (unsigned)r < (unsigned)N && (unsigned)c < (unsigned)N;
    };

    // Precompute initial degrees
    vector<uint8_t> init_deg(V, 0);
    for (int id = 0; id < V; ++id) {
        int r = id / N, c = id % N;
        uint8_t cnt = 0;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (inside(nr, nc)) ++cnt;
        }
        init_deg[id] = cnt;
    }

    vector<uint8_t> deg(V);
    vector<uint8_t> vis(V, 0);
    vector<int> path;
    path.reserve(V);

    vector<int> bestPath;
    bestPath.reserve(V);
    int bestLen = 0;

    auto now = chrono::steady_clock::now;
    auto startTime = now();
    auto deadline = startTime + chrono::milliseconds(900); // Time budget

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ ((uint64_t)N<<32) ^ ((uint64_t)r0<<16) ^ (uint64_t)c0);

    int attempts = 0;
    while (now() < deadline && bestLen < V) {
        ++attempts;

        // Randomize direction order for this attempt
        array<int,8> perm = {0,1,2,3,4,5,6,7};
        shuffle(perm.begin(), perm.end(), rng);

        // Reset state
        deg = init_deg;
        fill(vis.begin(), vis.end(), 0);
        path.clear();

        int cur = r0 * N + c0;
        vis[cur] = 1;
        path.push_back(cur);
        {
            int r = r0, c = c0;
            for (int t = 0; t < 8; ++t) {
                int nr = r + dr[t], nc = c + dc[t];
                if (inside(nr, nc)) {
                    int nid = nr * N + nc;
                    if (!vis[nid]) {
                        if (deg[nid] > 0) deg[nid]--;
                    }
                }
            }
        }

        bool ok = true;
        while ((int)path.size() < V) {
            int r = cur / N, c = cur % N;

            // Find minimal degree among neighbors (avoid choosing 0 if there is >0 and we are not at last step)
            int rem = V - (int)path.size();
            int minNonZero = 10, minAll = 10;

            for (int idx = 0; idx < 8; ++idx) {
                int k = perm[idx];
                int nr = r + dr[k], nc = c + dc[k];
                if (!inside(nr, nc)) continue;
                int nid = nr * N + nc;
                if (vis[nid]) continue;
                int d = deg[nid];
                if (d < minAll) minAll = d;
                if (d > 0 && d < minNonZero) minNonZero = d;
            }
            int targetMin = (rem > 1 && minNonZero <= 8) ? minNonZero : minAll;
            if (targetMin > 8) { ok = false; break; }

            int best = -1;
            int bestTie = 10;

            for (int idx = 0; idx < 8; ++idx) {
                int k = perm[idx];
                int nr = r + dr[k], nc = c + dc[k];
                if (!inside(nr, nc)) continue;
                int nid = nr * N + nc;
                if (vis[nid]) continue;
                int d = deg[nid];
                if (d != targetMin) continue;

                // Tie-breaker: minimal onward degree of neighbors (two-step lookahead)
                int tieMin = 10;
                if (rem > 1) {
                    int rr = nr, cc = nc;
                    for (int jdx = 0; jdx < 8; ++jdx) {
                        int j = perm[jdx];
                        int rr2 = rr + dr[j], cc2 = cc + dc[j];
                        if (!inside(rr2, cc2)) continue;
                        int wid = rr2 * N + cc2;
                        if (vis[wid]) continue;
                        int dw = deg[wid];
                        if (dw < tieMin) tieMin = dw;
                    }
                    if (tieMin > 8) tieMin = 9; // no onward moves (shouldn't happen unless rem==1)
                } else {
                    tieMin = 0;
                }

                if (best == -1 || tieMin < bestTie) {
                    best = nid;
                    bestTie = tieMin;
                }
            }

            if (best == -1) { ok = false; break; }

            cur = best;
            vis[cur] = 1;
            path.push_back(cur);

            // Update degrees of neighbors
            int rr = cur / N, cc = cur % N;
            for (int t = 0; t < 8; ++t) {
                int nr = rr + dr[t], nc = cc + dc[t];
                if (!inside(nr, nc)) continue;
                int nid = nr * N + nc;
                if (!vis[nid]) {
                    if (deg[nid] > 0) deg[nid]--;
                }
            }
        }

        if ((int)path.size() > bestLen) {
            bestLen = (int)path.size();
            bestPath = path;
        }
        if (bestLen == V) break;
    }

    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        int id = bestPath[i];
        int r = id / N + 1, c = id % N + 1;
        cout << r << ' ' << c << (i + 1 == bestLen ? '\n' : '\n');
    }

    return 0;
}