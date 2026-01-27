#include <bits/stdc++.h>
using namespace std;

struct Move {
    int id;
    char dir;
};

struct Puzzle {
    int n;
    int len[11];
    bool horiz[11];
    int fixRow[11];
    int fixCol[11];
    int maxPos[11];
    uint64_t MASK[11];
    int SHIFT[11];

    Puzzle() {
        memset(len, 0, sizeof(len));
        memset(horiz, 0, sizeof(horiz));
        for (int i = 0; i < 11; ++i) fixRow[i] = fixCol[i] = -1, maxPos[i]=0, MASK[i]=0, SHIFT[i]=0;
        n = 0;
    }

    void initFromBoard(const vector<vector<int>>& board) {
        int maxId = 0;
        for (int r = 0; r < 6; ++r) for (int c = 0; c < 6; ++c) maxId = max(maxId, board[r][c]);
        n = maxId;
        vector<int> minr(n+1, 6), maxr(n+1, -1), minc(n+1, 6), maxc(n+1, -1);
        for (int r = 0; r < 6; ++r) {
            for (int c = 0; c < 6; ++c) {
                int id = board[r][c];
                if (id == 0) continue;
                minr[id] = min(minr[id], r);
                maxr[id] = max(maxr[id], r);
                minc[id] = min(minc[id], c);
                maxc[id] = max(maxc[id], c);
            }
        }
        for (int id = 1; id <= n; ++id) {
            if (minr[id] == 6) continue; // just in case
            if (minr[id] == maxr[id]) {
                horiz[id] = true;
                len[id] = maxc[id] - minc[id] + 1;
                fixRow[id] = minr[id];
                fixCol[id] = -1;
                maxPos[id] = 6 - len[id];
            } else {
                horiz[id] = false;
                len[id] = maxr[id] - minr[id] + 1;
                fixCol[id] = minc[id];
                fixRow[id] = -1;
                maxPos[id] = 6 - len[id];
            }
        }
        for (int id = 1; id <= n; ++id) {
            SHIFT[id] = 3 * (id - 1);
            MASK[id] = (uint64_t)(7ULL) << SHIFT[id];
        }
    }

    uint64_t encodeInitial(const vector<vector<int>>& board) const {
        uint64_t key = 0;
        for (int id = 1; id <= n; ++id) {
            int pos = 0;
            if (horiz[id]) {
                // leftmost col
                for (int c = 0; c < 6; ++c) {
                    if (board[fixRow[id]][c] == id) { pos = c; break; }
                }
            } else {
                // topmost row
                for (int r = 0; r < 6; ++r) {
                    if (board[r][fixCol[id]] == id) { pos = r; break; }
                }
            }
            key |= (uint64_t)pos << SHIFT[id];
        }
        return key;
    }

    inline void decode(uint64_t key, int pos[]) const {
        for (int id = 1; id <= n; ++id) {
            pos[id] = (int)((key >> SHIFT[id]) & 7ULL);
        }
    }

    inline int getPos(uint64_t key, int id) const {
        return (int)((key >> SHIFT[id]) & 7ULL);
    }

    inline uint64_t setPos(uint64_t key, int id, int newPos) const {
        key &= ~MASK[id];
        key |= (uint64_t)newPos << SHIFT[id];
        return key;
    }

    void buildGrid(const int pos[], int grid[6][6]) const {
        for (int r = 0; r < 6; ++r) for (int c = 0; c < 6; ++c) grid[r][c] = 0;
        for (int id = 1; id <= n; ++id) {
            if (horiz[id]) {
                int r = fixRow[id];
                int c0 = pos[id];
                for (int k = 0; k < len[id]; ++k) grid[r][c0 + k] = id;
            } else {
                int c = fixCol[id];
                int r0 = pos[id];
                for (int k = 0; k < len[id]; ++k) grid[r0 + k][c] = id;
            }
        }
    }

    inline bool isGoal(uint64_t key) const {
        // red car id = 1; goal inside-board when leftmost col == 4
        return getPos(key, 1) == 4;
    }
};

struct BFS1Result {
    vector<uint64_t> nodes;
    unordered_map<uint64_t, int> idx;
    vector<int> parent;
    vector<Move> moveToHere;
    vector<int> depth;
    vector<int> seeds; // indices where red pos == 4
};

