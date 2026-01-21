#include <bits/stdc++.h>
using namespace std;

const int MAXV = 10;

struct State {
    uint8_t pos[MAXV + 1]; // 1..n used
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (!(cin >> board[r][c])) return 0;
        }
    }

    int n = 0;
    for (int r = 0; r < 6; ++r)
        for (int c = 0; c < 6; ++c)
            if (board[r][c] > n) n = board[r][c];

    if (n == 0) {
        // No vehicles; trivial (should not happen per problem, but handle gracefully)
        cout << "0 0\n";
        return 0;
    }

    bool horiz[MAXV + 1];
    int len[MAXV + 1];
    int fixedCoord[MAXV + 1]; // row for horiz, col for vert
    uint8_t initPos[MAXV + 1];
    int maxPos[MAXV + 1];

    for (int id = 1; id <= n; ++id) {
        bool found = false;
        int r0 = -1, c0 = -1;
        for (int r = 0; r < 6 && !found; ++r) {
            for (int c = 0; c < 6; ++c) {
                if (board[r][c] == id) {
                    r0 = r; c0 = c;
                    found = true;
                    break;
                }
            }
        }
        if (!found) continue; // Should not occur

        bool h = false;
        if (c0 + 1 < 6 && board[r0][c0 + 1] == id) h = true;
        else if (r0 + 1 < 6 && board[r0 + 1][c0] == id) h = false;
        else h = true; // Fallback, though vehicles are guaranteed length >= 2

        horiz[id] = h;
        if (h) {
            int c = c0;
            while (c < 6 && board[r0][c] == id) ++c;
            len[id] = c - c0;
            fixedCoord[id] = r0;
            initPos[id] = (uint8_t)c0;
        } else {
            int r = r0;
            while (r < 6 && board[r][c0] == id) ++r;
            len[id] = r - r0;
            fixedCoord[id] = c0;
            initPos[id] = (uint8_t)r0;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (horiz[i]) {
            if (i == 1) maxPos[i] = 6; // red car can go fully out
            else maxPos[i] = 6 - len[i];
        } else {
            maxPos[i] = 6 - len[i];
        }
    }

    State initial;
    for (int i = 1; i <= n; ++i) initial.pos[i] = initPos[i];

    auto encode = [&](const State &s) -> uint64_t {
        uint64_t key = 0;
        for (int i = 1; i <= n; ++i) {
            key |= (uint64_t)(s.pos[i]) << (3 * (i - 1));
        }
        return key;
    };

    vector<State> states;
    states.reserve(1000000);
    states.push_back(initial);

    vector<int> parent;
    parent.reserve(1000000);
    parent.push_back(-1);

    vector<int> distInit;
    distInit.reserve(1000000);
    distInit.push_back(0);

    vector<uint8_t> moveFromParent; // (vehicle_id << 2) | dirCode (0=U,1=D,2=L,3=R)
    moveFromParent.reserve(1000000);
    moveFromParent.push_back(0);

    unordered_map<uint64_t, int> mp;
    mp.reserve(1000000);
    mp.max_load_factor(0.7f);
    mp[encode(initial)] = 0;

    queue<int> q;
    q.push(0);

    // BFS from initial to enumerate all reachable states
    while (!q.empty()) {
        int id = q.front();
        q.pop();
        const State &cs = states[id];

        int grid[6][6];
        memset(grid, 0, sizeof(grid));

        for (int vid = 1; vid <= n; ++vid) {
            if (horiz[vid]) {
                int r = fixedCoord[vid];
                int pos = cs.pos[vid];
                for (int k = 0; k < len[vid]; ++k) {
                    int c = pos + k;
                    if (c >= 0 && c < 6) grid[r][c] = vid;
                }
            } else {
                int c = fixedCoord[vid];
                int pos = cs.pos[vid];
                for (int k = 0; k < len[vid]; ++k) {
                    int r = pos + k;
                    if (r >= 0 && r < 6) grid[r][c] = vid;
                }
            }
        }

        for (int vid = 1; vid <= n; ++vid) {
            if (horiz[vid]) {
                int row = fixedCoord[vid];
                int pos = cs.pos[vid];

                // Move left
                int newPos = pos - 1;
                if (newPos >= 0) {
                    int newCellCol = newPos; // cell entering on the left
                    if (grid[row][newCellCol] == 0) {
                        State ns = cs;
                        ns.pos[vid] = (uint8_t)newPos;
                        uint64_t key = encode(ns);
                        auto it = mp.find(key);
                        if (it == mp.end()) {
                            int nid = (int)states.size();
                            mp.emplace(key, nid);
                            states.push_back(ns);
                            distInit.push_back(distInit[id] + 1);
                            parent.push_back(id);
                            uint8_t dirCode = 2; // L
                            uint8_t pack = (uint8_t)((vid << 2) | dirCode);
                            moveFromParent.push_back(pack);
                            q.push(nid);
                        }
                    }
                }

                // Move right
                newPos = pos + 1;
                int maxp = maxPos[vid];
                if (newPos <= maxp) {
                    int newCellCol = pos + len[vid]; // cell entering on the right
                    bool allow = false;
                    if (newCellCol < 6) {
                        if (grid[row][newCellCol] == 0) allow = true;
                    } else {
                        if (vid == 1) allow = true; // red car leaving board
                    }
                    if (allow) {
                        State ns = cs;
                        ns.pos[vid] = (uint8_t)newPos;
                        uint64_t key = encode(ns);
                        auto it = mp.find(key);
                        if (it == mp.end()) {
                            int nid = (int)states.size();
                            mp.emplace(key, nid);
                            states.push_back(ns);
                            distInit.push_back(distInit[id] + 1);
                            parent.push_back(id);
                            uint8_t dirCode = 3; // R
                            uint8_t pack = (uint8_t)((vid << 2) | dirCode);
                            moveFromParent.push_back(pack);
                            q.push(nid);
                        }
                    }
                }
            } else { // vertical
                int col = fixedCoord[vid];
                int pos = cs.pos[vid];

                // Move up
                int newPos = pos - 1;
                if (newPos >= 0) {
                    int newCellRow = newPos; // entering cell above
                    if (grid[newCellRow][col] == 0) {
                        State ns = cs;
                        ns.pos[vid] = (uint8_t)newPos;
                        uint64_t key = encode(ns);
                        auto it = mp.find(key);
                        if (it == mp.end()) {
                            int nid = (int)states.size();
                            mp.emplace(key, nid);
                            states.push_back(ns);
                            distInit.push_back(distInit[id] + 1);
                            parent.push_back(id);
                            uint8_t dirCode = 0; // U
                            uint8_t pack = (uint8_t)((vid << 2) | dirCode);
                            moveFromParent.push_back(pack);
                            q.push(nid);
                        }
                    }
                }

                // Move down
                newPos = pos + 1;
                int maxp = maxPos[vid];
                if (newPos <= maxp) {
                    int newCellRow = pos + len[vid]; // entering cell below
                    if (newCellRow < 6 && grid[newCellRow][col] == 0) {
                        State ns = cs;
                        ns.pos[vid] = (uint8_t)newPos;
                        uint64_t key = encode(ns);
                        auto it = mp.find(key);
                        if (it == mp.end()) {
                            int nid = (int)states.size();
                            mp.emplace(key, nid);
                            states.push_back(ns);
                            distInit.push_back(distInit[id] + 1);
                            parent.push_back(id);
                            uint8_t dirCode = 1; // D
                            uint8_t pack = (uint8_t)((vid << 2) | dirCode);
                            moveFromParent.push_back(pack);
                            q.push(nid);
                        }
                    }
                }
            }
        }
    }

    int S = (int)states.size();
    const int INF = 1e9;
    vector<int> distGoal(S, INF);
    queue<int> q2;

    // Multi-source BFS from all solved states (red car fully out: pos[1] == 6)
    for (int id = 0; id < S; ++id) {
        if (states[id].pos[1] == 6) {
            distGoal[id] = 0;
            q2.push(id);
        }
    }

    auto relax_neighbor = [&](int currentId, const State &cs, int vid, int newPos) {
        State ns = cs;
        ns.pos[vid] = (uint8_t)newPos;
        uint64_t key = encode(ns);
        auto it = mp.find(key);
        if (it == mp.end()) return;
        int nid = it->second;
        if (distGoal[nid] == INF) {
            distGoal[nid] = distGoal[currentId] + 1;
            q2.push(nid);
        }
    };

    while (!q2.empty()) {
        int id = q2.front();
        q2.pop();
        const State &cs = states[id];

        int grid[6][6];
        memset(grid, 0, sizeof(grid));

        for (int vid = 1; vid <= n; ++vid) {
            if (horiz[vid]) {
                int r = fixedCoord[vid];
                int pos = cs.pos[vid];
                for (int k = 0; k < len[vid]; ++k) {
                    int c = pos + k;
                    if (c >= 0 && c < 6) grid[r][c] = vid;
                }
            } else {
                int c = fixedCoord[vid];
                int pos = cs.pos[vid];
                for (int k = 0; k < len[vid]; ++k) {
                    int r = pos + k;
                    if (r >= 0 && r < 6) grid[r][c] = vid;
                }
            }
        }

        for (int vid = 1; vid <= n; ++vid) {
            if (horiz[vid]) {
                int row = fixedCoord[vid];
                int pos = cs.pos[vid];

                // Move left
                int newPos = pos - 1;
                if (newPos >= 0) {
                    int newCellCol = newPos;
                    if (grid[row][newCellCol] == 0) {
                        relax_neighbor(id, cs, vid, newPos);
                    }
                }

                // Move right
                newPos = pos + 1;
                int maxp = maxPos[vid];
                if (newPos <= maxp) {
                    int newCellCol = pos + len[vid];
                    bool allow = false;
                    if (newCellCol < 6) {
                        if (grid[row][newCellCol] == 0) allow = true;
                    } else {
                        if (vid == 1) allow = true;
                    }
                    if (allow) {
                        relax_neighbor(id, cs, vid, newPos);
                    }
                }
            } else {
                int col = fixedCoord[vid];
                int pos = cs.pos[vid];

                // Move up
                int newPos = pos - 1;
                if (newPos >= 0) {
                    int newCellRow = newPos;
                    if (grid[newCellRow][col] == 0) {
                        relax_neighbor(id, cs, vid, newPos);
                    }
                }

                // Move down
                newPos = pos + 1;
                int maxp = maxPos[vid];
                if (newPos <= maxp) {
                    int newCellRow = pos + len[vid];
                    if (newCellRow < 6 && grid[newCellRow][col] == 0) {
                        relax_neighbor(id, cs, vid, newPos);
                    }
                }
            }
        }
    }

    // Select state with maximum distance to solution
    int bestId = 0;
    int bestDist = distGoal[0];
    for (int id = 1; id < S; ++id) {
        if (distGoal[id] > bestDist) {
            bestDist = distGoal[id];
            bestId = id;
        }
    }

    int solveSteps = (bestDist == INF ? 0 : bestDist);

    // Reconstruct path from initial (state 0) to bestId
    vector<pair<int, char>> moves;
    int cur = bestId;
    while (parent[cur] != -1) {
        uint8_t pack = moveFromParent[cur];
        int vid = pack >> 2;
        int code = pack & 3;
        char dir = (code == 0 ? 'U' : (code == 1 ? 'D' : (code == 2 ? 'L' : 'R')));
        moves.push_back({vid, dir});
        cur = parent[cur];
    }
    reverse(moves.begin(), moves.end());

    cout << solveSteps << ' ' << moves.size() << '\n';
    for (auto &mv : moves) {
        cout << mv.first << ' ' << mv.second << '\n';
    }

    return 0;
}