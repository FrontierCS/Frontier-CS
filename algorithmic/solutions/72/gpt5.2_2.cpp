#include <bits/stdc++.h>
using namespace std;

struct VehicleInfo {
    int len = 0;
    bool vertical = false; // false = horizontal
};

static inline uint64_t setPos(uint64_t code, int idx1, int r, int c) {
    int shift = (idx1 - 1) * 6;
    uint64_t mask = (uint64_t)63 << shift;
    uint64_t val = (uint64_t)(c | (r << 3)) << shift;
    return (code & ~mask) | val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int grid[6][6];
    int maxId = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (!(cin >> grid[r][c])) return 0;
            maxId = max(maxId, grid[r][c]);
        }
    }
    int n = maxId;
    vector<vector<pair<int,int>>> cells(n + 1);
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            int id = grid[r][c];
            if (id > 0) cells[id].push_back({r, c});
        }
    }

    vector<VehicleInfo> info(n + 1);
    vector<int> initR(n + 1, 0), initC(n + 1, 0);

    for (int id = 1; id <= n; id++) {
        int mnR = 10, mnC = 10, mxR = -1, mxC = -1;
        for (auto [r, c] : cells[id]) {
            mnR = min(mnR, r); mnC = min(mnC, c);
            mxR = max(mxR, r); mxC = max(mxC, c);
        }
        int cnt = (int)cells[id].size();
        info[id].len = cnt;
        info[id].vertical = (mxR > mnR);
        initR[id] = mnR;
        initC[id] = mnC;
    }

    uint64_t start = 0;
    for (int id = 1; id <= n; id++) {
        uint64_t v = (uint64_t)(initC[id] | (initR[id] << 3));
        start |= (v << ((id - 1) * 6));
    }

    unordered_map<uint64_t, int> dist;
    dist.reserve(1 << 20);
    dist.max_load_factor(0.7f);

    vector<uint64_t> q;
    q.reserve(1 << 20);
    q.push_back(start);
    dist.emplace(start, 0);

    vector<int> rpos(n + 1), cpos(n + 1);
    array<int, 36> occ{};

    int answer = -1;
    for (size_t qi = 0; qi < q.size(); qi++) {
        uint64_t code = q[qi];
        int d = dist[code];

        for (int id = 1; id <= n; id++) {
            uint64_t v = (code >> ((id - 1) * 6)) & 63ULL;
            cpos[id] = (int)(v & 7ULL);
            rpos[id] = (int)((v >> 3) & 7ULL);
        }

        if (cpos[1] == 6) { // red car fully out
            answer = d;
            break;
        }

        occ.fill(0);
        for (int id = 1; id <= n; id++) {
            int rr = rpos[id], cc = cpos[id];
            int len = info[id].len;
            if (!info[id].vertical) {
                for (int k = 0; k < len; k++) {
                    int c = cc + k;
                    if (0 <= rr && rr < 6 && 0 <= c && c < 6) occ[rr * 6 + c] = id;
                }
            } else {
                for (int k = 0; k < len; k++) {
                    int r = rr + k;
                    if (0 <= r && r < 6 && 0 <= cc && cc < 6) occ[r * 6 + cc] = id;
                }
            }
        }

        for (int id = 1; id <= n; id++) {
            int rr = rpos[id], cc = cpos[id], len = info[id].len;
            if (!info[id].vertical) {
                // Left
                if (cc > 0) {
                    int checkc = cc - 1;
                    if (checkc >= 0 && occ[rr * 6 + checkc] == 0) {
                        uint64_t nxt = setPos(code, id, rr, cc - 1);
                        auto it = dist.find(nxt);
                        if (it == dist.end()) {
                            dist.emplace(nxt, d + 1);
                            q.push_back(nxt);
                        }
                    }
                }
                // Right
                if (id == 1) {
                    if (cc < 6) {
                        int checkc = cc + len;
                        bool ok = true;
                        if (checkc < 6) {
                            if (occ[rr * 6 + checkc] != 0) ok = false;
                        }
                        if (ok) {
                            uint64_t nxt = setPos(code, id, rr, cc + 1);
                            auto it = dist.find(nxt);
                            if (it == dist.end()) {
                                dist.emplace(nxt, d + 1);
                                q.push_back(nxt);
                            }
                        }
                    }
                } else {
                    if (cc + len < 6) {
                        int checkc = cc + len;
                        if (occ[rr * 6 + checkc] == 0) {
                            uint64_t nxt = setPos(code, id, rr, cc + 1);
                            auto it = dist.find(nxt);
                            if (it == dist.end()) {
                                dist.emplace(nxt, d + 1);
                                q.push_back(nxt);
                            }
                        }
                    }
                }
            } else {
                // Up
                if (rr > 0) {
                    int checkr = rr - 1;
                    if (occ[checkr * 6 + cc] == 0) {
                        uint64_t nxt = setPos(code, id, rr - 1, cc);
                        auto it = dist.find(nxt);
                        if (it == dist.end()) {
                            dist.emplace(nxt, d + 1);
                            q.push_back(nxt);
                        }
                    }
                }
                // Down
                if (rr + len < 6) {
                    int checkr = rr + len;
                    if (occ[checkr * 6 + cc] == 0) {
                        uint64_t nxt = setPos(code, id, rr + 1, cc);
                        auto it = dist.find(nxt);
                        if (it == dist.end()) {
                            dist.emplace(nxt, d + 1);
                            q.push_back(nxt);
                        }
                    }
                }
            }
        }
    }

    if (answer < 0) answer = 0;
    cout << answer << " " << 0 << "\n";
    return 0;
}