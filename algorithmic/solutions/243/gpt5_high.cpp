#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, dir;
    int d;       // distance to wall in current direction
    int left_id, right_id, step_id; // transitions (step_id = -1 if not allowed)
    int posId;   // position id (i,j)
};

struct Sig {
    int d, l, r, st;
    bool operator==(const Sig& o) const {
        return d==o.d && l==o.l && r==o.r && st==o.st;
    }
};
struct SigHash {
    size_t operator()(Sig const& s) const noexcept {
        // combine integers
        size_t h = s.d * 1315423911u + 2654435761u;
        h ^= (size_t)s.l + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
        h ^= (size_t)s.r + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
        h ^= (size_t)(s.st+2) + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
        return h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) {
        return 0;
    }
    vector<string> grid(r+2, string(c+2, '#'));
    for (int i = 1; i <= r; ++i) {
        string line;
        cin >> line;
        for (int j = 1; j <= c; ++j) {
            grid[i][j] = line[j-1];
        }
    }

    // Directions: 0 up, 1 right, 2 down, 3 left
    int dx[4] = {-1, 0, 1, 0};
    int dy[4] = {0, 1, 0, -1};

    // Precompute distances to wall in each direction
    vector<vector<int>> distUp(r+2, vector<int>(c+2, 0));
    vector<vector<int>> distDown(r+2, vector<int>(c+2, 0));
    vector<vector<int>> distLeft(r+2, vector<int>(c+2, 0));
    vector<vector<int>> distRight(r+2, vector<int>(c+2, 0));

    // Up: number of open cells above until wall/outside
    for (int j = 1; j <= c; ++j) {
        distUp[1][j] = 0; // outside above row 1
        for (int i = 2; i <= r; ++i) {
            if (grid[i-1][j] == '.') distUp[i][j] = distUp[i-1][j] + 1;
            else distUp[i][j] = 0;
        }
    }
    // Down
    for (int j = 1; j <= c; ++j) {
        distDown[r][j] = 0;
        for (int i = r-1; i >= 1; --i) {
            if (grid[i+1][j] == '.') distDown[i][j] = distDown[i+1][j] + 1;
            else distDown[i][j] = 0;
        }
    }
    // Left
    for (int i = 1; i <= r; ++i) {
        distLeft[i][1] = 0;
        for (int j = 2; j <= c; ++j) {
            if (grid[i][j-1] == '.') distLeft[i][j] = distLeft[i][j-1] + 1;
            else distLeft[i][j] = 0;
        }
    }
    // Right
    for (int i = 1; i <= r; ++i) {
        distRight[i][c] = 0;
        for (int j = c-1; j >= 1; --j) {
            if (grid[i][j+1] == '.') distRight[i][j] = distRight[i][j+1] + 1;
            else distRight[i][j] = 0;
        }
    }

    // Position ids for open cells
    vector<vector<int>> posId(r+2, vector<int>(c+2, -1));
    int nPos = 0;
    for (int i = 1; i <= r; ++i) {
        for (int j = 1; j <= c; ++j) {
            if (grid[i][j] == '.') {
                posId[i][j] = nPos++;
            }
        }
    }
    if (nPos == 0) {
        // Should not happen due to problem statement "at least one open square"
        return 0;
    }

    // State ids map
    vector<vector<array<int,4>>> stateId(r+2, vector<array<int,4>>(c+2, array<int,4>{-1,-1,-1,-1}));
    vector<State> states;
    states.reserve(nPos * 4);

    auto get_d = [&](int i, int j, int dir)->int{
        if (dir == 0) return distUp[i][j];
        if (dir == 1) return distRight[i][j];
        if (dir == 2) return distDown[i][j];
        return distLeft[i][j];
    };

    // Create states
    for (int i = 1; i <= r; ++i) {
        for (int j = 1; j <= c; ++j) {
            if (grid[i][j] == '.') {
                for (int dir = 0; dir < 4; ++dir) {
                    int id = (int)states.size();
                    stateId[i][j][dir] = id;
                    State s;
                    s.i = i; s.j = j; s.dir = dir;
                    s.d = get_d(i,j,dir);
                    s.left_id = -1; s.right_id = -1; s.step_id = -1;
                    s.posId = posId[i][j];
                    states.push_back(s);
                }
            }
        }
    }
    int nStates = (int)states.size();

