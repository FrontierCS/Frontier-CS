#include <bits/stdc++.h>
using namespace std;

struct Move {
    int id; // 0-based
    int dir; // 0:L,1:R,2:U,3:D
};

static const char DIR_CHARS[4] = {'L','R','U','D'};
static const int OPP[4] = {1,0,3,2};

int n; // number of vehicles
vector<int> lenv; // length of each vehicle (2 or 3)
vector<char> isH; // 1 if horizontal
vector<int> fixr; // fixed row for horizontal vehicles (1..6)
vector<int> fixc; // fixed col for vertical vehicles (1..6)
vector<int> startPos; // initial pos: leftmost col for H, topmost row for V

// Encode state positions (3 bits per vehicle, values 0..7)
using Key = unsigned long long;

inline Key encodeKey(const vector<int>& pos) {
    Key k = 0;
    for (int i = 0; i < n; ++i) {
        k |= (Key)(pos[i] & 7) << (3*i);
    }
    return k;
}
inline void decodeKey(Key k, vector<int>& pos) {
    for (int i = 0; i < n; ++i) {
        pos[i] = (int)((k >> (3*i)) & 7ULL);
    }
}

inline void buildBoard(const vector<int>& pos, unsigned char board[7][7]) {
    for (int r=1;r<=6;r++) for (int c=1;c<=6;c++) board[r][c]=0;
    for (int i=0;i<n;i++) {
        if (isH[i]) {
            int r = fixr[i];
            int c0 = pos[i];
            for (int k=0;k<lenv[i];k++) {
                int c = c0 + k;
                if (c>=1 && c<=6) board[r][c] = (unsigned char)(i+1);
            }
        } else {
            int c = fixc[i];
            int r0 = pos[i];
            for (int k=0;k<lenv[i];k++) {
                int r = r0 + k;
                if (r>=1 && r<=6) board[r][c] = (unsigned char)(i+1);
            }
        }
    }
}

inline void applyMoveInPlace(vector<int>& pos, const Move& m) {
    if (m.dir==0) pos[m.id]--;
    else if (m.dir==1) pos[m.id]++;
    else if (m.dir==2) pos[m.id]--;
    else if (m.dir==3) pos[m.id]++;
}

// Generate one-step legal moves for formation (all vehicles stay fully on board)
inline void genNeighborsFormation(const vector<int>& pos, vector<Move>& out, const Move* prev) {
    unsigned char board[7][7];
    buildBoard(pos, board);
    out.clear();
    for (int i=0;i<n;i++) {
        if (isH[i]) {
            int r = fixr[i];
            int c0 = pos[i];
            // left
            if (c0 > 1 && board[r][c0-1]==0) {
                Move m{i,0};
                if (!(prev && prev->id==i && prev->dir==OPP[m.dir])) out.push_back(m);
            }
            // right (stay on board)
            if (c0 + lenv[i] - 1 < 6) {
                int nc = c0 + lenv[i];
                if (board[r][nc]==0) {
                    Move m{i,1};
                    if (!(prev && prev->id==i && prev->dir==OPP[m.dir])) out.push_back(m);
                }
            }
        } else {
            int c = fixc[i];
            int r0 = pos[i];
            // up
            if (r0 > 1 && board[r0-1][c]==0) {
                Move m{i,2};
                if (!(prev && prev->id==i && prev->dir==OPP[m.dir])) out.push_back(m);
            }
            // down (stay on board)
            if (r0 + lenv[i] - 1 < 6) {
                int nr = r0 + lenv[i];
                if (board[nr][c]==0) {
                    Move m{i,3};
                    if (!(prev && prev->id==i && prev->dir==OPP[m.dir])) out.push_back(m);
                }
            }
        }
    }
}

