#include <bits/stdc++.h>
using namespace std;

int R, C;
vector<string> grid;

vector<int> posR, posC, stateObs, nextL, nextR, nextStep;
int MaxObs = 0;

string choose_action(const vector<int>& cand) {
    vector<int> freq(MaxObs + 1);
    int bestWorst = INT_MAX;
    string best = "left";

    // Evaluate "left"
    int worst = 0;
    for (int id : cand) {
        int nid = nextL[id];
        int d = stateObs[nid];
        int &f = freq[d];
        ++f;
        if (f > worst) worst = f;
    }
    bestWorst = worst;
    best = "left";

    // Evaluate "right"
    fill(freq.begin(), freq.end(), 0);
    worst = 0;
    for (int id : cand) {
        int nid = nextR[id];
        int d = stateObs[nid];
        int &f = freq[d];
        ++f;
        if (f > worst) worst = f;
    }
    if (worst < bestWorst) {
        bestWorst = worst;
        best = "right";
    }

    // Evaluate "step" if safe for all candidates
    bool stepSafe = true;
    for (int id : cand) {
        if (nextStep[id] == -1) {
            stepSafe = false;
            break;
        }
    }
    if (stepSafe) {
        fill(freq.begin(), freq.end(), 0);
        worst = 0;
        for (int id : cand) {
            int nid = nextStep[id];
            int d = stateObs[nid];
            int &f = freq[d];
            ++f;
            if (f > worst) worst = f;
        }
        if (worst < bestWorst || (worst == bestWorst && best != "step")) {
            bestWorst = worst;
            best = "step";
        }
    }

    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> R >> C)) return 0;
    grid.resize(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    vector<vector<int>> cellId(R, vector<int>(C, -1));
    vector<pair<int,int>> cells;
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                cellId[i][j] = (int)cells.size();
                cells.emplace_back(i, j);
            }
        }
    }

    int K = (int)cells.size();
    if (K == 0) return 0;

    int NStates = K * 4;
    posR.assign(NStates, 0);
    posC.assign(NStates, 0);
    stateObs.assign(NStates, 0);
    nextL.assign(NStates, -1);
    nextR.assign(NStates, -1);
    nextStep.assign(NStates, -1);

    int dr[4] = {-1, 0, 1, 0};
    int dc[4] = {0, 1, 0, -1};

    for (int idx = 0; idx < K; ++idx) {
        int r0 = cells[idx].first;
        int c0 = cells[idx].second;
        for (int d = 0; d < 4; ++d) {
            int s = idx * 4 + d;
            posR[s] = r0;
            posC[s] = c0;

            nextL[s] = idx * 4 + ((d + 3) & 3);
            nextR[s] = idx * 4 + ((d + 1) & 3);

            int cnt = 0;
            int nr = r0 + dr[d], nc = c0 + dc[d];
            while (nr >= 0 && nr < R && nc >= 0 && nc < C && grid[nr][nc] == '.') {
                ++cnt;
                nr += dr[d];
                nc += dc[d];
            }
            stateObs[s] = cnt;
            if (cnt > MaxObs) MaxObs = cnt;

            nr = r0 + dr[d];
            nc = c0 + dc[d];
            if (nr >= 0 && nr < R && nc >= 0 && nc < C && grid[nr][nc] == '.') {
                int idx2 = cellId[nr][nc];
                nextStep[s] = idx2 * 4 + d;
            } else {
                nextStep[s] = -1;
            }
        }
    }

    vector<int> cand;
    cand.reserve(NStates);
    for (int s = 0; s < NStates; ++s) cand.push_back(s);

    const int ROUND_LIMIT = 5000;
    int rounds = 0;

    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;
        ++rounds;

        vector<int> newCand;
        newCand.reserve(cand.size());
        for (int id : cand) {
            if (stateObs[id] == d) newCand.push_back(id);
        }
        cand.swap(newCand);

        if (cand.empty()) {
            cout << "no" << endl;
            return 0;
        }

        // Check if all candidates share the same position
        bool samePos = true;
        int r0 = posR[cand[0]];
        int c0 = posC[cand[0]];
        for (size_t k = 1; k < cand.size(); ++k) {
            int s = cand[k];
            if (posR[s] != r0 || posC[s] != c0) {
                samePos = false;
                break;
            }
        }
        if (samePos) {
            cout << "yes " << (r0 + 1) << " " << (c0 + 1) << endl;
            return 0;
        }

        if (rounds >= ROUND_LIMIT) {
            cout << "no" << endl;
            return 0;
        }

        string action = choose_action(cand);
        cout << action << endl;

        vector<int> nextCand;
        nextCand.reserve(cand.size());
        if (action == "left") {
            for (int id : cand) nextCand.push_back(nextL[id]);
        } else if (action == "right") {
            for (int id : cand) nextCand.push_back(nextR[id]);
        } else { // "step"
            for (int id : cand) nextCand.push_back(nextStep[id]);
        }
        cand.swap(nextCand);
    }

    return 0;
}