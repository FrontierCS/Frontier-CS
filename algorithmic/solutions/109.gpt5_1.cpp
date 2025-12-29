#include <bits/stdc++.h>
using namespace std;

static const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
static const int dc[8] = {-1,1,-2,2,-2,2,-1,1};

struct Candidate {
    int r, c;
    int deg;
    int minNextDeg;
    int centerDist;
    uint64_t rnd;
};

struct Timer {
    chrono::steady_clock::time_point start;
    Timer() { start = chrono::steady_clock::now(); }
    double elapsed_ms() const {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double, std::milli>(now - start).count();
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    const int64_t NN = (int64_t)N * (int64_t)N;
    vector<int> visitStamp((size_t)NN, 0);
    vector<pair<int,int>> bestPath;
    bestPath.reserve((size_t)NN);
    int bestLen = 0;

    auto idx = [N](int r, int c){ return r * N + c; };
    auto inside = [N](int r, int c){ return (unsigned)r < (unsigned)N && (unsigned)c < (unsigned)N; };

    auto degree = [&](int r, int c, int stamp) {
        int cnt = 0;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (inside(nr,nc) && visitStamp[idx(nr,nc)] != stamp) ++cnt;
        }
        return cnt;
    };

    auto minNextDegree = [&](int r, int c, int stamp) {
        int m = 10;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (inside(nr,nc) && visitStamp[idx(nr,nc)] != stamp) {
                int d2 = 0;
                for (int t = 0; t < 8; ++t) {
                    int rr = nr + dr[t], cc = nc + dc[t];
                    if (inside(rr,cc) && visitStamp[idx(rr,cc)] != stamp) ++d2;
                }
                if (d2 < m) m = d2;
            }
        }
        if (m == 10) m = 0;
        return m;
    };

    // Precompute center position for tie-breaking
    int cr = (N - 1) / 2;
    int cc = (N - 1) / 2;

    Timer timer;
    const double TIME_LIMIT_MS = 900.0; // leave margin under 1s
    uint64_t seedBase = chrono::high_resolution_clock::now().time_since_epoch().count();
    int attempt = 0;

    // Move orders to try (several permutations can help)
    vector<array<int,8>> moveOrders;
    {
        array<int,8> ord = {0,1,2,3,4,5,6,7};
        moveOrders.push_back(ord);
        // Some alternative orders: prioritize moves towards center or edges
        moveOrders.push_back({2,3,0,1,4,5,6,7});
        moveOrders.push_back({4,5,6,7,2,3,0,1});
        moveOrders.push_back({6,7,4,5,2,3,0,1});
        moveOrders.push_back({1,0,3,2,5,4,7,6});
    }

    while (true) {
        ++attempt;
        int stamp = attempt;
        vector<pair<int,int>> path;
        path.reserve((size_t)NN);
        int r = r0, c = c0;
        visitStamp[idx(r,c)] = stamp;
        path.emplace_back(r, c);

        // choose a move order variation per attempt
        const array<int,8>& order = moveOrders[(attempt-1) % moveOrders.size()];
        uint64_t attRnd = splitmix64(seedBase ^ (uint64_t)attempt * 0x9e3779b97f4a7c15ULL);

        bool failed = false;
        for (int step = 1; step < NN; ++step) {
            // gather unvisited neighbors
            int minDeg = 9;
            vector<Candidate> cands;
            cands.reserve(8);
            for (int t = 0; t < 8; ++t) {
                int k = order[t];
                int nr = r + dr[k], nc = c + dc[k];
                if (!inside(nr,nc)) continue;
                if (visitStamp[idx(nr,nc)] == stamp) continue;
                int d = 0;
                for (int u = 0; u < 8; ++u) {
                    int rr = nr + dr[u], cc = nc + dc[u];
                    if (inside(rr,cc) && visitStamp[idx(rr,cc)] != stamp) ++d;
                }
                if (d < minDeg) minDeg = d;
                Candidate cand;
                cand.r = nr; cand.c = nc;
                cand.deg = d;
                cand.minNextDeg = 10; // to be computed lazily if needed
                int drc = nr - cr, dcc = nc - cc;
                cand.centerDist = drc*drc + dcc*dcc;
                // Small random tie breaker
                uint64_t h = (uint64_t)nr * 1000003ULL ^ ((uint64_t)nc << 24) ^ ((uint64_t)step << 40) ^ attRnd;
                cand.rnd = splitmix64(h);
                cands.push_back(cand);
            }

            if (cands.empty()) {
                failed = true;
                break;
            }

            // filter by minimal degree (Warnsdorff)
            int cntMin = 0;
            for (auto &cd : cands) if (cd.deg == minDeg) ++cntMin;

            vector<Candidate> bests;
            bests.reserve(cands.size());
            for (auto &cd : cands) if (cd.deg == minDeg) bests.push_back(cd);

            if (bests.size() > 1) {
                // compute minNextDeg for ties
                int bestMinNext = 10;
                for (auto &cd : bests) {
                    int mnd = 10;
                    // compute min next degree lazily
                    for (int u = 0; u < 8; ++u) {
                        int rr = cd.r + dr[u], cc2 = cd.c + dc[u];
                        if (!inside(rr,cc2)) continue;
                        if (visitStamp[idx(rr,cc2)] == stamp) continue;
                        int d2 = 0;
                        for (int v = 0; v < 8; ++v) {
                            int r3 = rr + dr[v], c3 = cc2 + dc[v];
                            if (inside(r3,c3) && visitStamp[idx(r3,c3)] != stamp) ++d2;
                        }
                        if (d2 < mnd) mnd = d2;
                    }
                    if (mnd == 10) mnd = 0;
                    cd.minNextDeg = mnd;
                    if (mnd < bestMinNext) bestMinNext = mnd;
                }
                vector<Candidate> temp;
                temp.reserve(bests.size());
                for (auto &cd : bests) if (cd.minNextDeg == bestMinNext) temp.push_back(cd);
                bests.swap(temp);

                if (bests.size() > 1) {
                    // prefer closer to center (smaller centerDist)
                    int bestCenter = INT_MAX;
                    for (auto &cd : bests) if (cd.centerDist < bestCenter) bestCenter = cd.centerDist;
                    vector<Candidate> temp2;
                    temp2.reserve(bests.size());
                    for (auto &cd : bests) if (cd.centerDist == bestCenter) temp2.push_back(cd);
                    bests.swap(temp2);

                    if (bests.size() > 1) {
                        // final tie breaker: random
                        size_t idxPick = (size_t)(bests[0].rnd % bests.size());
                        r = bests[idxPick].r;
                        c = bests[idxPick].c;
                    } else {
                        r = bests[0].r;
                        c = bests[0].c;
                    }
                } else {
                    r = bests[0].r;
                    c = bests[0].c;
                }
            } else {
                // pick the only minimal deg
                for (auto &cd : cands) if (cd.deg == minDeg) { r = cd.r; c = cd.c; break; }
            }

            visitStamp[idx(r,c)] = stamp;
            path.emplace_back(r,c);
        }

        if (!failed && (int)path.size() == NN) {
            cout << path.size() << "\n";
            for (size_t i = 0; i < path.size(); ++i) {
                cout << (path[i].first + 1) << " " << (path[i].second + 1);
                if (i + 1 < path.size()) cout << "\n";
            }
            return 0;
        } else {
            if ((int)path.size() > bestLen) {
                bestLen = (int)path.size();
                bestPath = path;
            }
        }

        if (timer.elapsed_ms() > TIME_LIMIT_MS) break;
    }

    // Fallback: output best found path (valid, not necessarily full)
    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        cout << (bestPath[i].first + 1) << " " << (bestPath[i].second + 1);
        if (i + 1 < bestPath.size()) cout << "\n";
    }
    return 0;
}