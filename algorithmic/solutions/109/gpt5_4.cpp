#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t state;
    RNG(uint64_t s) : state(s) {}
    uint64_t next() {
        uint64_t z = (state += 0x9e3779b97f4a7c15ull);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    }
    int nextInt(int n) { return (int)(next() % n); }
};

struct KnightTour {
    int N;
    int r0, c0;
    int dr[8] = {2,1,-1,-2,-2,-1,1,2};
    int dc[8] = {1,2,2,1,-1,-2,-2,-1};

    inline bool in(int r, int c) const {
        return (unsigned)r < (unsigned)N && (unsigned)c < (unsigned)N;
    }

    vector<pair<int,int>> attempt(const vector<int>& moveOrder, bool useSecondTie, bool useCenterTie) {
        int SZ = N * N;
        vector<unsigned char> visited(SZ, 0);
        vector<unsigned char> deg(SZ, 0);

        auto id = [this](int r, int c) { return r * N + c; };
        auto applyDegInit = [&](int r, int c) {
            int cnt = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (in(nr, nc)) cnt++;
            }
            return cnt;
        };
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                deg[id(r,c)] = (unsigned char)applyDegInit(r, c);
            }
        }

        vector<pair<int,int>> path;
        path.reserve(SZ);
        int r = r0, c = c0;
        int curId = id(r,c);
        visited[curId] = 1;
        path.emplace_back(r+1, c+1); // store 1-indexed for output
        // decrease degrees of neighbors of start
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (in(nr, nc) && !visited[id(nr,nc)]) {
                unsigned char &d = deg[id(nr,nc)];
                if (d) --d;
            }
        }

        const int midr = (N - 1) / 2;
        const int midc = (N - 1) / 2;

        for (int step = 1; step < SZ; ++step) {
            int bestR = -1, bestC = -1;
            int bestDeg = 100;
            int bestDeg2 = 100;
            int bestTie = INT_MAX;

            for (int idx = 0; idx < 8; ++idx) {
                int k = moveOrder[idx];
                int nr = r + dr[k], nc = c + dc[k];
                if (!in(nr, nc)) continue;
                int nid = id(nr, nc);
                if (visited[nid]) continue;
                int d = (int)deg[nid];

                if (d < bestDeg) {
                    bestDeg = d;
                    if (useSecondTie) {
                        int mn2 = 100;
                        for (int j = 0; j < 8; ++j) {
                            int nnr = nr + dr[j], nnc = nc + dc[j];
                            if (!in(nnr, nnc)) continue;
                            int nnid = id(nnr, nnc);
                            if (visited[nnid]) continue;
                            // After visiting (nr,nc), each neighbor loses one degree due to (nr,nc) becoming visited
                            int d2 = (int)deg[nnid] - 1;
                            if (d2 < mn2) mn2 = d2;
                        }
                        bestDeg2 = mn2 == 100 ? 100 : mn2;
                    } else bestDeg2 = 100;

                    if (useCenterTie) {
                        int t = abs(nr - midr) + abs(nc - midc);
                        bestTie = t;
                    } else {
                        bestTie = idx; // fallback to move order index
                    }

                    bestR = nr; bestC = nc;
                } else if (d == bestDeg) {
                    int mn2 = 100;
                    if (useSecondTie) {
                        for (int j = 0; j < 8; ++j) {
                            int nnr = nr + dr[j], nnc = nc + dc[j];
                            if (!in(nnr, nnc)) continue;
                            int nnid = id(nnr, nnc);
                            if (visited[nnid]) continue;
                            int d2 = (int)deg[nnid] - 1;
                            if (d2 < mn2) mn2 = d2;
                        }
                    }
                    bool take = false;
                    if (!useSecondTie) {
                        // direct tie-break by center or order
                        if (useCenterTie) {
                            int t = abs(nr - midr) + abs(nc - midc);
                            if (t < bestTie) take = true;
                            else if (t == bestTie) {
                                if (idx < bestTie) take = false; // no effect, keep current
                            }
                        } else {
                            if (idx < bestTie) take = true;
                        }
                    } else {
                        if (mn2 < bestDeg2) take = true;
                        else if (mn2 == bestDeg2) {
                            if (useCenterTie) {
                                int t = abs(nr - midr) + abs(nc - midc);
                                if (t < bestTie) take = true;
                                else if (t == bestTie) {
                                    if (idx < bestTie) take = false;
                                }
                            } else {
                                if (idx < bestTie) take = true;
                            }
                        }
                    }
                    if (take) {
                        bestR = nr; bestC = nc; bestDeg2 = useSecondTie ? mn2 : bestDeg2;
                        if (useCenterTie) bestTie = abs(nr - midr) + abs(nc - midc);
                        else bestTie = idx;
                    }
                }
            }
            if (bestR == -1) break; // stuck

            // move
            r = bestR; c = bestC; curId = id(r,c);
            visited[curId] = 1;
            path.emplace_back(r+1, c+1);
            // update degrees
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (in(nr, nc) && !visited[id(nr,nc)]) {
                    unsigned char &d = deg[id(nr,nc)];
                    if (d) --d;
                }
            }
        }
        return path;
    }

    vector<pair<int,int>> solve() {
        // Create initial move order
        vector<int> baseOrder = {0,1,2,3,4,5,6,7};
        // Deterministic shuffle based on input to avoid worst-case tie patterns
        uint64_t seed = ((uint64_t)N << 40) ^ ((uint64_t)(r0+1) << 20) ^ (uint64_t)(c0+1) ^ 0x9e3779b97f4a7c15ull;
        RNG rng(seed);
        for (int i = 7; i > 0; --i) {
            int j = rng.nextInt(i + 1);
            swap(baseOrder[i], baseOrder[j]);
        }

        // Determine number of attempts based on N (more tries for small N)
        int maxTries = 1;
        if (N <= 30) maxTries = 200;
        else if (N <= 50) maxTries = 50;
        else if (N <= 100) maxTries = 10;
        else if (N <= 200) maxTries = 3;
        else maxTries = 1;

        vector<pair<int,int>> bestPath;
        int target = N * N;

        // Try combinations of tie-break strategies
        vector<pair<bool,bool>> strategies;
        strategies.push_back({true,true});
        strategies.push_back({true,false});
        strategies.push_back({false,true});
        strategies.push_back({false,false});

        int tries = 0;
        for (int s = 0; s < (int)strategies.size() && tries < maxTries; ++s) {
            // Reset order each strategy
            vector<int> order = baseOrder;
            // attempt with different permutations per try
            for (int t = 0; t < maxTries / (int)strategies.size() + 1; ++t) {
                vector<pair<int,int>> path = attempt(order, strategies[s].first, strategies[s].second);
                if ((int)path.size() > (int)bestPath.size()) bestPath = path;
                if ((int)path.size() == target) return path; // full tour found
                // rotate or reshuffle order slightly for next try
                int a = rng.nextInt(8), b = rng.nextInt(8);
                if (a != b) swap(order[a], order[b]);
                tries++;
                if (tries >= maxTries) break;
            }
        }
        return bestPath;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    KnightTour kt;
    kt.N = N;
    kt.r0 = r0;
    kt.c0 = c0;

    vector<pair<int,int>> path = kt.solve();

    cout << path.size() << '\n';
    for (size_t i = 0; i < path.size(); ++i) {
        cout << path[i].first << ' ' << path[i].second;
        if (i + 1 < path.size()) cout << '\n';
    }
    return 0;
}