static inline void addNeighbor(unordered_map<uint64_t,int>& idx, vector<uint64_t>& nodes, vector<int>& parent, vector<Move>& moveToHere, vector<int>& depth, int curIdx, uint64_t neighborKey, int vid, char dir) {
    auto it = idx.find(neighborKey);
    if (it == idx.end()) {
        int newIdx = (int)nodes.size();
        idx.emplace(neighborKey, newIdx);
        nodes.push_back(neighborKey);
        parent.push_back(curIdx);
        moveToHere.push_back({vid, dir});
        depth.push_back(depth[curIdx] + 1);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> board(6, vector<int>(6));
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (!(cin >> board[r][c])) return 0;
        }
    }

    Puzzle P;
    P.initFromBoard(board);
    uint64_t startKey = P.encodeInitial(board);

    auto tStart = chrono::steady_clock::now();
    const double TOTAL_TIME = 1.95;

    // BFS1: Explore from start to get a pool of states and parent moves
    BFS1Result R;
    R.nodes.reserve(120000);
    R.parent.reserve(120000);
    R.moveToHere.reserve(120000);
    R.depth.reserve(120000);
    R.idx.reserve(200000);

    R.idx.emplace(startKey, 0);
    R.nodes.push_back(startKey);
    R.parent.push_back(-1);
    R.moveToHere.push_back({-1, 'X'});
    R.depth.push_back(0);
    if (P.isGoal(startKey)) R.seeds.push_back(0);

    vector<int> queueIdx;
    queueIdx.reserve(120000);
    queueIdx.push_back(0);
    size_t head = 0;

    int pos[12];
    int grid[6][6];

    // Control limits
    const int MAX_VISIT = 120000; // cap BFS1 nodes
    const double TIME_BFS1 = 0.7;

    while (head < queueIdx.size()) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - tStart).count();
        if (elapsed > TIME_BFS1 || (int)R.nodes.size() >= MAX_VISIT) break;

        int curIdx = queueIdx[head++];
        uint64_t key = R.nodes[curIdx];

        // decode and grid
        P.decode(key, pos);
        P.buildGrid(pos, grid);

        // record seed if goal
        if (P.getPos(key, 1) == 4) {
            R.seeds.push_back(curIdx);
        }

        // generate neighbors
        for (int id = 1; id <= P.n; ++id) {
            if (P.horiz[id]) {
                int r = P.fixRow[id];
                int c0 = pos[id];
                // move left
                if (c0 > 0 && grid[r][c0 - 1] == 0) {
                    uint64_t nk = P.setPos(key, id, c0 - 1);
                    addNeighbor(R.idx, R.nodes, R.parent, R.moveToHere, R.depth, curIdx, nk, id, 'L');
                    queueIdx.push_back((int)R.nodes.size() - 1);
                }
                // move right
                if (c0 + P.len[id] < 6 && grid[r][c0 + P.len[id]] == 0) {
                    uint64_t nk = P.setPos(key, id, c0 + 1);
                    addNeighbor(R.idx, R.nodes, R.parent, R.moveToHere, R.depth, curIdx, nk, id, 'R');
                    queueIdx.push_back((int)R.nodes.size() - 1);
                }
            } else {
                int c = P.fixCol[id];
                int r0 = pos[id];
                // move up
                if (r0 > 0 && grid[r0 - 1][c] == 0) {
                    uint64_t nk = P.setPos(key, id, r0 - 1);
                    addNeighbor(R.idx, R.nodes, R.parent, R.moveToHere, R.depth, curIdx, nk, id, 'U');
                    queueIdx.push_back((int)R.nodes.size() - 1);
                }
                // move down
                if (r0 + P.len[id] < 6 && grid[r0 + P.len[id]][c] == 0) {
                    uint64_t nk = P.setPos(key, id, r0 + 1);
                    addNeighbor(R.idx, R.nodes, R.parent, R.moveToHere, R.depth, curIdx, nk, id, 'D');
                    queueIdx.push_back((int)R.nodes.size() - 1);
                }
            }
        }
    }

    // Choose candidate state to maximize difficulty (heuristic: farthest from start)
    int bestIdx = 0;
    int bestDepth = 0;
    for (int i = 0; i < (int)R.nodes.size(); ++i) {
        if (R.depth[i] > bestDepth) {
            bestDepth = R.depth[i];
            bestIdx = i;
        }
    }

    // Compute exact minimal steps to goal from chosen state via BFS3
    auto beforeSolve = chrono::steady_clock::now();
    double timeUsed = chrono::duration<double>(beforeSolve - tStart).count();
    double timeLeft = TOTAL_TIME - timeUsed;
    // Even if low time left, we attempt BFS; it's required to be exact for chosen state.
    // BFS solve from bestIdx
    uint64_t startSolveKey = R.nodes[bestIdx];
    if (P.isGoal(startSolveKey)) {
        // Already at edge (inside-board), minimal steps to exit fully is 2
        // moves to form puzzle are the path to this state (bestIdx)
        vector<Move> path;
        int cur = bestIdx;
        while (R.parent[cur] != -1) {
            path.push_back(R.moveToHere[cur]);
            cur = R.parent[cur];
        }
        reverse(path.begin(), path.end());
        int minSteps = 2; // two steps to move completely out
        cout << minSteps << " " << (int)path.size() << "\n";
        for (auto &mv : path) {
            cout << mv.id << " " << mv.dir << "\n";
        }
        return 0;
    }

    unordered_map<uint64_t, int> dist;
    dist.reserve(200000);
    queue<uint64_t> q;
    dist.emplace(startSolveKey, 0);
    q.push(startSolveKey);

    int pos2[12];
    int grid2[6][6];
    int solveDist = -1;

    while (!q.empty()) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - tStart).count();
        if (elapsed > TOTAL_TIME) break;

        uint64_t key = q.front(); q.pop();
        int d = dist[key];

        if (P.isGoal(key)) {
            solveDist = d;
            break;
        }

        P.decode(key, pos2);
        P.buildGrid(pos2, grid2);

        for (int id = 1; id <= P.n; ++id) {
            if (P.horiz[id]) {
                int r = P.fixRow[id];
                int c0 = pos2[id];
                if (c0 > 0 && grid2[r][c0 - 1] == 0) {
                    uint64_t nk = P.setPos(key, id, c0 - 1);
                    if (dist.find(nk) == dist.end()) {
                        dist.emplace(nk, d + 1);
                        q.push(nk);
                    }
                }
                if (c0 + P.len[id] < 6 && grid2[r][c0 + P.len[id]] == 0) {
                    uint64_t nk = P.setPos(key, id, c0 + 1);
                    if (dist.find(nk) == dist.end()) {
                        dist.emplace(nk, d + 1);
                        q.push(nk);
                    }
                }
            } else {
                int c = P.fixCol[id];
                int r0 = pos2[id];
                if (r0 > 0 && grid2[r0 - 1][c] == 0) {
                    uint64_t nk = P.setPos(key, id, r0 - 1);
                    if (dist.find(nk) == dist.end()) {
                        dist.emplace(nk, d + 1);
                        q.push(nk);
                    }
                }
                if (r0 + P.len[id] < 6 && grid2[r0 + P.len[id]][c] == 0) {
                    uint64_t nk = P.setPos(key, id, r0 + 1);
                    if (dist.find(nk) == dist.end()) {
                        dist.emplace(nk, d + 1);
                        q.push(nk);
                    }
                }
            }
        }
    }

    if (solveDist < 0) {
        // Fallback: if time ran out (unlikely), estimate using zero
        solveDist = 0;
    }

    // Reconstruct path from initial to chosen bestIdx
    vector<Move> path;
    {
        int cur = bestIdx;
        while (R.parent[cur] != -1) {
            path.push_back(R.moveToHere[cur]);
            cur = R.parent[cur];
        }
        reverse(path.begin(), path.end());
    }

    int minStepsToExit = solveDist + 2; // add 2 steps to move red car completely out
    cout << minStepsToExit << " " << (int)path.size() << "\n";
    for (auto &mv : path) {
        cout << mv.id << " " << mv.dir << "\n";
    }
    return 0;
}