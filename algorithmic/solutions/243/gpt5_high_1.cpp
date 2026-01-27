#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // Map positions
    vector<vector<int>> posId(r, vector<int>(c, -1));
    vector<pair<int,int>> idToPos;
    int posCount = 0;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                posId[i][j] = posCount++;
                idToPos.emplace_back(i, j);
            }
        }
    }
    if (posCount == 0) return 0; // No open squares, nothing to do.

    const int DIRS = 4;
    int Nstates = posCount * DIRS;

    // Direction vectors: 0=N,1=E,2=S,3=W
    int dr[4] = {-1, 0, 1, 0};
    int dc[4] = {0, 1, 0, -1};

    // Precompute observation: distance to wall ahead
    vector<int> obs(Nstates, 0);
    for (int p = 0; p < posCount; ++p) {
        auto [i, j] = idToPos[p];
        for (int d = 0; d < 4; ++d) {
            int cnt = 0;
            int ni = i + dr[d];
            int nj = j + dc[d];
            while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                cnt++;
                ni += dr[d];
                nj += dc[d];
            }
            obs[p*4 + d] = cnt;
        }
    }

    // Precompute transitions
    vector<int> nextLeft(Nstates, -1), nextRight(Nstates, -1), nextStep(Nstates, -1);
    for (int p = 0; p < posCount; ++p) {
        auto [i, j] = idToPos[p];
        for (int d = 0; d < 4; ++d) {
            int s = p*4 + d;
            int dl = (d + 3) & 3;
            int drt = (d + 1) & 3;
            nextLeft[s] = p*4 + dl;
            nextRight[s] = p*4 + drt;
            if (obs[s] >= 1) {
                int ni = i + dr[d];
                int nj = j + dc[d];
                int p2 = posId[ni][nj];
                if (p2 != -1) nextStep[s] = p2*4 + d;
            } else {
                nextStep[s] = -1;
            }
        }
    }

    // Initialize state set: all open cells times 4 directions
    vector<int> S;
    S.reserve(Nstates);
    for (int s = 0; s < Nstates; ++s) S.push_back(s);

    // Helpers for dedup and scoring
    vector<int> stateMark(Nstates, -1);
    int stateMarkTag = 1;

    int maxD = max(r, c); // distances up to 100 approx
    vector<int> countByObs(maxD + 5, 0);
    vector<int> tagStamp(maxD + 5, 0);
    vector<int> posSeenTag(posCount, 0);
    int curPosSeenTag = 1;

    auto unique_positions_count = [&](const vector<int>& states) -> int {
        int cnt = 0;
        ++curPosSeenTag;
        for (int s : states) {
            int p = s / 4;
            if (posSeenTag[p] != curPosSeenTag) {
                posSeenTag[p] = curPosSeenTag;
                ++cnt;
            }
        }
        return cnt;
    };

    auto step_is_universally_safe = [&](const vector<int>& states) -> bool {
        for (int s : states) {
            if (nextStep[s] == -1) return false;
        }
        return true;
    };

    auto apply_action = [&](const vector<int>& states, int action, vector<int>& outStates) {
        // action: 0=left, 1=right, 2=step
        ++stateMarkTag;
        outStates.clear();
        outStates.reserve(states.size());
        if (action == 0) {
            for (int s : states) {
                int t = nextLeft[s];
                if (stateMark[t] != stateMarkTag) {
                    stateMark[t] = stateMarkTag;
                    outStates.push_back(t);
                }
            }
        } else if (action == 1) {
            for (int s : states) {
                int t = nextRight[s];
                if (stateMark[t] != stateMarkTag) {
                    stateMark[t] = stateMarkTag;
                    outStates.push_back(t);
                }
            }
        } else {
            for (int s : states) {
                int t = nextStep[s];
                if (t == -1) continue; // shouldn't happen if universally safe
                if (stateMark[t] != stateMarkTag) {
                    stateMark[t] = stateMarkTag;
                    outStates.push_back(t);
                }
            }
        }
    };

    auto score_action = [&](const vector<int>& states, int action) {
        vector<int> nextStates;
        apply_action(states, action, nextStates);

        // Group nextStates by observation value
        int worstPos = 0;
        int worstStates = 0;

        // Reset tagging for groups
        int usedMaxD = maxD + 2;
        // We will use tagStamp[v] to store a token to associate with posSeenTag marking
        // Prepare a unique token for each obs value encountered
        int localGroupTokenBase = curPosSeenTag + 1;
        int localToken = localGroupTokenBase;

        // Reset counts
        // Instead of clearing entire countByObs, we will track obs values encountered
        vector<int> obsValuesUsed;
        obsValuesUsed.reserve(128);

        // Map obs value to index in obsValuesUsed to iterate later
        // We'll use a small array for small obs range
        vector<int> have(maxD + 5, 0);

        for (int s : nextStates) {
            int v = obs[s];
            if (!have[v]) {
                have[v] = 1;
                obsValuesUsed.push_back(v);
                countByObs[v] = 0;
                tagStamp[v] = ++localToken; // unique token for this group
            }
            countByObs[v]++;
            int p = s / 4;
            if (posSeenTag[p] != tagStamp[v]) {
                posSeenTag[p] = tagStamp[v];
            }
        }

        for (int v : obsValuesUsed) {
            // Count unique positions for group v
            int posCountGroup = 0;
            int token = tagStamp[v];
            // We need to count how many posSeenTag entries equal token.
            // But we didn't count while iterating. We'll count now by iterating nextStates again.
            // To avoid O(|nextStates| * #groups) we can recollect positions per group in a map.
            // Simpler: iterate nextStates once more and count unique positions for each group.
        }

        // To avoid extra passes, let's do it better: we need to compute position counts per group while building.
        // We'll rebuild properly.

        // Rebuild tracking with single pass: map obs value -> position count
        // Reset structures
        // Clear previous marks
        // We'll redo apply_action and compute both counts together:

        apply_action(states, action, nextStates);

        // Reset group used flags
        fill(have.begin(), have.end(), 0);
        obsValuesUsed.clear();

        // posGroupTag[v] token
        // We'll reuse posSeenTag with different tokens per group v
        localToken = curPosSeenTag + 1;
        for (int s : nextStates) {
            int v = obs[s];
            if (!have[v]) {
                have[v] = 1;
                obsValuesUsed.push_back(v);
                countByObs[v] = 0; // states count
                tagStamp[v] = ++localToken; // unique token for group v
            }
            countByObs[v]++;

            int p = s / 4;
            if (posSeenTag[p] != tagStamp[v]) {
                posSeenTag[p] = tagStamp[v];
                // We need another array to count positions per group; reuse countByObsPos?
                // We don't have it, so we'll repurpose countByObsPos using another array.
            }
        }

        // We need two counts per group: states and positions.
        // Let's redo with two arrays.
        vector<int> posCountGroup(maxD + 5, 0);
        // Reset and compute again:

        // Clear marks and recalc
        // Reapply action again (third pass)
        apply_action(states, action, nextStates);
        fill(have.begin(), have.end(), 0);
        obsValuesUsed.clear();
        localToken = curPosSeenTag + 1;

        for (int s : nextStates) {
            int v = obs[s];
            if (!have[v]) {
                have[v] = 1;
                obsValuesUsed.push_back(v);
                countByObs[v] = 0;
                posCountGroup[v] = 0;
                tagStamp[v] = ++localToken;
            }
            countByObs[v]++;

            int p = s / 4;
            if (posSeenTag[p] != tagStamp[v]) {
                posSeenTag[p] = tagStamp[v];
                posCountGroup[v]++;
            }
        }

        for (int v : obsValuesUsed) {
            worstStates = max(worstStates, countByObs[v]);
            worstPos = max(worstPos, posCountGroup[v]);
        }

        return tuple<int,int,int>(worstPos, worstStates, (int)nextStates.size());
    };

    auto choose_action = [&](const vector<int>& states) -> int {
        // 0=left,1=right,2=step
        bool canStep = step_is_universally_safe(states);
        vector<int> actions;
        actions.push_back(0);
        actions.push_back(1);
        if (canStep) actions.push_back(2);

        tuple<int,int,int> bestScore = make_tuple(INT_MAX, INT_MAX, INT_MAX);
        int bestAction = actions[0];
        for (int a : actions) {
            auto sc = score_action(states, a);
            if (sc < bestScore) {
                bestScore = sc;
                bestAction = a;
            }
        }
        return bestAction;
    };

    // We will run interaction rounds
    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Filter S by observation equal to d
        vector<int> Snew;
        Snew.reserve(S.size());
        for (int s : S) {
            if (obs[s] == d) Snew.push_back(s);
        }
        S.swap(Snew);

        if (S.empty()) {
            cout << "no" << endl << flush;
            return 0;
        }

        // Check if position is determined
        int uniquePos = -1;
        bool multiplePos = false;
        ++curPosSeenTag;
        for (int s : S) {
            int p = s / 4;
            if (posSeenTag[p] != curPosSeenTag) {
                if (uniquePos == -1) uniquePos = p;
                else multiplePos = true;
                posSeenTag[p] = curPosSeenTag;
                if (multiplePos) break;
            }
        }
        if (!multiplePos && uniquePos != -1) {
            int i = idToPos[uniquePos].first + 1;
            int j = idToPos[uniquePos].second + 1;
            cout << "yes " << i << " " << j << endl << flush;
            return 0;
        }

        // Choose action
        int action = choose_action(S);
        if (action == 2) {
            cout << "step" << endl << flush;
        } else if (action == 0) {
            cout << "left" << endl << flush;
        } else {
            cout << "right" << endl << flush;
        }

        // Update S to post-action states
        vector<int> S1;
        apply_action(S, action, S1);
        S.swap(S1);
    }

    return 0;
}