#include <bits/stdc++.h>
using namespace std;

struct Move { int id; char dir; };

struct Node {
    array<uint8_t, 10> r{};
    array<uint8_t, 10> c{};
};

int N = 0;
array<char, 10> orient; // 'H' or 'V'
array<int, 10> vlen;    // 2 or 3

uint64_t packKey(const Node& s) {
    uint64_t key = 0;
    int shift = 0;
    for (int i = 0; i < N; ++i) {
        key |= (uint64_t(s.r[i]) & 7u) << shift; shift += 3;
        key |= (uint64_t(s.c[i]) & 7u) << shift; shift += 3;
    }
    return key;
}

inline char opposite(char d) {
    if (d == 'U') return 'D';
    if (d == 'D') return 'U';
    if (d == 'L') return 'R';
    if (d == 'R') return 'L';
    return '?';
}

void buildBoard(const Node& s, int board[6][6]) {
    for (int i = 0; i < 6; ++i) for (int j = 0; j < 6; ++j) board[i][j] = 0;
    for (int i = 0; i < N; ++i) {
        if (orient[i] == 'H') {
            int rr = s.r[i];
            int cc = s.c[i];
            for (int k = 0; k < vlen[i]; ++k) {
                int c2 = cc + k;
                if (0 <= rr && rr < 6 && 0 <= c2 && c2 < 6) board[rr][c2] = i + 1;
            }
        } else {
            int rr = s.r[i];
            int cc = s.c[i];
            for (int k = 0; k < vlen[i]; ++k) {
                int r2 = rr + k;
                if (0 <= r2 && r2 < 6 && 0 <= cc && cc < 6) board[r2][cc] = i + 1;
            }
        }
    }
}

int solveMinSteps(const Node& start) {
    if (start.c[0] >= 6) return 0;
    vector<Node> q;
    vector<int> dist;
    q.reserve(50000);
    dist.reserve(50000);
    unordered_set<uint64_t> seen;
    seen.reserve(200000);
    uint64_t k0 = packKey(start);
    seen.insert(k0);
    q.push_back(start);
    dist.push_back(0);
    size_t head = 0;
    int board[6][6];

    while (head < q.size()) {
        const Node cur = q[head];
        int d = dist[head];
        if (cur.c[0] >= 6) return d;
        buildBoard(cur, board);

        for (int i = 0; i < N; ++i) {
            if (orient[i] == 'H') {
                // Left
                if (cur.c[i] > 0 && board[cur.r[i]][cur.c[i] - 1] == 0) {
                    Node nxt = cur;
                    nxt.c[i]--;
                    uint64_t kk = packKey(nxt);
                    if (seen.insert(kk).second) {
                        q.push_back(nxt);
                        dist.push_back(d + 1);
                    }
                }
                // Right
                bool allowR = false;
                if (cur.c[i] + vlen[i] <= 5) {
                    allowR = (board[cur.r[i]][cur.c[i] + vlen[i]] == 0);
                } else if (i == 0 && cur.c[i] < 6) {
                    // Red car allowed to go out of the board to the right up to c==6
                    allowR = true;
                }
                if (allowR) {
                    Node nxt = cur;
                    nxt.c[i]++;
                    uint64_t kk = packKey(nxt);
                    if (seen.insert(kk).second) {
                        q.push_back(nxt);
                        dist.push_back(d + 1);
                    }
                }
            } else {
                // Vertical
                // Up
                if (cur.r[i] > 0 && board[cur.r[i] - 1][cur.c[i]] == 0) {
                    Node nxt = cur;
                    nxt.r[i]--;
                    uint64_t kk = packKey(nxt);
                    if (seen.insert(kk).second) {
                        q.push_back(nxt);
                        dist.push_back(d + 1);
                    }
                }
                // Down
                if (cur.r[i] + vlen[i] <= 5 && board[cur.r[i] + vlen[i]][cur.c[i]] == 0) {
                    Node nxt = cur;
                    nxt.r[i]++;
                    uint64_t kk = packKey(nxt);
                    if (seen.insert(kk).second) {
                        q.push_back(nxt);
                        dist.push_back(d + 1);
                    }
                }
            }
        }
        head++;
    }
    // Should be solvable as per problem statement
    return INT_MAX / 2;
}

void getPossibleMovesFormation(const Node& st, vector<Move>& out, int forbidId, char forbidDir) {
    out.clear();
    int board[6][6];
    buildBoard(st, board);
    for (int i = 0; i < N; ++i) {
        if (orient[i] == 'H') {
            // Left
            if (st.c[i] > 0 && board[st.r[i]][st.c[i] - 1] == 0) {
                if (!(i == forbidId && opposite(forbidDir) == 'L')) {
                    out.push_back({i, 'L'});
                }
            }
            // Right (formation: cannot go out of grid)
            if (st.c[i] + vlen[i] <= 5 && board[st.r[i]][st.c[i] + vlen[i]] == 0) {
                if (!(i == forbidId && opposite(forbidDir) == 'R')) {
                    out.push_back({i, 'R'});
                }
            }
        } else {
            // Up
            if (st.r[i] > 0 && board[st.r[i] - 1][st.c[i]] == 0) {
                if (!(i == forbidId && opposite(forbidDir) == 'U')) {
                    out.push_back({i, 'U'});
                }
            }
            // Down
            if (st.r[i] + vlen[i] <= 5 && board[st.r[i] + vlen[i]][st.c[i]] == 0) {
                if (!(i == forbidId && opposite(forbidDir) == 'D')) {
                    out.push_back({i, 'D'});
                }
            }
        }
    }
}

