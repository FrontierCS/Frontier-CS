#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horiz;   // true: horizontal, false: vertical
    int len;      // 2 or 3
    int fixed;    // row if horiz, col if vertical
};

static inline uint64_t encodeState(const vector<int>& pos, int n) {
    uint64_t code = 0;
    for (int i = 1; i <= n; i++) {
        code |= (uint64_t)(pos[i] & 7) << (3 * (i - 1));
    }
    return code;
}

static inline void decodeState(uint64_t code, vector<int>& pos, int n) {
    for (int i = 1; i <= n; i++) pos[i] = (int)((code >> (3 * (i - 1))) & 7ULL);
}

static int solveMinSteps(const vector<Vehicle>& veh, int n, uint64_t startCode) {
    vector<int> pos(n + 1);
    vector<int> npos(n + 1);

    unordered_map<uint64_t, int> dist;
    dist.reserve(1 << 18);
    dist.max_load_factor(0.7f);

    queue<uint64_t> q;
    dist[startCode] = 0;
    q.push(startCode);

    while (!q.empty()) {
        uint64_t code = q.front();
        q.pop();
        int d = dist[code];

        decodeState(code, pos, n);
        if (pos[1] == 6) return d;

        int grid[6][6];
        for (int r = 0; r < 6; r++)
            for (int c = 0; c < 6; c++)
                grid[r][c] = 0;

        for (int i = 1; i <= n; i++) {
            if (i == 1 && pos[i] == 6) continue; // red car already out
            const auto& v = veh[i];
            if (v.horiz) {
                int r = v.fixed;
                int c0 = pos[i];
                for (int k = 0; k < v.len; k++) {
                    int c = c0 + k;
                    if (0 <= c && c < 6) grid[r][c] = i;
                }
            } else {
                int c = v.fixed;
                int r0 = pos[i];
                for (int k = 0; k < v.len; k++) {
                    int r = r0 + k;
                    if (0 <= r && r < 6) grid[r][c] = i;
                }
            }
        }

        for (int i = 1; i <= n; i++) {
            if (i == 1 && pos[i] == 6) continue;
            const auto& v = veh[i];
            npos = pos;

            if (v.horiz) {
                int r = v.fixed;
                int c0 = pos[i];

                // Left
                if (c0 > 0 && grid[r][c0 - 1] == 0) {
                    npos[i] = c0 - 1;
                    uint64_t nc = encodeState(npos, n);
                    if (!dist.count(nc)) {
                        dist[nc] = d + 1;
                        q.push(nc);
                    }
                }

                // Right
                if (i == 1) {
                    if (c0 < 6) {
                        bool ok = true;
                        int front = c0 + v.len;
                        if (front <= 5) {
                            if (grid[r][front] != 0) ok = false;
                        }
                        if (ok) {
                            npos[i] = c0 + 1;
                            uint64_t nc = encodeState(npos, n);
                            if (!dist.count(nc)) {
                                dist[nc] = d + 1;
                                q.push(nc);
                            }
                        }
                    }
                } else {
                    int front = c0 + v.len;
                    if (front <= 5 && grid[r][front] == 0) {
                        npos[i] = c0 + 1;
                        uint64_t nc = encodeState(npos, n);
                        if (!dist.count(nc)) {
                            dist[nc] = d + 1;
                            q.push(nc);
                        }
                    }
                }
            } else {
                int c = v.fixed;
                int r0 = pos[i];

                // Up
                if (r0 > 0 && grid[r0 - 1][c] == 0) {
                    npos[i] = r0 - 1;
                    uint64_t nc = encodeState(npos, n);
                    if (!dist.count(nc)) {
                        dist[nc] = d + 1;
                        q.push(nc);
                    }
                }

                // Down
                int front = r0 + v.len;
                if (front <= 5 && grid[front][c] == 0) {
                    npos[i] = r0 + 1;
                    uint64_t nc = encodeState(npos, n);
                    if (!dist.count(nc)) {
                        dist[nc] = d + 1;
                        q.push(nc);
                    }
                }
            }
        }
    }

    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    int n = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (!(cin >> board[r][c])) return 0;
            n = max(n, board[r][c]);
        }
    }

    vector<vector<pair<int,int>>> cells(n + 1);
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            int id = board[r][c];
            if (id > 0) cells[id].push_back({r, c});
        }
    }

    vector<Vehicle> veh(n + 1);
    vector<int> pos(n + 1, 0);

    for (int id = 1; id <= n; id++) {
        int minr = 6, maxr = -1, minc = 6, maxc = -1;
        for (auto [r, c] : cells[id]) {
            minr = min(minr, r); maxr = max(maxr, r);
            minc = min(minc, c); maxc = max(maxc, c);
        }
        bool horiz = (minr == maxr);
        int len = horiz ? (maxc - minc + 1) : (maxr - minr + 1);
        int fixed = horiz ? minr : minc;
        int start = horiz ? minc : minr;

        veh[id] = {horiz, len, fixed};
        pos[id] = start;
    }

    uint64_t startCode = encodeState(pos, n);
    int minSteps = solveMinSteps(veh, n, startCode);
    if (minSteps < 0) minSteps = 0;

    cout << minSteps << " " << 0 << "\n";
    return 0;
}