#include <bits/stdc++.h>
using namespace std;

struct Move {
    uint8_t id;
    char dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int H = 6, W = 6, MAXV = 10;
    int grid[H][W];
    int maxid = 0;
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int x; 
            if (!(cin >> x)) return 0;
            grid[r][c] = x;
            if (x > maxid) maxid = x;
        }
    }
    int n = maxid;
    if (n == 0) {
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    vector<vector<pair<int,int>>> cells(n+1);
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int id = grid[r][c];
            if (id > 0) cells[id].push_back({r,c});
        }
    }

    vector<uint8_t> len(n), baseLen(n), ub(n);
    vector<uint8_t> isHor(n), fixedCoord(n), initPos(n);
    for (int id = 1; id <= n; ++id) {
        auto &vec = cells[id];
        sort(vec.begin(), vec.end());
        int l = (int)vec.size();
        len[id-1] = (uint8_t)l;
        bool allSameRow = true, allSameCol = true;
        for (int i = 1; i < l; ++i) {
            if (vec[i].first != vec[0].first) allSameRow = false;
            if (vec[i].second != vec[0].second) allSameCol = false;
        }
        if (allSameRow) {
            isHor[id-1] = 1;
            fixedCoord[id-1] = (uint8_t)vec[0].first;
            int minc = 6;
            for (auto &p : vec) minc = min(minc, p.second);
            initPos[id-1] = (uint8_t)minc;
        } else {
            isHor[id-1] = 0;
            fixedCoord[id-1] = (uint8_t)vec[0].second;
            int minr = 6;
            for (auto &p : vec) minr = min(minr, p.first);
            initPos[id-1] = (uint8_t)minr;
        }
        ub[id-1] = (uint8_t)(6 - len[id-1]);
        baseLen[id-1] = (uint8_t)(ub[id-1] + 1);
    }

    // Encode initial state
    using Code = uint32_t;
    vector<Code> basePow(n);
    basePow[0] = 1;
    for (int i = 1; i < n; ++i) basePow[i] = basePow[i-1] * baseLen[i-1];
    Code initCode = 0;
    for (int i = 0; i < n; ++i) {
        initCode += (Code)initPos[i] * basePow[i];
    }

    auto decode = [&](Code code, uint8_t pos[]) {
        for (int i = 0; i < n; ++i) {
            pos[i] = (uint8_t)(code % baseLen[i]);
            code /= baseLen[i];
        }
    };

    // Phase 1: BFS from initial, enumerate component and parents
    unordered_map<Code, int> idxMap;
    idxMap.reserve(200000);
    vector<Code> states;
    states.reserve(200000);
    vector<int> parent;
    vector<uint8_t> parentVid;
    vector<char> parentDir;

    idxMap.emplace(initCode, 0);
    states.push_back(initCode);
    parent.push_back(-1);
    parentVid.push_back(0);
    parentDir.push_back(' ');

    int front = 0;
    uint8_t pos[ MAXV ];
    int8_t occ[H][W];

    while (front < (int)states.size()) {
        Code code = states[front];
        decode(code, pos);

        // Build occupancy
        for (int r = 0; r < H; ++r) for (int c = 0; c < W; ++c) occ[r][c] = -1;
        for (int i = 0; i < n; ++i) {
            if (isHor[i]) {
                int r = fixedCoord[i];
                int c0 = pos[i];
                for (int k = 0; k < len[i]; ++k) occ[r][c0 + k] = i;
            } else {
                int c = fixedCoord[i];
                int r0 = pos[i];
                for (int k = 0; k < len[i]; ++k) occ[r0 + k][c] = i;
            }
        }

        // Generate neighbors (1-step moves)
        for (int i = 0; i < n; ++i) {
            if (isHor[i]) {
                int r = fixedCoord[i];
                int c0 = pos[i];
                // Left
                if (c0 > 0 && occ[r][c0 - 1] == -1) {
                    Code ncode = code - basePow[i];
                    auto it = idxMap.find(ncode);
                    if (it == idxMap.end()) {
                        int ni = (int)states.size();
                        idxMap.emplace(ncode, ni);
                        states.push_back(ncode);
                        parent.push_back(front);
                        parentVid.push_back((uint8_t)(i + 1));
                        parentDir.push_back('L');
                    }
                }
                // Right
                if (c0 + len[i] <= 5 && occ[r][c0 + len[i]] == -1) {
                    Code ncode = code + basePow[i];
                    auto it = idxMap.find(ncode);
                    if (it == idxMap.end()) {
                        int ni = (int)states.size();
                        idxMap.emplace(ncode, ni);
                        states.push_back(ncode);
                        parent.push_back(front);
                        parentVid.push_back((uint8_t)(i + 1));
                        parentDir.push_back('R');
                    }
                }
            } else {
                int c = fixedCoord[i];
                int r0 = pos[i];
                // Up
                if (r0 > 0 && occ[r0 - 1][c] == -1) {
                    Code ncode = code - basePow[i];
                    auto it = idxMap.find(ncode);
                    if (it == idxMap.end()) {
                        int ni = (int)states.size();
                        idxMap.emplace(ncode, ni);
                        states.push_back(ncode);
                        parent.push_back(front);
                        parentVid.push_back((uint8_t)(i + 1));
                        parentDir.push_back('U');
                    }
                }
                // Down
                if (r0 + len[i] <= 5 && occ[r0 + len[i]][c] == -1) {
                    Code ncode = code + basePow[i];
                    auto it = idxMap.find(ncode);
                    if (it == idxMap.end()) {
                        int ni = (int)states.size();
                        idxMap.emplace(ncode, ni);
                        states.push_back(ncode);
                        parent.push_back(front);
                        parentVid.push_back((uint8_t)(i + 1));
                        parentDir.push_back('D');
                    }
                }
            }
        }

        ++front;
    }

    int S = (int)states.size();

    // Phase 2: Multi-source BFS from goal states (red car anchor at 4)
    vector<int> distToGoal(S, -1);
    vector<int> q;
    q.reserve(S);
    for (int i = 0; i < S; ++i) {
        decode(states[i], pos);
        if (pos[0] == 4) {
            distToGoal[i] = 0;
            q.push_back(i);
        }
    }

    int qf = 0;
    while (qf < (int)q.size()) {
        int idx = q[qf++];
        Code code = states[idx];
        decode(code, pos);

        // Build occupancy
        for (int r = 0; r < H; ++r) for (int c = 0; c < W; ++c) occ[r][c] = -1;
        for (int i = 0; i < n; ++i) {
            if (isHor[i]) {
                int r = fixedCoord[i];
                int c0 = pos[i];
                for (int k = 0; k < len[i]; ++k) occ[r][c0 + k] = i;
            } else {
                int c = fixedCoord[i];
                int r0 = pos[i];
                for (int k = 0; k < len[i]; ++k) occ[r0 + k][c] = i;
            }
        }

        // Neighbors
        for (int i = 0; i < n; ++i) {
            if (isHor[i]) {
                int r = fixedCoord[i];
                int c0 = pos[i];
                if (c0 > 0 && occ[r][c0 - 1] == -1) {
                    Code ncode = code - basePow[i];
                    int j = idxMap[ncode];
                    if (distToGoal[j] == -1) {
                        distToGoal[j] = distToGoal[idx] + 1;
                        q.push_back(j);
                    }
                }
                if (c0 + len[i] <= 5 && occ[r][c0 + len[i]] == -1) {
                    Code ncode = code + basePow[i];
                    int j = idxMap[ncode];
                    if (distToGoal[j] == -1) {
                        distToGoal[j] = distToGoal[idx] + 1;
                        q.push_back(j);
                    }
                }
            } else {
                int c = fixedCoord[i];
                int r0 = pos[i];
                if (r0 > 0 && occ[r0 - 1][c] == -1) {
                    Code ncode = code - basePow[i];
                    int j = idxMap[ncode];
                    if (distToGoal[j] == -1) {
                        distToGoal[j] = distToGoal[idx] + 1;
                        q.push_back(j);
                    }
                }
                if (r0 + len[i] <= 5 && occ[r0 + len[i]][c] == -1) {
                    Code ncode = code + basePow[i];
                    int j = idxMap[ncode];
                    if (distToGoal[j] == -1) {
                        distToGoal[j] = distToGoal[idx] + 1;
                        q.push_back(j);
                    }
                }
            }
        }
    }

    // Choose best state maximizing distToGoal
    int bestIdx = 0;
    int bestDist = distToGoal[0];
    for (int i = 1; i < S; ++i) {
        if (distToGoal[i] > bestDist) {
            bestDist = distToGoal[i];
            bestIdx = i;
        }
    }

    int solveSteps = bestDist + 2;
    // reconstruct path from init (index 0) to bestIdx
    vector<Move> path;
    int cur = bestIdx;
    while (cur != 0) {
        Move m{parentVid[cur], parentDir[cur]};
        path.push_back(m);
        cur = parent[cur];
    }
    reverse(path.begin(), path.end());

    cout << solveSteps << " " << path.size() << "\n";
    for (auto &m : path) {
        cout << (int)m.id << " " << m.dir << "\n";
    }

    return 0;
}