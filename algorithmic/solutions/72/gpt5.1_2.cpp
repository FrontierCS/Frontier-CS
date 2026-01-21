#include <bits/stdc++.h>
using namespace std;

const int MAXV = 10;

int gN;
bool gHoriz[MAXV];
int gLen[MAXV];
int gFix[MAXV];   // row for horizontal, col for vertical
int gStart[MAXV];

uint64_t encodeState(const vector<int>& pos) {
    uint64_t key = 0;
    for (int i = 0; i < gN; ++i) {
        key |= (uint64_t(pos[i] & 0xF) << (i * 4));
    }
    return key;
}

void decodeState(uint64_t key, vector<int>& pos) {
    for (int i = 0; i < gN; ++i) {
        pos[i] = int((key >> (i * 4)) & 0xF);
    }
}

int bfs_min_steps() {
    vector<int> pos(gN), newPos(gN);
    for (int i = 0; i < gN; ++i) pos[i] = gStart[i];

    uint64_t startKey = encodeState(pos);

    unordered_map<uint64_t, int> dist;
    dist.reserve(200000);
    dist.max_load_factor(0.7f);

    queue<uint64_t> q;
    q.push(startKey);
    dist[startKey] = 0;

    while (!q.empty()) {
        uint64_t key = q.front();
        q.pop();
        int d = dist[key];
        decodeState(key, pos);

        // Build occupancy grid
        int occ[6][6];
        memset(occ, 0, sizeof(occ));
        for (int i = 0; i < gN; ++i) {
            int len = gLen[i];
            if (gHoriz[i]) {
                int row = gFix[i];
                int L = pos[i];
                for (int k = 0; k < len; ++k) {
                    int c = L + k;
                    if (c >= 0 && c < 6 && row >= 0 && row < 6) {
                        occ[row][c] = i + 1;
                    }
                }
            } else {
                int col = gFix[i];
                int R = pos[i];
                for (int k = 0; k < len; ++k) {
                    int r = R + k;
                    if (r >= 0 && r < 6 && col >= 0 && col < 6) {
                        occ[r][col] = i + 1;
                    }
                }
            }
        }

        // Generate moves
        for (int i = 0; i < gN; ++i) {
            int len = gLen[i];

            if (gHoriz[i]) {
                int row = gFix[i];
                int L = pos[i];

                // Move left
                {
                    int newL = L - 1;
                    if (newL >= 0) {
                        int checkCol = newL;
                        if (row >= 0 && row < 6 && checkCol >= 0 && checkCol < 6 &&
                            occ[row][checkCol] == 0) {
                            newPos = pos;
                            newPos[i] = newL;
                            uint64_t k2 = encodeState(newPos);
                            if (!dist.count(k2)) {
                                dist[k2] = d + 1;
                                q.push(k2);
                            }
                        }
                    }
                }

                // Move right
                {
                    int newL = L + 1;
                    int enterCol = L + len; // new front cell inside board if <6

                    if (i == 0) { // red car
                        if (enterCol <= 7) { // allow up to column 7 (off-board extension)
                            bool blocked = false;
                            if (enterCol < 6) {
                                if (row >= 0 && row < 6 &&
                                    occ[row][enterCol] != 0) {
                                    blocked = true;
                                }
                            }
                            if (!blocked) {
                                if (newL >= 6) {
                                    // red car totally out
                                    return d + 1;
                                } else {
                                    newPos = pos;
                                    newPos[i] = newL;
                                    uint64_t k2 = encodeState(newPos);
                                    if (!dist.count(k2)) {
                                        dist[k2] = d + 1;
                                        q.push(k2);
                                    }
                                }
                            }
                        }
                    } else { // other horizontal vehicles
                        if (enterCol < 6) {
                            if (row >= 0 && row < 6 &&
                                occ[row][enterCol] == 0) {
                                newPos = pos;
                                newPos[i] = newL;
                                uint64_t k2 = encodeState(newPos);
                                if (!dist.count(k2)) {
                                    dist[k2] = d + 1;
                                    q.push(k2);
                                }
                            }
                        }
                    }
                }
            } else { // vertical
                int col = gFix[i];
                int R = pos[i];

                // Move up
                {
                    int newR = R - 1;
                    if (newR >= 0) {
                        int checkRow = newR;
                        if (checkRow >= 0 && checkRow < 6 &&
                            col >= 0 && col < 6 &&
                            occ[checkRow][col] == 0) {
                            newPos = pos;
                            newPos[i] = newR;
                            uint64_t k2 = encodeState(newPos);
                            if (!dist.count(k2)) {
                                dist[k2] = d + 1;
                                q.push(k2);
                            }
                        }
                    }
                }

                // Move down
                {
                    int newR = R + 1;
                    int enterRow = R + len; // new front cell after moving down
                    if (enterRow < 6) {
                        if (enterRow >= 0 && enterRow < 6 &&
                            col >= 0 && col < 6 &&
                            occ[enterRow][col] == 0) {
                            newPos = pos;
                            newPos[i] = newR;
                            uint64_t k2 = encodeState(newPos);
                            if (!dist.count(k2)) {
                                dist[k2] = d + 1;
                                q.push(k2);
                            }
                        }
                    }
                }
            }
        }
    }

    // Should not happen (puzzles are guaranteed solvable)
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    vector<pair<int,int>> cells[MAXV + 1];

    int n = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int v;
            if (!(cin >> v)) return 0;
            board[r][c] = v;
            if (v > 0 && v <= MAXV) {
                n = max(n, v);
                cells[v].push_back({r, c});
            }
        }
    }

    gN = n;
    for (int id = 1; id <= n; ++id) {
        auto &ps = cells[id];
        int idx = id - 1;
        int len = (int)ps.size();
        gLen[idx] = len;

        if (len >= 2 && ps[0].first == ps[1].first) {
            // horizontal
            gHoriz[idx] = true;
            int row = ps[0].first;
            int minCol = 6;
            for (auto &p : ps) minCol = min(minCol, p.second);
            gFix[idx] = row;
            gStart[idx] = minCol;
        } else {
            // vertical
            gHoriz[idx] = false;
            int col = ps[0].second;
            int minRow = 6;
            for (auto &p : ps) minRow = min(minRow, p.first);
            gFix[idx] = col;
            gStart[idx] = minRow;
        }
    }

    int minSteps = bfs_min_steps();

    // We do not change the puzzle: 0 steps to form the new puzzle.
    cout << minSteps << ' ' << 0 << '\n';

    return 0;
}