    // Fill transitions
    for (int id = 0; id < nStates; ++id) {
        State &s = states[id];
        int i = s.i, j = s.j, dir = s.dir;
        int dirL = (dir + 3) % 4;
        int dirR = (dir + 1) % 4;
        s.left_id = stateId[i][j][dirL];
        s.right_id = stateId[i][j][dirR];
        if (s.d >= 1) {
            int ni = i + dx[dir];
            int nj = j + dy[dir];
            if (grid[ni][nj] == '.') {
                s.step_id = stateId[ni][nj][dir];
            } else {
                s.step_id = -1; // shouldn't happen due to d>=1
            }
        } else {
            s.step_id = -1;
        }
    }

    // Compute equivalence classes (bisimulation with observation d and actions left/right/step if allowed)
    vector<int> classId(nStates, -1), newClassId(nStates, -1);
    // Initial partition by d value
    vector<int> uniqueDs;
    uniqueDs.reserve(100);
    {
        unordered_map<int, int> d2cls;
        int cid = 0;
        for (int id = 0; id < nStates; ++id) {
            int d = states[id].d;
            auto it = d2cls.find(d);
            if (it == d2cls.end()) {
                d2cls.emplace(d, cid);
                classId[id] = cid;
                uniqueDs.push_back(d);
                cid++;
            } else {
                classId[id] = it->second;
            }
        }
    }

    bool changed = true;
    vector<int> leftCls(nStates), rightCls(nStates), stepCls(nStates);
    while (changed) {
        for (int id = 0; id < nStates; ++id) {
            leftCls[id] = classId[states[id].left_id];
            rightCls[id] = classId[states[id].right_id];
            stepCls[id] = (states[id].step_id == -1) ? -1 : classId[states[id].step_id];
        }
        unordered_map<Sig, int, SigHash> mp;
        mp.reserve(nStates * 2);
        int cid = 0;
        changed = false;
        for (int id = 0; id < nStates; ++id) {
            Sig key{states[id].d, leftCls[id], rightCls[id], stepCls[id]};
            auto it = mp.find(key);
            if (it == mp.end()) {
                mp.emplace(key, cid);
                newClassId[id] = cid;
                cid++;
            } else {
                newClassId[id] = it->second;
            }
            if (newClassId[id] != classId[id]) changed = true;
        }
        classId.swap(newClassId);
    }
    int nClasses = 0;
    for (int x : classId) nClasses = max(nClasses, x+1);

    // For each class, compute number of distinct positions it contains
    vector<vector<int>> classMembers(nClasses);
    for (int id = 0; id < nStates; ++id) {
        classMembers[classId[id]].push_back(id);
    }
    vector<int> classPosUniqueCount(nClasses, 0);
    vector<int> tmpPos;
    tmpPos.reserve(4*max(1,nPos));
    for (int cid = 0; cid < nClasses; ++cid) {
        tmpPos.clear();
        for (int id : classMembers[cid]) tmpPos.push_back(states[id].posId);
        sort(tmpPos.begin(), tmpPos.end());
        tmpPos.erase(unique(tmpPos.begin(), tmpPos.end()), tmpPos.end());
        classPosUniqueCount[cid] = (int)tmpPos.size();
    }

    // Initialize candidate states set S as all states
    vector<int> S;
    S.reserve(nStates);
    for (int id = 0; id < nStates; ++id) S.push_back(id);

    // Helper to count unique positions in S
    vector<int> posMark(nPos, 0);
    int curMark = 1;
    auto countUniquePositionsInSet = [&](const vector<int>& vec, bool useNextPos, const string& act)->pair<int,int> {
        // Returns (unique positions count, total states count)
        // useNextPos: if true and act == "step", uses positions of next state after step, else current positions
        int uniqueCount = 0;
        int totalCount = (int)vec.size();
        if (curMark == INT_MAX) {
            fill(posMark.begin(), posMark.end(), 0);
            curMark = 1;
        }
        for (int id : vec) {
            int pos = -1;
            if (useNextPos && act == "step") {
                int nid = states[id].step_id;
                if (nid == -1) continue; // shouldn't happen if step allowed based on observed d
                pos = states[nid].posId;
            } else {
                pos = states[id].posId;
            }
            if (posMark[pos] != curMark) {
                posMark[pos] = curMark;
                uniqueCount++;
            }
        }
        curMark++;
        return {uniqueCount, totalCount};
    };