// Generate neighbors for solver BFS (stay on board for all vehicles; exit handled separately)
inline void genNeighborsSolver(const vector<int>& pos, vector<Key>& outKeys, Key curKey) {
    unsigned char board[7][7];
    buildBoard(pos, board);
    outKeys.clear();
    for (int i=0;i<n;i++) {
        if (isH[i]) {
            int r = fixr[i];
            int c0 = pos[i];
            // left
            if (c0 > 1 && board[r][c0-1]==0) {
                int np = c0 - 1;
                Key nk = (curKey & ~(7ULL << (3*i))) | ((Key)np << (3*i));
                outKeys.push_back(nk);
            }
            // right (stay on board)
            if (c0 + lenv[i] - 1 < 6) {
                int nc = c0 + lenv[i];
                if (board[r][nc]==0) {
                    int np = c0 + 1;
                    Key nk = (curKey & ~(7ULL << (3*i))) | ((Key)np << (3*i));
                    outKeys.push_back(nk);
                }
            }
        } else {
            int c = fixc[i];
            int r0 = pos[i];
            // up
            if (r0 > 1 && board[r0-1][c]==0) {
                int np = r0 - 1;
                Key nk = (curKey & ~(7ULL << (3*i))) | ((Key)np << (3*i));
                outKeys.push_back(nk);
            }
            // down (stay on board)
            if (r0 + lenv[i] - 1 < 6) {
                int nr = r0 + lenv[i];
                if (board[nr][c]==0) {
                    int np = r0 + 1;
                    Key nk = (curKey & ~(7ULL << (3*i))) | ((Key)np << (3*i));
                    outKeys.push_back(nk);
                }
            }
        }
    }
}

// Cache for hardness evaluations
unordered_map<Key,int> hardnessCache;

