#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; ++i) cin >> g[i];

    vector<vector<int>> cellId(r, vector<int>(c, -1));
    vector<pair<int,int>> cellCoord;
    cellCoord.reserve(r * c);

    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '.') {
                cellId[i][j] = (int)cellCoord.size();
                cellCoord.emplace_back(i, j);
            }
        }
    }

    int cellCount = (int)cellCoord.size();
    if (cellCount == 0) {
        return 0;
    }

    const int dx[4] = {-1, 0, 1, 0};
    const int dy[4] = {0, 1, 0, -1};

    auto inside = [&](int x, int y) -> bool {
        return x >= 0 && x < r && y >= 0 && y < c;
    };

    int N = cellCount * 4;
    const int SINK = N;
    int TOT = N + 1;

    vector<int> Dist(N);
    vector<int> StepSucc(N, -1);
    int maxDist = 0;

    // Precompute distance to wall and step successors.
    for (int cid = 0; cid < cellCount; ++cid) {
        int i = cellCoord[cid].first;
        int j = cellCoord[cid].second;
        for (int dir = 0; dir < 4; ++dir) {
            int x = i + dx[dir];
            int y = j + dy[dir];
            int d = 0;
            while (inside(x, y) && g[x][y] == '.') {
                ++d;
                x += dx[dir];
                y += dy[dir];
            }
            int s = cid * 4 + dir;
            Dist[s] = d;
            if (d > maxDist) maxDist = d;
            if (d > 0) {
                int ni = i + dx[dir];
                int nj = j + dy[dir];
                int ncell = cellId[ni][nj];
                StepSucc[s] = ncell * 4 + dir;
            } else {
                StepSucc[s] = -1;
            }
        }
    }

    // Build labels and transition function with sink (for equivalence computation).
    vector<int> label(TOT);
    vector<array<int,3>> succ(TOT); // 0:left,1:right,2:step

    for (int s = 0; s < N; ++s) {
        label[s] = Dist[s];
        int cell = s / 4;
        int dir = s % 4;
        int leftDir = (dir + 3) & 3;
        int rightDir = (dir + 1) & 3;
        succ[s][0] = cell * 4 + leftDir;
        succ[s][1] = cell * 4 + rightDir;
        succ[s][2] = (StepSucc[s] != -1 ? StepSucc[s] : SINK);
    }
    label[SINK] = -1;
    succ[SINK][0] = succ[SINK][1] = succ[SINK][2] = SINK;

    // Compute equivalence classes via iterative refinement.
    vector<int> comp(TOT, 0), newComp(TOT);
    bool changed = true;
    vector<tuple<int,int,int,int,int>> arr;
    arr.reserve(TOT);

    while (changed) {
        arr.clear();
        for (int s = 0; s < TOT; ++s) {
            arr.emplace_back(label[s],
                             comp[succ[s][0]],
                             comp[succ[s][1]],
                             comp[succ[s][2]],
                             s);
        }
        sort(arr.begin(), arr.end(),
             [](const auto &a, const auto &b) {
                 if (get<0>(a) != get<0>(b)) return get<0>(a) < get<0>(b);
                 if (get<1>(a) != get<1>(b)) return get<1>(a) < get<1>(b);
                 if (get<2>(a) != get<2>(b)) return get<2>(a) < get<2>(b);
                 if (get<3>(a) != get<3>(b)) return get<3>(a) < get<3>(b);
                 return get<4>(a) < get<4>(b);
             });
        int curId = 0;
        newComp[get<4>(arr[0])] = 0;
        for (int i = 1; i < TOT; ++i) {
            if (get<0>(arr[i]) != get<0>(arr[i-1]) ||
                get<1>(arr[i]) != get<1>(arr[i-1]) ||
                get<2>(arr[i]) != get<2>(arr[i-1]) ||
                get<3>(arr[i]) != get<3>(arr[i-1])) {
                ++curId;
            }
            newComp[get<4>(arr[i])] = curId;
        }
        changed = false;
        for (int s = 0; s < TOT; ++s) {
            if (newComp[s] != comp[s]) {
                changed = true;
                break;
            }
        }
        comp.swap(newComp);
    }

    int numComp = 0;
    for (int s = 0; s < TOT; ++s)
        if (comp[s] + 1 > numComp)
            numComp = comp[s] + 1;

    // Count distinct positions (cells) within each equivalence class.
    vector<int> posCount(numComp, 0);
    vector<int> markCell(cellCount, -1);
    for (int s = 0; s < N; ++s) {
        int cid = comp[s];
        int cell = s / 4;
        if (markCell[cell] != cid) {
            markCell[cell] = cid;
            ++posCount[cid];
        }
    }

    // Candidate states: all possible oriented open cells.
    vector<char> possible(N, 1), newPossible(N);

    vector<int> candidateStates;
    candidateStates.reserve(N);

    int lastAction = -1; // -1 none, 0 left,1 right,2 step

    vector<char> cellPossible(cellCount);
    vector<char> compSeen(numComp);
    vector<int> cellList;
    cellList.reserve(cellCount);
    vector<int> compList;
    compList.reserve(numComp);

    vector<int> count(maxDist + 1);

    while (true) {
        int d_in;
        if (!(cin >> d_in)) return 0;
        if (d_in == -1) return 0;

        // Build current candidate state list.
        candidateStates.clear();
        for (int s = 0; s < N; ++s)
            if (possible[s]) candidateStates.push_back(s);

        // Apply last action to candidate states.
        if (lastAction != -1) {
            fill(newPossible.begin(), newPossible.end(), 0);
            if (lastAction == 0) { // left
                for (int s : candidateStates) {
                    int t = succ[s][0];
                    if (t < N) newPossible[t] = 1;
                }
            } else if (lastAction == 1) { // right
                for (int s : candidateStates) {
                    int t = succ[s][1];
                    if (t < N) newPossible[t] = 1;
                }
            } else if (lastAction == 2) { // step
                for (int s : candidateStates) {
                    int t = StepSucc[s];
                    if (t != -1) {
                        newPossible[t] = 1;
                    }
                }
            }
            possible.swap(newPossible);
            candidateStates.clear();
            for (int s = 0; s < N; ++s)
                if (possible[s]) candidateStates.push_back(s);
        }

        // Filter by observed distance.
        if (candidateStates.empty()) {
            for (int s = 0; s < N; ++s) {
                if (Dist[s] != d_in) possible[s] = 0;
            }
        } else {
            for (int s : candidateStates) {
                if (Dist[s] != d_in) possible[s] = 0;
            }
        }

        candidateStates.clear();
        for (int s = 0; s < N; ++s)
            if (possible[s]) candidateStates.push_back(s);

        if (candidateStates.empty()) {
            cout << "no\n";
            cout.flush();
            return 0;
        }

        // Determine how many distinct positions remain.
        fill(cellPossible.begin(), cellPossible.end(), 0);
        cellList.clear();
        for (int s : candidateStates) {
            int cell = s / 4;
            if (!cellPossible[cell]) {
                cellPossible[cell] = 1;
                cellList.push_back(cell);
            }
        }

        if (cellList.size() == 1) {
            int cell = cellList[0];
            int i = cellCoord[cell].first;
            int j = cellCoord[cell].second;
            cout << "yes " << (i + 1) << ' ' << (j + 1) << '\n';
            cout.flush();
            return 0;
        }

        // 'no' detection using equivalence classes.
        fill(compSeen.begin(), compSeen.end(), 0);
        compList.clear();
        for (int s : candidateStates) {
            int cid = comp[s];
            if (!compSeen[cid]) {
                compSeen[cid] = 1;
                compList.push_back(cid);
            }
        }
        if (compList.size() == 1) {
            int cid = compList[0];
            if (posCount[cid] > 1) {
                cout << "no\n";
                cout.flush();
                return 0;
            }
        }

        // Choose next action by minimizing worst-case candidate size after next observation.
        bool canStep = (d_in > 0);
        const int INF = 1e9;
        int bestAction = 0;
        int bestWorst = INF;

        for (int act = 0; act < 3; ++act) {
            if (act == 2 && !canStep) continue;

            fill(count.begin(), count.end(), 0);

            if (act == 0) { // left
                for (int s : candidateStates) {
                    int t = succ[s][0];
                    int d2 = Dist[t];
                    ++count[d2];
                }
            } else if (act == 1) { // right
                for (int s : candidateStates) {
                    int t = succ[s][1];
                    int d2 = Dist[t];
                    ++count[d2];
                }
            } else { // step
                for (int s : candidateStates) {
                    int t = StepSucc[s];
                    if (t == -1) continue;
                    int d2 = Dist[t];
                    ++count[d2];
                }
            }

            int worst = 0;
            for (int d2 = 0; d2 <= maxDist; ++d2) {
                if (count[d2] > worst) worst = count[d2];
            }

            if (worst < bestWorst ||
                (worst == bestWorst && act == 2 && canStep && bestAction != 2)) {
                bestWorst = worst;
                bestAction = act;
            }
        }

        if (bestAction == 0) {
            cout << "left\n";
            lastAction = 0;
        } else if (bestAction == 1) {
            cout << "right\n";
            lastAction = 1;
        } else {
            cout << "step\n";
            lastAction = 2;
        }
        cout.flush();
    }

    return 0;
}