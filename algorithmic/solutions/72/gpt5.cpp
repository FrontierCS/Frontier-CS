#include <bits/stdc++.h>
using namespace std;

struct Move {
    uint8_t id;
    char dir;
};

struct Node {
    uint64_t key;
    int parent;
    Move mv;
};

struct Game {
    int n;
    vector<int> len;      // 1..n
    vector<uint8_t> ori;  // 0: vertical, 1: horizontal
    int redRow;           // 0-based row of red car (should be 2)
};

// Encode positions into 64-bit key: per id (1..n), 6 bits: row(3) << 3 | col(3)
static inline uint64_t encodeKey(const vector<uint8_t>& rows, const vector<uint8_t>& cols, int n) {
    uint64_t key = 0;
    for (int i = 1; i <= n; ++i) {
        uint64_t seg = ((uint64_t)rows[i] << 3) | (uint64_t)cols[i];
        key |= (seg << (6 * (i - 1)));
    }
    return key;
}

static inline void decodeKey(uint64_t key, vector<uint8_t>& rows, vector<uint8_t>& cols, int n) {
    for (int i = 1; i <= n; ++i) {
        uint64_t seg = (key >> (6 * (i - 1))) & 63ULL;
        rows[i] = (uint8_t)((seg >> 3) & 7ULL);
        cols[i] = (uint8_t)(seg & 7ULL);
    }
}

static inline uint64_t updateKey(uint64_t key, int id, uint8_t newRow, uint8_t newCol) {
    int shift = 6 * (id - 1);
    uint64_t mask = 63ULL << shift;
    uint64_t seg = ((uint64_t)newRow << 3) | (uint64_t)newCol;
    key &= ~mask;
    key |= (seg << shift);
    return key;
}

static inline void buildBoard(const Game& g, const vector<uint8_t>& rows, const vector<uint8_t>& cols, array<uint8_t, 36>& board) {
    board.fill(0);
    for (int i = 1; i <= g.n; ++i) {
        int r = rows[i], c = cols[i], l = g.len[i];
        if (g.ori[i]) { // horizontal
            for (int d = 0; d < l; ++d) {
                board[r * 6 + (c + d)] = (uint8_t)i;
            }
        } else { // vertical
            for (int d = 0; d < l; ++d) {
                board[(r + d) * 6 + c] = (uint8_t)i;
            }
        }
    }
}

static inline void generateNeighbors(const Game& g, uint64_t key, const array<uint8_t,36>& board, vector<pair<uint64_t, Move>>& out) {
    out.clear();
    // For decoding single id position quickly:
    for (int i = 1; i <= g.n; ++i) {
        uint64_t seg = (key >> (6 * (i - 1))) & 63ULL;
        uint8_t r = (uint8_t)((seg >> 3) & 7ULL);
        uint8_t c = (uint8_t)(seg & 7ULL);
        int l = g.len[i];
        if (g.ori[i]) { // horizontal
            // move left
            if (c > 0 && board[r * 6 + (c - 1)] == 0) {
                uint64_t nk = updateKey(key, i, r, c - 1);
                out.push_back({nk, Move{(uint8_t)i, 'L'}});
            }
            // move right
            if (c + l < 6 && board[r * 6 + (c + l)] == 0) {
                uint64_t nk = updateKey(key, i, r, c + 1);
                out.push_back({nk, Move{(uint8_t)i, 'R'}});
            }
        } else { // vertical
            // move up
            if (r > 0 && board[(r - 1) * 6 + c] == 0) {
                uint64_t nk = updateKey(key, i, r - 1, c);
                out.push_back({nk, Move{(uint8_t)i, 'U'}});
            }
            // move down
            if (r + l < 6 && board[(r + l) * 6 + c] == 0) {
                uint64_t nk = updateKey(key, i, r + 1, c);
                out.push_back({nk, Move{(uint8_t)i, 'D'}});
            }
        }
    }
}