// BFS solver: minimal steps to move red car (id=1 index 0) totally out (row 3, horizontal).
int solve_min_steps(const vector<int>& startPosVec) {
    Key startKey = encodeKey(startPosVec);
    auto itc = hardnessCache.find(startKey);
    if (itc != hardnessCache.end()) return itc->second;

    // BFS over on-board states only; compute candidate cost when exit path is clear
    deque<Key> q;
    unordered_map<Key,int> dist;
    q.push_back(startKey);
    dist.reserve(100000);
    dist[startKey] = 0;

    vector<int> pos(n);
    vector<Key> neighKeys;
    int best = INT_MAX;

    while (!q.empty()) {
        Key k = q.front(); q.pop_front();
        int d = dist[k];
        // Prune if further exploration cannot beat best
        if (best != INT_MAX && d >= best - 2) continue;

        decodeKey(k, pos);
        unsigned char board[7][7];
        buildBoard(pos, board);

        int c = pos[0]; // red car leftmost col (1..5)
        int r = fixr[0];
        bool clear = true;
        int rightStart = c + lenv[0];
        for (int cc = rightStart; cc <= 6; ++cc) {
            if (board[r][cc] != 0) { clear = false; break; }
        }
        if (clear) {
            int candidate = d + (7 - c); // from pos c, need (5-c) to [5,6] + 2 more = 7 - c
            if (candidate < best) best = candidate;
            if (best == d + 2) {
                // minimal possible from this layer, still continue to process other same-layer states via pruning
            }
        }

        genNeighborsSolver(pos, neighKeys, k);
        for (Key nk : neighKeys) {
            if (dist.find(nk) == dist.end()) {
                dist[nk] = d + 1;
                q.push_back(nk);
            }
        }
    }

    if (best == INT_MAX) best = 0; // should not happen due to guarantee
    hardnessCache[startKey] = best;
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read input board
    int a[7][7];
    int maxid = 0;
    for (int r=1;r<=6;r++){
        for (int c=1;c<=6;c++){
            int x; if(!(cin>>x)) x=0;
            a[r][c] = x;
            if (x > maxid) maxid = x;
        }
    }
    n = maxid;
    if (n <= 0) {
        cout << "0 0\n";
        return 0;
    }
    lenv.assign(n,2);
    isH.assign(n,0);
    fixr.assign(n,0);
    fixc.assign(n,0);
    startPos.assign(n,1);

    // Collect cells per id
    vector<vector<pair<int,int>>> cells(n+1);
    for (int r=1;r<=6;r++){
        for (int c=1;c<=6;c++){
            int id = a[r][c];
            if (id>=1 && id<=n) cells[id].push_back({r,c});
        }
    }
    for (int id=1; id<=n; ++id) {
        auto &v = cells[id];
        int cnt = (int)v.size();
        lenv[id-1] = cnt; // 2 or 3
        // Determine orientation
        bool horiz = false;
        if (cnt >= 2) {
            if (v[0].first == v[1].first) horiz = true;
            else horiz = false;
        } else {
            // Shouldn't happen
            // Default guess
            horiz = true;
        }
        isH[id-1] = horiz ? 1 : 0;
        if (horiz) {
            int r = v[0].first;
            for (auto &p : v) r = p.first; // all equal
            int minc = 7;
            for (auto &p : v) minc = min(minc, p.second);
            fixr[id-1] = r;
            startPos[id-1] = minc;
        } else {
            int c = v[0].second;
            for (auto &p : v) c = p.second; // all equal
            int minr = 7;
            for (auto &p : v) minr = min(minr, p.first);
            fixc[id-1] = c;
            startPos[id-1] = minr;
        }
    }
    // Assert red car is horizontal and row 3 (given guaranteed)
    // But to be safe, set fixr[0] to its row.
    // Already set above.

    // Initial hardness
    int initHard = solve_min_steps(startPos);

    // Local search to find a harder configuration
    vector<Move> bestPath;
    vector<Move> curPath;

    vector<int> bestState = startPos;
    vector<int> curState = startPos;

    int bestHard = initHard;
    int curHard = initHard;

    Move lastMove{-1,-1};
    vector<Move> neighMoves;

    // Random engine
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto getTime = [](){ return chrono::steady_clock::now(); };
    auto startTime = getTime();
    const int TIME_LIMIT_MS = 1900; // a bit under 2s
    const int GREEDY_SAMPLE = 10; // number of neighbors to sample/evaluate per step
    const int MAX_STEPS = 100000; // safety

    int steps = 0;
    while (steps < MAX_STEPS) {
        auto now = getTime();
        int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - startTime).count();
        if (elapsed > TIME_LIMIT_MS) break;

        genNeighborsFormation(curState, neighMoves, (lastMove.id>=0? &lastMove : nullptr));
        if (neighMoves.empty()) {
            // restart from best
            curState = bestState;
            curPath = bestPath;
            lastMove = Move{-1,-1};
            continue;
        }

        // sample some neighbors to evaluate
        vector<int> idx(neighMoves.size());
        iota(idx.begin(), idx.end(), 0);
        shuffle(idx.begin(), idx.end(), rng);
        int evalCount = min((int)idx.size(), GREEDY_SAMPLE);
        int chosenIdx = idx[0];
        int chosenHard = -1;
        int bestLocalHard = -1;
        int bestLocalIdx = -1;

        for (int ei=0; ei<evalCount; ++ei) {
            int mvIdx = idx[ei];
            Move mv = neighMoves[mvIdx];
            vector<int> tmp = curState;
            applyMoveInPlace(tmp, mv);
            int h = solve_min_steps(tmp);
            if (h > bestLocalHard) {
                bestLocalHard = h;
                bestLocalIdx = mvIdx;
            }
            // Early accept if it strictly improves global best by significant margin
        }
        // Choose move
        Move chosenMove;
        bool improvement = false;
        if (bestLocalIdx != -1) {
            chosenIdx = bestLocalIdx;
            chosenMove = neighMoves[chosenIdx];
            vector<int> tmp = curState;
            applyMoveInPlace(tmp, chosenMove);
            chosenHard = solve_min_steps(tmp);
            improvement = (chosenHard > curHard);
        } else {
            chosenMove = neighMoves[0];
        }

        // Occasionally accept non-improving move
        bool accept = improvement;
        if (!accept) {
            uniform_int_distribution<int> dist(0, 9);
            int r = dist(rng);
            if (r < 3) accept = true; // 30% chance
        }

        if (!accept) {
            // pick random neighbor
            uniform_int_distribution<int> dist2(0, (int)neighMoves.size()-1);
            chosenIdx = dist2(rng);
            chosenMove = neighMoves[chosenIdx];
            vector<int> tmp = curState;
            applyMoveInPlace(tmp, chosenMove);
            chosenHard = solve_min_steps(tmp);
        }

        // Apply chosen move
        applyMoveInPlace(curState, chosenMove);
        curPath.push_back(chosenMove);
        lastMove = chosenMove;
        curHard = chosenHard;

        // Update best
        if (curHard > bestHard) {
            bestHard = curHard;
            bestState = curState;
            bestPath = curPath;
        }

        // Occasionally restart from best to focus search
        if ((int)curPath.size() > 200) {
            curState = bestState;
            curPath = bestPath;
            lastMove = Move{-1,-1};
        }

        steps++;
    }

    // Output result
    cout << bestHard << " " << bestPath.size() << "\n";
    for (auto &m : bestPath) {
        cout << (m.id+1) << " " << DIR_CHARS[m.dir] << "\n";
    }
    return 0;
}