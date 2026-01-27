#include <bits/stdc++.h>
using namespace std;

// Rush Hour-like puzzle state search and reverse distance computation.
// We explore all reachable states from the initial board (or until resources run out),
// then compute minimal steps to solve (exit) for each state via multi-source BFS,
// and pick the state with maximal solve distance. Output the path (sequence of unit moves)
// from the initial state to that chosen state.

struct Vehicle {
    bool horizontal;
    int row; // for horizontal vehicles
    int col; // for vertical vehicles
    int len;
    int maxPos; // maximum position along movement axis (0..maxPos inclusive)
};

static const int NGRID = 6;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read board
    int board[6][6];
    int maxId = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            cin >> board[r][c];
            maxId = max(maxId, board[r][c]);
        }
    }
    int n = maxId;
    if (n == 0) {
        cout << "0 0\n";
        return 0;
    }

    // Extract vehicle info
    vector<int> minr(n+1, 10), minc(n+1, 10), maxr(n+1, -1), maxc(n+1, -1);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id == 0) continue;
            minr[id] = min(minr[id], r);
            minc[id] = min(minc[id], c);
            maxr[id] = max(maxr[id], r);
            maxc[id] = max(maxc[id], c);
        }
    }
    vector<Vehicle> V(n+1);
    for (int id = 1; id <= n; ++id) {
        if (maxr[id] == -1) { // not present, but per statement ids are 1..n present
            // Should not happen
            cout << "0 0\n";
            return 0;
        }
        Vehicle v{};
        if (minr[id] == maxr[id]) {
            v.horizontal = true;
            v.row = minr[id];
            v.col = -1;
            v.len = maxc[id] - minc[id] + 1;
            v.maxPos = NGRID - v.len;
        } else {
            v.horizontal = false;
            v.col = minc[id];
            v.row = -1;
            v.len = maxr[id] - minr[id] + 1;
            v.maxPos = NGRID - v.len;
        }
        V[id] = v;
    }
    // Verify red car is horizontal and at row 2 (0-based)
    if (!(V[1].horizontal && V[1].row == 2)) {
        // According to problem, guaranteed; but guard anyway.
        // We'll proceed anyway.
    }

    // Build initial positions (pos[i] = minimal coordinate along move axis)
    vector<int> initPos(n+1);
    for (int id = 1; id <= n; ++id) {
        if (V[id].horizontal) initPos[id] = minc[id];
        else initPos[id] = minr[id];
    }

    auto encode = [&](const vector<int>& pos)->uint64_t{
        uint64_t key = 0;
        for (int id = 1; id <= n; ++id) {
            key |= (uint64_t)(pos[id] & 0xF) << (4*(id-1));
        }
        return key;
    };
    auto decode = [&](uint64_t key, vector<int>& pos){
        pos.resize(n+1);
        for (int id = 1; id <= n; ++id) {
            pos[id] = (int)((key >> (4*(id-1))) & 0xF);
        }
    };

    // Move encoding: 0=L,1=R,2=U,3=D
    auto dirChar = [&](uint8_t d)->char{
        if (d==0) return 'L';
        if (d==1) return 'R';
        if (d==2) return 'U';
        return 'D';
    };

    // BFS from initial to enumerate reachable states
    uint64_t initKey = encode(initPos);

    // visited map: state key -> index
    unordered_map<uint64_t,int> indexOf;
    indexOf.reserve(1<<20);

    vector<uint64_t> keys;
    vector<int> parent;
    vector<uint8_t> parentVid;
    vector<uint8_t> parentDir;

    deque<int> q;

    auto add_state = [&](uint64_t key, int pidx, uint8_t vid, uint8_t dir)->int{
        auto it = indexOf.find(key);
        if (it != indexOf.end()) return it->second;
        int idx = (int)keys.size();
        indexOf.emplace(key, idx);
        keys.push_back(key);
        parent.push_back(pidx);
        parentVid.push_back(vid);
        parentDir.push_back(dir);
        q.push_back(idx);
        return idx;
    };

    add_state(initKey, -1, 0, 0);

    vector<int> occ(36);

    // Resource limits (simple safety)
    const size_t MAX_STATES = 2000000; // cap to avoid memory/time blow-up
    while (!q.empty()) {
        int u = q.front(); q.pop_front();
        if (keys.size() >= MAX_STATES) break;

        // Decode positions
        vector<int> pos;
        decode(keys[u], pos);
        // Build occupancy grid
        fill(occ.begin(), occ.end(), 0);
        for (int id = 1; id <= n; ++id) {
            if (V[id].horizontal) {
                int r = V[id].row;
                int c0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[r*6 + (c0+k)] = id;
                }
            } else {
                int c = V[id].col;
                int r0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[(r0+k)*6 + c] = id;
                }
            }
        }
        // Generate one-step moves
        for (int id = 1; id <= n; ++id) {
            int p = pos[id];
            if (V[id].horizontal) {
                int r = V[id].row;
                // Left
                if (p-1 >= 0 && occ[r*6 + (p-1)] == 0) {
                    pos[id] = p-1;
                    uint64_t nk = encode(pos);
                    add_state(nk, u, (uint8_t)id, 0);
                    pos[id] = p;
                }
                // Right
                if (p + V[id].len < 6 && occ[r*6 + (p + V[id].len)] == 0) {
                    pos[id] = p+1;
                    uint64_t nk = encode(pos);
                    add_state(nk, u, (uint8_t)id, 1);
                    pos[id] = p;
                }
            } else {
                int c = V[id].col;
                // Up
                if (p-1 >= 0 && occ[(p-1)*6 + c] == 0) {
                    pos[id] = p-1;
                    uint64_t nk = encode(pos);
                    add_state(nk, u, (uint8_t)id, 2);
                    pos[id] = p;
                }
                // Down
                if (p + V[id].len < 6 && occ[(p + V[id].len)*6 + c] == 0) {
                    pos[id] = p+1;
                    uint64_t nk = encode(pos);
                    add_state(nk, u, (uint8_t)id, 3);
                    pos[id] = p;
                }
            }
        }
    }

    int S = (int)keys.size();

    // Compute is-goal-clear and seed distances
    const int INF = 1e9;
    vector<int> dist(S, INF);

    for (int idx = 0; idx < S; ++idx) {
        // Decode and grid
        vector<int> pos;
        decode(keys[idx], pos);
        fill(occ.begin(), occ.end(), 0);
        for (int id = 1; id <= n; ++id) {
            if (V[id].horizontal) {
                int r = V[id].row;
                int c0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[r*6 + (c0+k)] = id;
                }
            } else {
                int c = V[id].col;
                int r0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[(r0+k)*6 + c] = id;
                }
            }
        }
        int cLeft = pos[1];
        bool clear = true;
        int r = 2;
        for (int j = cLeft + 2; j < 6; ++j) {
            if (occ[r*6 + j] != 0) { clear = false; break; }
        }
        if (clear) {
            int base = 6 - cLeft; // moves to fully exit once clear
            dist[idx] = base;
        }
    }

    // Reverse BFS (multi-source with pre-initialized distances)
    deque<int> dq;
    vector<char> inq(S, 0);
    for (int i = 0; i < S; ++i) {
        if (dist[i] < INF) {
            dq.push_back(i);
            inq[i] = 1;
        }
    }

    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        inq[u] = 0;

        // Generate neighbors (undirected graph)
        vector<int> pos;
        decode(keys[u], pos);
        fill(occ.begin(), occ.end(), 0);
        for (int id = 1; id <= n; ++id) {
            if (V[id].horizontal) {
                int rr = V[id].row;
                int c0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[rr*6 + (c0+k)] = id;
                }
            } else {
                int cc = V[id].col;
                int r0 = pos[id];
                for (int k = 0; k < V[id].len; ++k) {
                    occ[(r0+k)*6 + cc] = id;
                }
            }
        }
        for (int id = 1; id <= n; ++id) {
            int p = pos[id];
            if (V[id].horizontal) {
                int rr = V[id].row;
                // Left neighbor
                if (p-1 >= 0 && occ[rr*6 + (p-1)] == 0) {
                    pos[id] = p-1;
                    uint64_t nk = encode(pos);
                    auto it = indexOf.find(nk);
                    if (it != indexOf.end()) {
                        int v = it->second;
                        if (dist[u] + 1 < dist[v]) {
                            dist[v] = dist[u] + 1;
                            if (!inq[v]) { dq.push_back(v); inq[v] = 1; }
                        }
                    }
                    pos[id] = p;
                }
                // Right neighbor
                if (p + V[id].len < 6 && occ[rr*6 + (p + V[id].len)] == 0) {
                    pos[id] = p+1;
                    uint64_t nk = encode(pos);
                    auto it = indexOf.find(nk);
                    if (it != indexOf.end()) {
                        int v = it->second;
                        if (dist[u] + 1 < dist[v]) {
                            dist[v] = dist[u] + 1;
                            if (!inq[v]) { dq.push_back(v); inq[v] = 1; }
                        }
                    }
                    pos[id] = p;
                }
            } else {
                int cc = V[id].col;
                // Up neighbor
                if (p-1 >= 0 && occ[(p-1)*6 + cc] == 0) {
                    pos[id] = p-1;
                    uint64_t nk = encode(pos);
                    auto it = indexOf.find(nk);
                    if (it != indexOf.end()) {
                        int v = it->second;
                        if (dist[u] + 1 < dist[v]) {
                            dist[v] = dist[u] + 1;
                            if (!inq[v]) { dq.push_back(v); inq[v] = 1; }
                        }
                    }
                    pos[id] = p;
                }
                // Down neighbor
                if (p + V[id].len < 6 && occ[(p + V[id].len)*6 + cc] == 0) {
                    pos[id] = p+1;
                    uint64_t nk = encode(pos);
                    auto it = indexOf.find(nk);
                    if (it != indexOf.end()) {
                        int v = it->second;
                        if (dist[u] + 1 < dist[v]) {
                            dist[v] = dist[u] + 1;
                            if (!inq[v]) { dq.push_back(v); inq[v] = 1; }
                        }
                    }
                    pos[id] = p;
                }
            }
        }
    }

    // Choose best state (max dist)
    int bestIdx = 0;
    int bestVal = dist[0] < INF ? dist[0] : -1;
    for (int i = 0; i < S; ++i) {
        if (dist[i] < INF && dist[i] > bestVal) {
            bestVal = dist[i];
            bestIdx = i;
        }
    }
    if (bestVal < 0) {
        // Should not happen (there is guaranteed solution). Fallback to initial with 0.
        bestIdx = 0;
        bestVal = 0;
    }

    // Reconstruct path from initial (index 0) to bestIdx
    vector<pair<int,char>> moves;
    int cur = bestIdx;
    while (cur != -1 && parent[cur] != -1) {
        moves.emplace_back((int)parentVid[cur], dirChar(parentDir[cur]));
        cur = parent[cur];
    }
    reverse(moves.begin(), moves.end());

    // Output
    cout << bestVal << " " << moves.size() << "\n";
    for (auto &mv : moves) {
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}