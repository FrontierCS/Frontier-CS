#include <bits/stdc++.h>
using namespace std;

static const int dr[8] = {2, 1, -1, -2, -2, -1, 1, 2};
static const int dc[8] = {1, 2, 2, 1, -1, -2, -2, -1};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    auto inb = [&](int r, int c) -> bool {
        return r >= 0 && r < N && c >= 0 && c < N;
    };

    auto idx = [&](int r, int c) -> int {
        return r * N + c;
    };

    // visited as stamped array for efficient multiple attempts on small N
    vector<int> seen(N * N, 0);
    int tag = 1;

    auto countOnward = [&](int r, int c, int tagLocal) -> int {
        int cnt = 0;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (inb(nr, nc) && seen[idx(nr, nc)] != tagLocal) ++cnt;
        }
        return cnt;
    };

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // decide number of attempts based on N
    int attempts = 1;
    if (N <= 30) attempts = 2000;
    else if (N <= 50) attempts = 500;
    else if (N <= 100) attempts = 50;
    else attempts = 1;

    vector<pair<int,int>> bestPath;
    bestPath.reserve((size_t)N * N);

    for (int attempt = 0; attempt < attempts; ++attempt) {
        int curR = r0, curC = c0;
        vector<pair<int,int>> path;
        path.reserve((size_t)N * N);
        ++tag; // new visit stamp
        if (tag == 0) { // overflow protection (practically impossible here)
            fill(seen.begin(), seen.end(), 0);
            tag = 1;
        }
        seen[idx(curR, curC)] = tag;
        path.emplace_back(curR, curC);

        while ((int)path.size() < N * N) {
            // gather candidates with minimal onward degree (Warnsdorff)
            int minDeg = 9; // max 8
            struct Cand { int r, c, deg, tieval; };
            vector<Cand> cands;
            cands.reserve(8);
            for (int k = 0; k < 8; ++k) {
                int nr = curR + dr[k], nc = curC + dc[k];
                if (!inb(nr, nc)) continue;
                int id = idx(nr, nc);
                if (seen[id] == tag) continue;
                int deg = countOnward(nr, nc, tag);
                if (deg < minDeg) {
                    minDeg = deg;
                    cands.clear();
                    cands.push_back({nr, nc, deg, 0});
                } else if (deg == minDeg) {
                    cands.push_back({nr, nc, deg, 0});
                }
            }
            if (cands.empty()) break;

            // tie-breaker: lookahead minimal onward degree from next step
            if (cands.size() > 1) {
                int bestTie = INT_MAX;
                for (auto &cand : cands) {
                    int r = cand.r, c = cand.c;
                    int secondMin = 9;
                    for (int k = 0; k < 8; ++k) {
                        int rr = r + dr[k], cc = c + dc[k];
                        if (!inb(rr, cc)) continue;
                        int id2 = idx(rr, cc);
                        if (seen[id2] == tag) continue;
                        int d2 = countOnward(rr, cc, tag);
                        if (d2 < secondMin) secondMin = d2;
                    }
                    if (secondMin == 9) secondMin = 0;
                    cand.tieval = secondMin;
                    if (secondMin < bestTie) bestTie = secondMin;
                }
                // filter by best tie value
                int write = 0;
                for (int i = 0; i < (int)cands.size(); ++i) {
                    if (cands[i].tieval == bestTie) {
                        cands[write++] = cands[i];
                    }
                }
                cands.resize(write);
            }

            // final tie-breaker: random choice among equals
            int pick = 0;
            if (cands.size() > 1) {
                uniform_int_distribution<int> dist(0, (int)cands.size() - 1);
                pick = dist(rng);
            }
            auto nxt = cands[pick];
            curR = nxt.r; curC = nxt.c;
            seen[idx(curR, curC)] = tag;
            path.emplace_back(curR, curC);
        }

        if (path.size() > bestPath.size()) bestPath = path;
        if ((int)bestPath.size() == N * N) break;
    }

    // Build output
    string out;
    out.reserve((size_t)bestPath.size() * 16 + 32);
    out += to_string((int)bestPath.size());
    out += '\n';
    for (size_t i = 0; i < bestPath.size(); ++i) {
        out += to_string(bestPath[i].first + 1);
        out += ' ';
        out += to_string(bestPath[i].second + 1);
        if (i + 1 < bestPath.size()) out += '\n';
    }
    cout << out;
    return 0;
}