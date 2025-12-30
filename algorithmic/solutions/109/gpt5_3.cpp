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

    int total = N * N;
    auto id = [N](int r, int c){ return r * N + c; };
    auto rc = [N](int v){ return pair<int,int>(v / N, v % N); };

    // Precompute neighbors
    static const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
    static const int dc[8] = {-1,1,-2,2,-2,2,-1,1};

    vector<array<int,8>> neigh(total);
    vector<uint8_t> ncnt(total, 0);
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int v = id(r,c);
            uint8_t cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int rr = r + dr[k], cc = c + dc[k];
                if (rr >= 0 && rr < N && cc >= 0 && cc < N) {
                    neigh[v][cnt++] = id(rr, cc);
                }
            }
            ncnt[v] = cnt;
        }
    }

    // RNG: xorshift64*
    uint64_t rng_state = chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng32 = [&]()->uint32_t{
        uint64_t x = rng_state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        rng_state = x;
        return (uint32_t)((x * 2685821657736338717ULL) >> 32);
    };

    vector<int> best_path;
    best_path.reserve(total);

    vector<uint8_t> baseDeg = ncnt;
    vector<uint8_t> deg(total);
    vector<int> visited(total, 0);
    int curMark = 0;

    auto attempt = [&](int start_id, vector<int>& out_path){
        ++curMark;
        out_path.clear();
        deg = baseDeg;
        int cur = start_id;
        visited[cur] = curMark;
        out_path.push_back(cur);
        // update degrees of neighbors of start
        uint8_t cnt = ncnt[cur];
        for (uint8_t i = 0; i < cnt; ++i) {
            int nb = neigh[cur][i];
            if (visited[nb] != curMark) {
                if (deg[nb] > 0) --deg[nb];
            }
        }
        for (int step = 1; step < total; ++step) {
            uint8_t cntc = ncnt[cur];
            int minDeg = 255;
            int minPos = -1;
            // collect candidates with minimal degree
            // Also track whether there exists candidate with deg>0 if minDeg==0 to avoid early dead-ends
            vector<int> cand;
            cand.reserve(8);
            vector<int> cand_posdeg; // candidates with deg>0
            cand_posdeg.reserve(8);
            for (uint8_t i = 0; i < cntc; ++i) {
                int nb = neigh[cur][i];
                if (visited[nb] == curMark) continue;
                int d = deg[nb];
                if (d < minDeg) {
                    minDeg = d;
                }
                cand.push_back(nb);
                if (d > 0) cand_posdeg.push_back(nb);
            }
            if (cand.empty()) break;

            int chosen = -1;

            // Prefer minimal degree, but avoid choosing deg==0 if not at last move and an alternative exists
            vector<int> pool;
            if (minDeg == 0 && (int)out_path.size() + 1 < total && !cand_posdeg.empty()) {
                // Restrict pool to minimal > 0
                int best = 255;
                for (int nb : cand_posdeg) best = min(best, (int)deg[nb]);
                for (int nb : cand_posdeg) if (deg[nb] == best) pool.push_back(nb);
            } else {
                // pool = candidates with minimal degree
                for (int nb : cand) if (deg[nb] == minDeg) pool.push_back(nb);
            }

            if (pool.size() == 1) {
                chosen = pool[0];
            } else {
                // Optional second-level heuristic: pick one whose neighbors have minimal minimal degree
                int best2 = 255;
                vector<int> pool2;
                pool2.reserve(pool.size());
                for (int nb : pool) {
                    uint8_t cc = ncnt[nb];
                    int mind2 = 255;
                    for (uint8_t j = 0; j < cc; ++j) {
                        int u = neigh[nb][j];
                        if (visited[u] == curMark) continue;
                        mind2 = min(mind2, (int)deg[u]);
                    }
                    if (mind2 < best2) {
                        best2 = mind2;
                        pool2.clear();
                        pool2.push_back(nb);
                    } else if (mind2 == best2) {
                        pool2.push_back(nb);
                    }
                }
                if (!pool2.empty()) {
                    if (pool2.size() == 1) chosen = pool2[0];
                    else chosen = pool2[rng32() % pool2.size()];
                } else {
                    chosen = pool[rng32() % pool.size()];
                }
            }

            cur = chosen;
            visited[cur] = curMark;
            out_path.push_back(cur);
            // update degrees of neighbors of chosen
            uint8_t cntn = ncnt[cur];
            for (uint8_t i = 0; i < cntn; ++i) {
                int nb = neigh[cur][i];
                if (visited[nb] != curMark) {
                    if (deg[nb] > 0) --deg[nb];
                }
            }
        }
        return (int)out_path.size();
    };

    int start_id = id(r0, c0);

    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT_SEC = 0.95;

    vector<int> path;
    path.reserve(total);

    int len = attempt(start_id, path);
    best_path = path;

    if (len < total) {
        // Try more attempts with random perturbations until time runs out
        // Use modest number of retries to respect time limit
        int tries = 0;
        while (true) {
            auto t_now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(t_now - t_start).count();
            if (elapsed > TIME_LIMIT_SEC) break;
            ++tries;
            // Slight randomization: shuffle neighbor ordering indirectly by rotating dr/dc? We can't change adjacency now,
            // but randomness in tie-breaking should suffice. Just re-run.
            int l = attempt(start_id, path);
            if (l > (int)best_path.size()) best_path = path;
            if (l == total) break;
        }
    }

    cout << best_path.size() << '\n';
    for (size_t i = 0; i < best_path.size(); ++i) {
        auto [rr, cc] = rc(best_path[i]);
        cout << (rr + 1) << ' ' << (cc + 1);
        if (i + 1 < best_path.size()) cout << '\n';
    }
    return 0;
}