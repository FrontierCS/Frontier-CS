#include <bits/stdc++.h>
using namespace std;

const int BOARD_SIZE = 6;
const int MAX_VEHICLES = 10;
const int BITS_PER_VEHICLE = 3;
const int POS_MASK = (1 << BITS_PER_VEHICLE) - 1;

struct CustomHash {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const noexcept {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return splitmix64(x + FIXED_RANDOM);
    }
};

int numVehicles;
bool isHoriz[MAX_VEHICLES];
int fixedCoord[MAX_VEHICLES]; // row if horiz, col if vert
int lengthV[MAX_VEHICLES];
int targetLeft;    // last fully on-board left position before exit
int exitExtra;     // extra steps from targetLeft to fully exit (len of red)

// encode/decode positions array to 64-bit key
inline uint64_t encodePositions(const int pos[]) {
    uint64_t key = 0;
    for (int i = 0; i < numVehicles; ++i) {
        key |= (uint64_t(pos[i]) << (i * BITS_PER_VEHICLE));
    }
    return key;
}

inline void decodePositions(uint64_t key, int pos[]) {
    for (int i = 0; i < numVehicles; ++i) {
        pos[i] = int(key & POS_MASK);
        key >>= BITS_PER_VEHICLE;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int boardInput[BOARD_SIZE][BOARD_SIZE];
    for (int r = 0; r < BOARD_SIZE; ++r) {
        for (int c = 0; c < BOARD_SIZE; ++c) {
            if (!(cin >> boardInput[r][c])) return 0;
        }
    }

    // Collect cells per vehicle id
    vector<pair<int,int>> cells[MAX_VEHICLES + 1];
    int maxId = 0;
    for (int r = 0; r < BOARD_SIZE; ++r) {
        for (int c = 0; c < BOARD_SIZE; ++c) {
            int id = boardInput[r][c];
            if (id > 0) {
                if (id <= MAX_VEHICLES) {
                    cells[id].push_back({r, c});
                    if (id > maxId) maxId = id;
                }
            }
        }
    }
    numVehicles = maxId;

    int startPos[MAX_VEHICLES];

    // Deduce orientation, fixed coord, length, starting pos
    for (int id = 1; id <= numVehicles; ++id) {
        auto &v = cells[id];
        int idx = id - 1;
        int len = (int)v.size();
        lengthV[idx] = len;
        if (len >= 2) {
            // Determine orientation
            bool horiz = (v[0].first == v[1].first);
            isHoriz[idx] = horiz;
            if (horiz) {
                int row = v[0].first;
                int minC = BOARD_SIZE;
                for (auto &p : v) {
                    // p.first should equal row
                    if (p.second < minC) minC = p.second;
                }
                fixedCoord[idx] = row;
                startPos[idx] = minC;
            } else {
                int col = v[0].second;
                int minR = BOARD_SIZE;
                for (auto &p : v) {
                    // p.second should equal col
                    if (p.first < minR) minR = p.first;
                }
                fixedCoord[idx] = col;
                startPos[idx] = minR;
            }
        } else {
            // Should not happen in valid input
            isHoriz[idx] = true;
            fixedCoord[idx] = 0;
            startPos[idx] = 0;
        }
    }

    // Red car is id 1, index 0
    int redIdx = 0;
    int lenRed = lengthV[redIdx];
    exitExtra = lenRed;
    targetLeft = BOARD_SIZE - lenRed; // last fully on-board position

    // BFS from initial state: build full reachable component
    unordered_map<uint64_t,int,CustomHash> idMap;
    idMap.reserve(2000000);
    idMap.max_load_factor(0.7f);

    vector<uint64_t> states;
    states.reserve(2000000);
    vector<int> distInit;
    distInit.reserve(2000000);
    vector<int> parentIdx;
    parentIdx.reserve(2000000);
    vector<uint8_t> parentVehicle;
    parentVehicle.reserve(2000000);
    vector<char> parentDir;
    parentDir.reserve(2000000);
    vector<int> nearSolvedIndices;
    nearSolvedIndices.reserve(1024);

    int posArr[MAX_VEHICLES];
    memcpy(posArr, startPos, sizeof(int) * numVehicles);
    uint64_t startKey = encodePositions(posArr);

    states.push_back(startKey);
    distInit.push_back(0);
    parentIdx.push_back(-1);
    parentVehicle.push_back(0);
    parentDir.push_back(0);
    idMap[startKey] = 0;

    queue<int> q;
    q.push(0);

    int board[BOARD_SIZE][BOARD_SIZE];

    while (!q.empty()) {
        int idx = q.front();
        q.pop();
        uint64_t key = states[idx];

        // Decode positions
        decodePositions(key, posArr);

        // Build board occupancy
        memset(board, 0, sizeof(board));
        for (int i = 0; i < numVehicles; ++i) {
            int len = lengthV[i];
            if (isHoriz[i]) {
                int r = fixedCoord[i];
                int c0 = posArr[i];
                for (int d = 0; d < len; ++d) {
                    board[r][c0 + d] = i + 1;
                }
            } else {
                int c = fixedCoord[i];
                int r0 = posArr[i];
                for (int d = 0; d < len; ++d) {
                    board[r0 + d][c] = i + 1;
                }
            }
        }

        // Near-solved detection: red at targetLeft
        if (posArr[redIdx] == targetLeft) {
            nearSolvedIndices.push_back(idx);
        }

        int curDist = distInit[idx];

        // Generate neighbors
        for (int i = 0; i < numVehicles; ++i) {
            int len = lengthV[i];
            if (isHoriz[i]) {
                int r = fixedCoord[i];
                int c = posArr[i];

                // Move left
                if (c > 0 && board[r][c - 1] == 0) {
                    posArr[i] = c - 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it == idMap.end()) {
                        int newIdx = (int)states.size();
                        states.push_back(key2);
                        distInit.push_back(curDist + 1);
                        parentIdx.push_back(idx);
                        parentVehicle.push_back((uint8_t)(i + 1));
                        parentDir.push_back('L');
                        idMap[key2] = newIdx;
                        q.push(newIdx);
                    }
                    posArr[i] = c;
                }

                // Move right
                if (c + len < BOARD_SIZE && board[r][c + len] == 0) {
                    posArr[i] = c + 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it == idMap.end()) {
                        int newIdx = (int)states.size();
                        states.push_back(key2);
                        distInit.push_back(curDist + 1);
                        parentIdx.push_back(idx);
                        parentVehicle.push_back((uint8_t)(i + 1));
                        parentDir.push_back('R');
                        idMap[key2] = newIdx;
                        q.push(newIdx);
                    }
                    posArr[i] = c;
                }
            } else {
                int c = fixedCoord[i];
                int r = posArr[i];

                // Move up
                if (r > 0 && board[r - 1][c] == 0) {
                    posArr[i] = r - 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it == idMap.end()) {
                        int newIdx = (int)states.size();
                        states.push_back(key2);
                        distInit.push_back(curDist + 1);
                        parentIdx.push_back(idx);
                        parentVehicle.push_back((uint8_t)(i + 1));
                        parentDir.push_back('U');
                        idMap[key2] = newIdx;
                        q.push(newIdx);
                    }
                    posArr[i] = r;
                }

                // Move down
                if (r + len < BOARD_SIZE && board[r + len][c] == 0) {
                    posArr[i] = r + 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it == idMap.end()) {
                        int newIdx = (int)states.size();
                        states.push_back(key2);
                        distInit.push_back(curDist + 1);
                        parentIdx.push_back(idx);
                        parentVehicle.push_back((uint8_t)(i + 1));
                        parentDir.push_back('D');
                        idMap[key2] = newIdx;
                        q.push(newIdx);
                    }
                    posArr[i] = r;
                }
            }
        }
    }

    int N = (int)states.size();

    // If no near-solved states found (shouldn't happen for solvable puzzles), fall back to initial
    if (nearSolvedIndices.empty()) {
        // Trivial output: keep initial puzzle
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    // BFS2: distances to nearest near-solved state (red at targetLeft)
    const int INF = 1e9;
    vector<int> distSolve(N, INF);
    queue<int> q2;
    for (int idx : nearSolvedIndices) {
        if (distSolve[idx] == 0) continue;
        distSolve[idx] = 0;
        q2.push(idx);
    }

    while (!q2.empty()) {
        int idx = q2.front();
        q2.pop();
        uint64_t key = states[idx];

        decodePositions(key, posArr);

        memset(board, 0, sizeof(board));
        for (int i = 0; i < numVehicles; ++i) {
            int len = lengthV[i];
            if (isHoriz[i]) {
                int r = fixedCoord[i];
                int c0 = posArr[i];
                for (int d = 0; d < len; ++d) {
                    board[r][c0 + d] = i + 1;
                }
            } else {
                int c = fixedCoord[i];
                int r0 = posArr[i];
                for (int d = 0; d < len; ++d) {
                    board[r0 + d][c] = i + 1;
                }
            }
        }

        int curDist = distSolve[idx];

        for (int i = 0; i < numVehicles; ++i) {
            int len = lengthV[i];
            if (isHoriz[i]) {
                int r = fixedCoord[i];
                int c = posArr[i];

                // left
                if (c > 0 && board[r][c - 1] == 0) {
                    posArr[i] = c - 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it != idMap.end()) {
                        int nb = it->second;
                        if (distSolve[nb] == INF) {
                            distSolve[nb] = curDist + 1;
                            q2.push(nb);
                        }
                    }
                    posArr[i] = c;
                }

                // right
                if (c + len < BOARD_SIZE && board[r][c + len] == 0) {
                    posArr[i] = c + 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it != idMap.end()) {
                        int nb = it->second;
                        if (distSolve[nb] == INF) {
                            distSolve[nb] = curDist + 1;
                            q2.push(nb);
                        }
                    }
                    posArr[i] = c;
                }
            } else {
                int c = fixedCoord[i];
                int r = posArr[i];

                // up
                if (r > 0 && board[r - 1][c] == 0) {
                    posArr[i] = r - 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it != idMap.end()) {
                        int nb = it->second;
                        if (distSolve[nb] == INF) {
                            distSolve[nb] = curDist + 1;
                            q2.push(nb);
                        }
                    }
                    posArr[i] = r;
                }

                // down
                if (r + len < BOARD_SIZE && board[r + len][c] == 0) {
                    posArr[i] = r + 1;
                    uint64_t key2 = encodePositions(posArr);
                    auto it = idMap.find(key2);
                    if (it != idMap.end()) {
                        int nb = it->second;
                        if (distSolve[nb] == INF) {
                            distSolve[nb] = curDist + 1;
                            q2.push(nb);
                        }
                    }
                    posArr[i] = r;
                }
            }
        }
    }

    // Choose best new puzzle: maximize minimal steps to solve
    int bestStepsSolve = -1;
    int bestIdx = 0;
    for (int i = 0; i < N; ++i) {
        if (distSolve[i] == INF) continue;
        int total = distSolve[i] + exitExtra;
        if (total > bestStepsSolve) {
            bestStepsSolve = total;
            bestIdx = i;
        }
    }

    int stepsForm = distInit[bestIdx];

    // Reconstruct path from initial (idx 0) to bestIdx
    vector<pair<int,char>> path;
    int cur = bestIdx;
    while (parentIdx[cur] != -1) {
        path.push_back({ (int)parentVehicle[cur], parentDir[cur] });
        cur = parentIdx[cur];
    }
    reverse(path.begin(), path.end());

    cout << bestStepsSolve << " " << stepsForm << "\n";
    for (auto &mv : path) {
        cout << mv.first << " " << mv.second << "\n";
    }

    return 0;
}