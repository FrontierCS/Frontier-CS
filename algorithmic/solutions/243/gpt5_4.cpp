#include <bits/stdc++.h>
using namespace std;

struct ActionRes {
    vector<int> states; // unique next states after applying action
    int worstCount;     // worst-case size after observing next distance
    int uniqueD;        // number of distinct next distances
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // Map open cells to indices
    vector<int> cellIndex(r * c, -1);
    vector<pair<int,int>> idxToCell;
    idxToCell.reserve(r * c);
    int openCnt = 0;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                cellIndex[i * c + j] = openCnt++;
                idxToCell.emplace_back(i, j);
            }
        }
    }
    if (openCnt == 0) {
        // No open cells: immediately stop (nothing to do)
        return 0;
    }

    // Directions: 0=up,1=right,2=down,3=left
    int dr[4] = {-1, 0, 1, 0};
    int dc[4] = {0, 1, 0, -1};

    int N = openCnt * 4; // total number of states (position + direction)

    // Precompute distance to wall for each state
    vector<int> distLabel(N, 0);
    int maxDist = 0;

    auto inb = [&](int x, int y) -> bool { return x >= 0 && x < r && y >= 0 && y < c; };

    for (int idx = 0; idx < openCnt; ++idx) {
        int i = idxToCell[idx].first;
        int j = idxToCell[idx].second;
        for (int d = 0; d < 4; ++d) {
            int ni = i + dr[d], nj = j + dc[d];
            int dist = 0;
            while (inb(ni, nj) && grid[ni][nj] == '.') {
                dist++;
                ni += dr[d];
                nj += dc[d];
            }
            distLabel[idx * 4 + d] = dist;
            if (dist > maxDist) maxDist = dist;
        }
    }
    if (maxDist < 0) maxDist = 0;
    if (maxDist > 1000) maxDist = 1000; // safety cap

    // Transitions
    vector<int> transLeft(N), transRight(N), transStep(N, -1);
    vector<int> posR(N), posC(N), posDir(N);

    for (int idx = 0; idx < openCnt; ++idx) {
        int i = idxToCell[idx].first;
        int j = idxToCell[idx].second;
        for (int d = 0; d < 4; ++d) {
            int id = idx * 4 + d;
            posR[id] = i; posC[id] = j; posDir[id] = d;
            transLeft[id] = idx * 4 + ((d + 3) & 3);
            transRight[id] = idx * 4 + ((d + 1) & 3);
            if (distLabel[id] > 0) {
                int ni = i + dr[d];
                int nj = j + dc[d];
                if (inb(ni, nj) && grid[ni][nj] == '.') {
                    int nidx = cellIndex[ni * c + nj];
                    transStep[id] = nidx * 4 + d;
                } else {
                    transStep[id] = -1; // should not happen since dist>0 ensures next is open
                }
            }
        }
    }

    // Initial belief: all states
    vector<int> S;
    S.reserve(N);
    for (int id = 0; id < N; ++id) S.push_back(id);

    // helper to deduplicate and count next-distance partitions
    vector<int> mark(N, 0);
    int curMark = 1;

    auto computeAction = [&](const vector<int>& curS, char act) -> ActionRes {
        ActionRes res;
        res.worstCount = 0;
        res.uniqueD = 0;
        vector<int> counts(maxDist + 1, 0);

        int nextId;
        for (int id : curS) {
            if (act == 'L') nextId = transLeft[id];
            else if (act == 'R') nextId = transRight[id];
            else { // 'S'
                nextId = transStep[id];
                if (nextId == -1) continue; // should not happen if step is allowed
            }
            if (mark[nextId] != curMark) {
                mark[nextId] = curMark;
                res.states.push_back(nextId);
                int dnext = distLabel[nextId];
                if (dnext < 0) dnext = 0;
                if (dnext > maxDist) dnext = maxDist;
                counts[dnext]++;
                if (counts[dnext] == 1) res.uniqueD++;
                if (counts[dnext] > res.worstCount) res.worstCount = counts[dnext];
            }
        }
        curMark++;
        return res;
    };

    auto allSameCell = [&](const vector<int>& curS) -> bool {
        if (curS.empty()) return false;
        int i0 = posR[curS[0]];
        int j0 = posC[curS[0]];
        for (int id : curS) {
            if (posR[id] != i0 || posC[id] != j0) return false;
        }
        return true;
    };

    // Interaction loop
    int d;
    int rounds = 0;
    const int MAX_ROUNDS = 100000; // safety cutoff to avoid infinite loops in pathological cases
    while (cin >> d) {
        if (d == -1) {
            // Interactor requests termination
            return 0;
        }
        // Filter S by observed distance
        vector<int> S2;
        S2.reserve(S.size());
        for (int id : S) {
            if (distLabel[id] == d) S2.push_back(id);
        }
        S.swap(S2);

        if (S.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        if (allSameCell(S)) {
            int i0 = posR[S[0]] + 1;
            int j0 = posC[S[0]] + 1;
            cout << "yes " << i0 << " " << j0 << endl;
            cout.flush();
            return 0;
        }

        // Choose action: left, right always allowed; step allowed iff d > 0
        vector<pair<char, ActionRes>> candidates;
        // Left
        ActionRes resL = computeAction(S, 'L');
        candidates.push_back({'L', resL});
        // Right
        ActionRes resR = computeAction(S, 'R');
        candidates.push_back({'R', resR});
        // Step if safe
        if (d > 0) {
            ActionRes resS = computeAction(S, 'S');
            candidates.push_back({'S', resS});
        }

        // Select best by minimizing worstCount, tie-break by smaller states.size(), then prefer step, then left
        int bestIdx = -1;
        for (int i = 0; i < (int)candidates.size(); ++i) {
            if (bestIdx == -1) {
                bestIdx = i;
            } else {
                if (candidates[i].second.worstCount < candidates[bestIdx].second.worstCount) {
                    bestIdx = i;
                } else if (candidates[i].second.worstCount == candidates[bestIdx].second.worstCount) {
                    if (candidates[i].second.states.size() < candidates[bestIdx].second.states.size()) {
                        bestIdx = i;
                    } else if (candidates[i].second.states.size() == candidates[bestIdx].second.states.size()) {
                        // prefer step if available
                        if (candidates[i].first == 'S' && candidates[bestIdx].first != 'S') {
                            bestIdx = i;
                        } else if (candidates[i].first != 'S' && candidates[bestIdx].first != 'S') {
                            // prefer left over right
                            if (candidates[i].first == 'L' && candidates[bestIdx].first == 'R') {
                                bestIdx = i;
                            }
                        }
                    }
                }
            }
        }

        if (bestIdx == -1) {
            // Should not happen
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        char act = candidates[bestIdx].first;
        if (act == 'L') {
            cout << "left" << endl;
        } else if (act == 'R') {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }
        cout.flush();

        // Update belief to post-action states
        S.swap(candidates[bestIdx].second.states);
        rounds++;
        if (rounds > MAX_ROUNDS) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }
    }
    return 0;
}