    auto chooseAction = [&](const vector<int>& curS, int observed_d)->string {
        vector<string> actions;
        actions.push_back("left");
        actions.push_back("right");
        if (observed_d > 0) actions.push_back("step");

        string bestAct = actions[0];
        int bestWorstPos = INT_MAX;
        int bestWorstStates = INT_MAX;

        for (const string& act : actions) {
            // Partition by next d
            unordered_map<int, vector<int>> groups; // d2 -> list of state ids (pre-action) belonging to group
            groups.reserve(curS.size()*2);
            for (int id : curS) {
                int nid = -1;
                if (act == "left") nid = states[id].left_id;
                else if (act == "right") nid = states[id].right_id;
                else if (act == "step") nid = states[id].step_id;
                if (nid == -1) continue; // step might be invalid for some (shouldn't if observed_d > 0)
                int d2 = states[nid].d;
                groups[d2].push_back(id);
            }
            // compute worst-case by positions after action
            int worstPos = 0;
            int worstStates = 0;
            for (auto &kv : groups) {
                const vector<int>& vec = kv.second;
                auto pr = countUniquePositionsInSet(vec, true, act);
                worstPos = max(worstPos, pr.first);
                worstStates = max(worstStates, pr.second);
            }
            // if groups empty (shouldn't happen) set worst high
            if (groups.empty()) {
                worstPos = INT_MAX/2;
                worstStates = INT_MAX/2;
            }
            if (worstPos < bestWorstPos || (worstPos == bestWorstPos && worstStates < bestWorstStates)) {
                bestWorstPos = worstPos;
                bestWorstStates = worstStates;
                bestAct = act;
            }
        }
        return bestAct;
    };

    // Interactive loop
    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Filter S by current observation d (states at current time)
        {
            vector<int> filtered;
            filtered.reserve(S.size());
            for (int id : S) {
                if (states[id].d == d) filtered.push_back(id);
            }
            S.swap(filtered);
        }

        // If impossible situation: no states match
        if (S.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        // Check if unique position
        {
            // Count unique positions in S (current positions)
            auto pr = countUniquePositionsInSet(S, false, "");
            if (pr.first == 1) {
                // Find the unique position (i,j)
                int pid = -1;
                for (int id : S) { pid = states[id].posId; break; }
                // decode posId to (i,j)
                int target_i = -1, target_j = -1;
                // We need a map from posId to (i,j)
                // Build on the fly by scanning neighbors around first state's (i,j) not efficient; better precompute a vector
                // Let's precompute posId to coords once
                // We'll break out to compute once; But we don't have stored mapping; Let's build now:

                static bool posCoordsBuilt = false;
                static vector<pair<int,int>> posCoords;
                if (!posCoordsBuilt) {
                    posCoords.assign(nPos, {-1,-1});
                    for (int ii = 1; ii <= r; ++ii) {
                        for (int jj = 1; jj <= c; ++jj) {
                            if (grid[ii][jj] == '.') {
                                int p = posId[ii][jj];
                                posCoords[p] = {ii, jj};
                            }
                        }
                    }
                    posCoordsBuilt = true;
                }
                target_i = posCoords[pid].first;
                target_j = posCoords[pid].second;

                cout << "yes " << target_i << " " << target_j << endl;
                cout.flush();
                return 0;
            }
        }

        // Check if S is subset of a single equivalence class with multiple positions -> impossible to localize
        {
            int cid0 = classId[S[0]];
            bool allSame = true;
            for (int id : S) {
                if (classId[id] != cid0) { allSame = false; break; }
            }
            if (allSame) {
                if (classPosUniqueCount[cid0] > 1) {
                    cout << "no" << endl;
                    cout.flush();
                    return 0;
                }
            }
        }

        // Choose action
        string action = chooseAction(S, d);
        cout << action << endl;
        cout.flush();

        // Update S by applying action transition
        vector<int> nextS;
        nextS.reserve(S.size());
        if (action == "left") {
            for (int id : S) nextS.push_back(states[id].left_id);
        } else if (action == "right") {
            for (int id : S) nextS.push_back(states[id].right_id);
        } else if (action == "step") {
            // Ensure safe for actual state: step allowed iff d >= 1
            // We're already reading observed d, so action chosen "step" only when d > 0
            for (int id : S) {
                int nid = states[id].step_id;
                if (nid != -1) nextS.push_back(nid);
                else {
                    // Shouldn't happen because all in S had same d
                    // Keep as is (ignore)
                }
            }
        } else {
            // Unknown action; should not happen
            return 0;
        }
        S.swap(nextS);
        if (S.empty()) {
            // Should not happen; but handle gracefully
            cout << "no" << endl;
            cout.flush();
            return 0;
        }
    }

    return 0;
}