#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    const int nn = N * N;

    // Move offsets for a knight
    int dr[8] = {-2,-1, 1, 2, 2, 1,-1,-2};
    int dc[8] = { 1, 2, 2, 1,-1,-2,-2,-1};

    vector<unsigned char> visited(nn, 0);
    vector<unsigned char> deg(nn, 0);
    vector<int> path;
    path.reserve(nn);

    vector<int> bestPath;
    bestPath.reserve(nn);
    int bestLen = 0;

    auto inb = [N](int r, int c){ return (unsigned)r < (unsigned)N && (unsigned)c < (unsigned)N; };
    auto idx = [N](int r, int c){ return r * N + c; };

    uint64_t rng_state = chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(N * 1315423911u);

    auto attempt = [&](int start_r, int start_c) -> int {
        // Initialize visited and degrees
        fill(visited.begin(), visited.end(), 0);
        // Compute initial degrees
        for (int r = 0; r < N; ++r) {
            int base = r * N;
            for (int c = 0; c < N; ++c) {
                int count = 0;
                for (int k = 0; k < 8; ++k) {
                    int nr = r + dr[k], nc = c + dc[k];
                    if (inb(nr,nc)) ++count;
                }
                deg[base + c] = (unsigned char)count;
            }
        }

        path.clear();
        int cur = idx(start_r, start_c);
        visited[cur] = 1;
        path.push_back(cur);
        // Decrease degrees of neighbors of start
        {
            int r = start_r, c = start_c;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (inb(nr,nc)) {
                    int v = idx(nr,nc);
                    if (!visited[v]) deg[v]--;
                }
            }
        }

        for (int step = 1; step < nn; ++step) {
            int r = cur / N, c = cur % N;
            int best = -1;
            int bestDeg = 9;
            int bestSec = 9;

            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (!inb(nr, nc)) continue;
                int v = idx(nr, nc);
                if (visited[v]) continue;

                int d = deg[v];
                if (d > bestDeg) continue;

                // Compute secondary heuristic only if needed
                int secMin = 9;
                for (int kk = 0; kk < 8; ++kk) {
                    int r2 = nr + dr[kk], c2 = nc + dc[kk];
                    if (!inb(r2, c2)) continue;
                    int w = idx(r2, c2);
                    if (visited[w]) continue;
                    int dw = deg[w];
                    if (dw < secMin) secMin = dw;
                }

                if (d < bestDeg) {
                    best = v; bestDeg = d; bestSec = secMin;
                } else if (d == bestDeg) {
                    if (secMin < bestSec) {
                        best = v; bestSec = secMin;
                    } else if (secMin == bestSec) {
                        // Random tie break
                        if ((splitmix64(rng_state) & 1ULL) == 0ULL) {
                            best = v;
                        }
                    }
                }
            }

            if (best == -1) break; // stuck
            cur = best;
            visited[cur] = 1;
            path.push_back(cur);
            int rr = cur / N, cc = cur % N;
            for (int k = 0; k < 8; ++k) {
                int nr = rr + dr[k], nc = cc + dc[k];
                if (inb(nr,nc)) {
                    int v = idx(nr,nc);
                    if (!visited[v]) deg[v]--;
                }
            }
        }

        return (int)path.size();
    };

    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 0.95; // seconds

    // First try with given move order
    int len = attempt(r0, c0);
    if (len > bestLen) {
        bestLen = len;
        bestPath = path;
        if (bestLen == nn) {
            // Full tour found
            cout << bestLen << '\n';
            for (int i = 0; i < bestLen; ++i) {
                int r = bestPath[i] / N;
                int c = bestPath[i] % N;
                cout << (r + 1) << ' ' << (c + 1) << '\n';
            }
            return 0;
        }
    }

    // Keep trying until time runs out or full tour found
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t_start).count();
        if (elapsed > TIME_LIMIT) break;

        // Randomize move order for next attempt
        array<int,8> order = {0,1,2,3,4,5,6,7};
        for (int i = 7; i > 0; --i) {
            uint64_t r = splitmix64(rng_state);
            int j = (int)(r % (i + 1));
            swap(order[i], order[j]);
        }
        int dr2[8], dc2[8];
        for (int i = 0; i < 8; ++i) {
            dr2[i] = dr[order[i]];
            dc2[i] = dc[order[i]];
        }
        for (int i = 0; i < 8; ++i) { dr[i] = dr2[i]; dc[i] = dc2[i]; }

        len = attempt(r0, c0);
        if (len > bestLen) {
            bestLen = len;
            bestPath = path;
            if (bestLen == nn) break;
        }
    }

    cout << bestLen << '\n';
    for (int i = 0; i < bestLen; ++i) {
        int r = bestPath[i] / N;
        int c = bestPath[i] % N;
        cout << (r + 1) << ' ' << (c + 1) << '\n';
    }
    return 0;
}