static int bfsSolveExact(const Game& g, uint64_t startKey) {
    // BFS from startKey to any state with red car anchor col == 5. Return dist + 2.
    unordered_map<uint64_t, int> dist;
    dist.reserve(1 << 18);
    deque<uint64_t> dq;
    dist[startKey] = 0;
    dq.push_back(startKey);

    vector<uint8_t> rows(g.n + 1), cols(g.n + 1);
    array<uint8_t,36> board{};
    vector<pair<uint64_t, Move>> neigh;

    while (!dq.empty()) {
        uint64_t key = dq.front(); dq.pop_front();
        int dcur = dist[key];

        uint64_t segRed = (key >> 0) & 63ULL; // id 1
        uint8_t colRed = (uint8_t)(segRed & 7ULL);
        if (colRed == 5) {
            return dcur + 2;
        }

        decodeKey(key, rows, cols, g.n);
        buildBoard(g, rows, cols, board);
        generateNeighbors(g, key, board, neigh);
        for (auto& pr : neigh) {
            uint64_t nk = pr.first;
            if (dist.find(nk) == dist.end()) {
                dist[nk] = dcur + 1;
                dq.push_back(nk);
            }
        }
    }
    // Should be solvable; but safe return large
    return INT_MAX / 4;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int grid[6][6];
    int maxId = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int x;
            if (!(cin >> x)) return 0;
            grid[r][c] = x;
            if (x > maxId) maxId = x;
        }
    }

    int n = maxId;
    vector<vector<pair<int,int>>> cells(n + 1);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = grid[r][c];
            if (id > 0) cells[id].push_back({r, c});
        }
    }

    Game g;
    g.n = n;
    g.len.assign(n + 1, 0);
    g.ori.assign(n + 1, 0);
    g.redRow = 2;

    vector<uint8_t> initRows(n + 1), initCols(n + 1);

    for (int id = 1; id <= n; ++id) {
        auto& v = cells[id];
        if (v.empty()) continue;
        sort(v.begin(), v.end());
        g.len[id] = (int)v.size();
        bool horiz = false;
        if (v.size() >= 2) {
            if (v[0].first == v[1].first) horiz = true;
        }
        g.ori[id] = horiz ? 1 : 0;
        if (horiz) {
            int r = v[0].first;
            int cmin = 10;
            for (auto &p : v) cmin = min(cmin, p.second);
            initRows[id] = (uint8_t)r;
            initCols[id] = (uint8_t)cmin;
        } else {
            int c = v[0].second;
            int rmin = 10;
            for (auto &p : v) rmin = min(rmin, p.first);
            initRows[id] = (uint8_t)rmin;
            initCols[id] = (uint8_t)c;
        }
    }

    uint64_t startKey = encodeKey(initRows, initCols, n);

    // Phase 1: BFS enumerate all reachable states from initial
    vector<Node> nodes;
    nodes.reserve(1 << 18);
    unordered_map<uint64_t, int> idxMap;
    idxMap.reserve(1 << 18);

    nodes.push_back(Node{startKey, -1, Move{0, 0}});
    idxMap[startKey] = 0;
    vector<int> q;
    q.reserve(1 << 18);
    q.push_back(0);
    size_t qhead = 0;

    vector<uint8_t> rows(n + 1), cols(n + 1);
    array<uint8_t,36> board{};
    vector<pair<uint64_t, Move>> neigh;

    while (qhead < q.size()) {
        int idx = q[qhead++];
        uint64_t key = nodes[idx].key;

        decodeKey(key, rows, cols, n);
        buildBoard(g, rows, cols, board);
        generateNeighbors(g, key, board, neigh);
        for (auto &pr : neigh) {
            uint64_t nk = pr.first;
            auto it = idxMap.find(nk);
            if (it == idxMap.end()) {
                int nid = (int)nodes.size();
                nodes.push_back(Node{nk, idx, pr.second});
                idxMap.emplace(nk, nid);
                q.push_back(nid);
            }
        }
    }

    // Phase 2: BFS distances to goal (red anchor col == 5) restricted to visited set
    int M = (int)nodes.size();
    vector<int> distGoal(M, -1);
    vector<int> qq;
    qq.reserve(M);

    for (int i = 0; i < M; ++i) {
        uint64_t segRed = (nodes[i].key >> 0) & 63ULL;
        uint8_t colRed = (uint8_t)(segRed & 7ULL);
        if (colRed == 5) {
            distGoal[i] = 0;
            qq.push_back(i);
        }
    }

    size_t h = 0;
    while (h < qq.size()) {
        int idx = qq[h++];
        uint64_t key = nodes[idx].key;

        decodeKey(key, rows, cols, n);
        buildBoard(g, rows, cols, board);
        generateNeighbors(g, key, board, neigh);
        for (auto &pr : neigh) {
            uint64_t nk = pr.first;
            auto it = idxMap.find(nk);
            if (it != idxMap.end()) {
                int j = it->second;
                if (distGoal[j] == -1) {
                    distGoal[j] = distGoal[idx] + 1;
                    qq.push_back(j);
                }
            }
        }
    }

    // Pick best state maximizing distGoal + 2
    int bestIdx = 0;
    int bestDist = -1;
    for (int i = 0; i < M; ++i) {
        if (distGoal[i] >= 0) {
            int val = distGoal[i] + 2;
            if (val > bestDist) {
                bestDist = val;
                bestIdx = i;
            }
        }
    }

    // Compute exact minimal steps for chosen state to solve (to ensure correctness)
    int exactSolve = bfsSolveExact(g, nodes[bestIdx].key);

    // Reconstruct path from start to bestIdx
    vector<Move> path;
    int cur = bestIdx;
    while (cur != 0) {
        path.push_back(nodes[cur].mv);
        cur = nodes[cur].parent;
    }
    reverse(path.begin(), path.end());

    cout << exactSolve << " " << path.size() << "\n";
    for (auto &mv : path) {
        cout << (int)mv.id << " " << mv.dir << "\n";
    }

    return 0;
}