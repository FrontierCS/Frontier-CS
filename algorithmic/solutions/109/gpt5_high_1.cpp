#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int sr, sc;
    cin >> sr >> sc;
    --sr; --sc;

    const int dx[8] = {2,1,-1,-2,-2,-1,1,2};
    const int dy[8] = {1,2,2,1,-1,-2,-2,-1};

    auto inside = [&](int x, int y)->bool {
        return (unsigned)x < (unsigned)N && (unsigned)y < (unsigned)N;
    };

    const long long T = 1LL * N * N;

    vector<pair<int,int>> bestPath;
    bestPath.reserve(T);
    long long bestLen = 0;

    // Pre-generate a set of move orders to try (deterministic variety)
    vector<array<int,8>> orders;
    {
        array<int,8> base = {0,1,2,3,4,5,6,7};
        // Rotations
        for (int s = 0; s < 8; ++s) {
            array<int,8> ord;
            for (int i = 0; i < 8; ++i) ord[i] = base[(i + s) % 8];
            orders.push_back(ord);
        }
        // Reverse
        array<int,8> rev = base;
        reverse(rev.begin(), rev.end());
        orders.push_back(rev);
        // Alternating
        array<int,8> alt1 = {0,2,4,6,1,3,5,7};
        array<int,8> alt2 = {1,3,5,7,0,2,4,6};
        orders.push_back(alt1);
        orders.push_back(alt2);
        // Some manual permutations
        orders.push_back({0,1,4,5,2,3,6,7});
        orders.push_back({2,3,6,7,0,1,4,5});
        orders.push_back({1,0,3,2,5,4,7,6});
        orders.push_back({4,5,6,7,0,1,2,3});
    }

    auto attempt = [&](const array<int,8>& ord)->vector<pair<int,int>> {
        vector<unsigned char> vis(1LL*N*N, 0);
        vector<pair<int,int>> path;
        path.reserve(T);

        auto idx = [&](int x, int y)->int { return x * N + y; };

        int x = sr, y = sc;
        vis[idx(x,y)] = 1;
        path.emplace_back(x,y);

        auto deg_count = [&](int ux, int uy)->int {
            int d = 0;
            for (int k = 0; k < 8; ++k) {
                int vx = ux + dx[ord[k]];
                int vy = uy + dy[ord[k]];
                if (inside(vx, vy) && !vis[idx(vx, vy)]) ++d;
            }
            return d;
        };

        for (long long step = 1; step < T; ++step) {
            int candx[8], candy[8], cdeg[8], cdd[8];
            bool bad[8];
            int cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int nx = x + dx[ord[k]];
                int ny = y + dy[ord[k]];
                if (inside(nx, ny) && !vis[idx(nx, ny)]) {
                    candx[cnt] = nx;
                    candy[cnt] = ny;
                    int d0 = 0;
                    for (int t = 0; t < 8; ++t) {
                        int tx = nx + dx[ord[t]];
                        int ty = ny + dy[ord[t]];
                        if (inside(tx, ty) && !vis[idx(tx, ty)]) ++d0;
                    }
                    cdeg[cnt] = d0;
                    // secondary lookahead: minimal onward degree
                    int minNext = 9;
                    for (int t = 0; t < 8; ++t) {
                        int tx = nx + dx[ord[t]];
                        int ty = ny + dy[ord[t]];
                        if (inside(tx, ty) && !vis[idx(tx, ty)]) {
                            int d2 = 0;
                            for (int u = 0; u < 8; ++u) {
                                int sx = tx + dx[ord[u]];
                                int sy = ty + dy[ord[u]];
                                if (inside(sx, sy) && !vis[idx(sx, sy)]) ++d2;
                            }
                            if (d2 < minNext) minNext = d2;
                        }
                    }
                    if (minNext == 9) minNext = 0;
                    cdd[cnt] = minNext;
                    bad[cnt] = (d0 == 0 && step + 1 < T);
                    ++cnt;
                }
            }

            if (cnt == 0) break; // dead end

            bool haveGood = false;
            for (int i = 0; i < cnt; ++i) if (!bad[i]) { haveGood = true; break; }

            int besti = -1;
            int best_deg = INT_MAX;
            int best_dd = INT_MAX;

            for (int i = 0; i < cnt; ++i) {
                if (haveGood && bad[i]) continue;
                int d0 = cdeg[i];
                int d1 = cdd[i];
                if (d0 < best_deg || (d0 == best_deg && d1 < best_dd)) {
                    best_deg = d0;
                    best_dd = d1;
                    besti = i;
                }
            }

            if (besti == -1) break;

            x = candx[besti];
            y = candy[besti];
            vis[idx(x,y)] = 1;
            path.emplace_back(x,y);
        }

        return path;
    };

    // Try multiple orders, keep the longest path
    for (size_t i = 0; i < orders.size(); ++i) {
        auto path = attempt(orders[i]);
        if ((long long)path.size() > bestLen) {
            bestLen = (long long)path.size();
            bestPath.swap(path);
        }
        if (bestLen == T) break;
    }

    // Fallback: if still not full, try a few randomized permutations deterministically seeded
    if (bestLen < T) {
        std::mt19937 rng( (uint32_t)(146527 + 19260817 * (sr+1) + 911382323 * (sc+1) + 972663749 * N) );
        for (int tries = 0; tries < 8 && bestLen < T; ++tries) {
            array<int,8> ord = {0,1,2,3,4,5,6,7};
            shuffle(ord.begin(), ord.end(), rng);
            auto path = attempt(ord);
            if ((long long)path.size() > bestLen) {
                bestLen = (long long)path.size();
                bestPath.swap(path);
            }
        }
    }

    cout << bestPath.size() << '\n';
    for (size_t i = 0; i < bestPath.size(); ++i) {
        cout << (bestPath[i].first + 1) << ' ' << (bestPath[i].second + 1);
        if (i + 1 < bestPath.size()) cout << '\n';
    }
    return 0;
}