void applyMove(Node& s, const Move& m) {
    if (m.dir == 'L') s.c[m.id]--;
    else if (m.dir == 'R') s.c[m.id]++;
    else if (m.dir == 'U') s.r[m.id]--;
    else if (m.dir == 'D') s.r[m.id]++;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read input board
    int grid[6][6];
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            if (!(cin >> grid[i][j])) return 0;
        }
    }

    int maxId = 0;
    for (int i = 0; i < 6; ++i)
        for (int j = 0; j < 6; ++j)
            maxId = max(maxId, grid[i][j]);
    N = maxId;

    vector<vector<pair<int,int>>> cells(N + 1);
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            int id = grid[i][j];
            if (id > 0) cells[id].push_back({i, j});
        }
    }

    Node initial;
    for (int id = 1; id <= N; ++id) {
        auto& vec = cells[id];
        if (vec.empty()) continue;
        sort(vec.begin(), vec.end());
        // Determine orientation and length
        if (vec.size() >= 2) {
            if (vec[0].first == vec[1].first) orient[id - 1] = 'H';
            else orient[id - 1] = 'V';
        } else {
            // Shouldn't happen
            orient[id - 1] = 'H';
        }
        vlen[id - 1] = (int)vec.size();
        if (orient[id - 1] == 'H') {
            int rr = vec[0].first;
            int cc = 7;
            for (auto &p : vec) cc = min(cc, p.second);
            initial.r[id - 1] = rr;
            initial.c[id - 1] = cc;
        } else {
            int rr = 7;
            int cc = vec[0].second;
            for (auto &p : vec) rr = min(rr, p.first);
            initial.r[id - 1] = rr;
            initial.c[id - 1] = cc;
        }
    }

    // Random engine
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Cache for evaluated states
    unordered_map<uint64_t, int> distCache;
    distCache.reserve(10000);

    // Initial distance
    int bestDist;
    {
        uint64_t k0 = packKey(initial);
        auto it = distCache.find(k0);
        if (it != distCache.end()) bestDist = it->second;
        else {
            bestDist = solveMinSteps(initial);
            distCache.emplace(k0, bestDist);
        }
    }

    Node bestState = initial;
    vector<Move> bestMoves;

    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.90; // seconds
    int evals = 0;
    const int MAX_EVALS = 200;

    vector<Move> moves, candMoves;
    vector<Move> possible;
    possible.reserve(64);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > TIME_LIMIT * 0.9) break; // leave time at the end

        Node cur = initial;
        moves.clear();
        int lastId = -1;
        char lastDir = '?';

        int L = 200; // length of random walk
        int sampleFreq = 8 + (rng() % 5); // sample every 8-12 steps

        for (int step = 1; step <= L; ++step) {
            getPossibleMovesFormation(cur, possible, lastId, lastDir);
            if (possible.empty()) break;
            // Randomly pick a move, slightly bias against moving red right
            int idx;
            if (N > 0 && (rng() & 7) && !possible.empty()) {
                // try avoid 'red right' sometimes
                vector<int> idxs;
                idxs.reserve(possible.size());
                for (int ii = 0; ii < (int)possible.size(); ++ii) {
                    if (!(possible[ii].id == 0 && possible[ii].dir == 'R')) idxs.push_back(ii);
                }
                if (!idxs.empty()) idx = idxs[rng() % idxs.size()];
                else idx = rng() % possible.size();
            } else {
                idx = rng() % possible.size();
            }
            Move mv = possible[idx];
            applyMove(cur, mv);
            moves.push_back({mv.id, mv.dir});
            lastId = mv.id; lastDir = mv.dir;

            if (step % sampleFreq == 0 || step == L) {
                now = chrono::steady_clock::now();
                elapsed = chrono::duration<double>(now - startTime).count();
                if (elapsed > TIME_LIMIT * 0.95) break;
                uint64_t k = packKey(cur);
                int d;
                auto it = distCache.find(k);
                if (it != distCache.end()) {
                    d = it->second;
                } else {
                    if (evals >= MAX_EVALS) continue;
                    d = solveMinSteps(cur);
                    distCache.emplace(k, d);
                    evals++;
                }
                if (d > bestDist) {
                    bestDist = d;
                    bestState = cur;
                    bestMoves = moves;
                }
            }
        }
    }

    // Ensure we have exact bestDist cached
    {
        uint64_t kb = packKey(bestState);
        auto it = distCache.find(kb);
        if (it == distCache.end()) {
            bestDist = solveMinSteps(bestState);
            distCache.emplace(kb, bestDist);
        } else {
            bestDist = it->second;
        }
    }

    cout << bestDist << " " << bestMoves.size() << "\n";
    for (auto &mv : bestMoves) {
        int vid = mv.id + 1;
        cout << vid << " " << mv.dir << "\n";
    }

    return 0;
}