#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int lit[3];
};

inline bool clauseValue(const Clause &cl, const vector<int> &assign) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl.lit[k];
        int v = abs(lit) - 1;
        int val = assign[v];
        bool varVal = (val != 0);
        bool litVal = (lit > 0) ? varVal : !varVal;
        if (litVal) return true;
    }
    return false;
}

inline bool clauseValueAfterFlip(const Clause &cl, const vector<int> &assign, int flipVar) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl.lit[k];
        int v = abs(lit) - 1;
        int val = (v == flipVar) ? (1 - assign[v]) : assign[v];
        bool varVal = (val != 0);
        bool litVal = (lit > 0) ? varVal : !varVal;
        if (litVal) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<Clause> clauses(m);
    vector<vector<int>> occ(n);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        clauses[i].lit[2] = c;

        int v0 = abs(a) - 1;
        int v1 = abs(b) - 1;
        int v2 = abs(c) - 1;

        occ[v0].push_back(i);
        if (v1 != v0) occ[v1].push_back(i);
        if (v2 != v0 && v2 != v1) occ[v2].push_back(i);
    }

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    const int noisePermille = 100; // 0.1 probability

    int totalSteps = max(10000, 4000 * n);
    int stepsPerRestart = min(1000, totalSteps);
    int restarts = max(1, totalSteps / stepsPerRestart);

    vector<int> bestAssign(n, 0);
    int bestSat = -1;

    for (int r = 0; r < restarts; ++r) {
        vector<int> assign(n);
        for (int i = 0; i < n; ++i) assign[i] = rng() & 1;

        vector<char> sat(m);
        vector<int> unsatList;
        unsatList.reserve(m);
        vector<int> posInUnsat(m, -1);

        int s = 0;
        for (int i = 0; i < m; ++i) {
            bool val = clauseValue(clauses[i], assign);
            if (val) {
                sat[i] = 1;
                ++s;
            } else {
                sat[i] = 0;
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }
        }

        if (s > bestSat) {
            bestSat = s;
            bestAssign = assign;
            if (s == m) goto search_done;
        }

        for (int step = 0; step < stepsPerRestart; ++step) {
            if (s == m) {
                bestSat = s;
                bestAssign = assign;
                goto search_done;
            }
            if (unsatList.empty()) break;

            int ci = unsatList[rng() % unsatList.size()];
            Clause &cl = clauses[ci];

            int cand[3] = {abs(cl.lit[0]) - 1, abs(cl.lit[1]) - 1, abs(cl.lit[2]) - 1};

            int uniq[3];
            int ucnt = 0;
            for (int t = 0; t < 3; ++t) {
                int v = cand[t];
                bool found = false;
                for (int j = 0; j < ucnt; ++j) {
                    if (uniq[j] == v) {
                        found = true;
                        break;
                    }
                }
                if (!found) uniq[ucnt++] = v;
            }

            int varToFlip;
            if ((int)(rng() % 1000) < noisePermille) {
                varToFlip = uniq[rng() % ucnt];
            } else {
                int bestVar = uniq[0];
                int bestDelta = -1000000000;

                for (int idx = 0; idx < ucnt; ++idx) {
                    int v = uniq[idx];
                    int delta = 0;
                    const auto &cv = occ[v];
                    for (int cindex : cv) {
                        bool oldSat = sat[cindex];
                        bool newSat = clauseValueAfterFlip(clauses[cindex], assign, v);
                        if (oldSat) {
                            if (!newSat) --delta;
                        } else {
                            if (newSat) ++delta;
                        }
                    }
                    if (delta > bestDelta || (delta == bestDelta && (rng() & 1))) {
                        bestDelta = delta;
                        bestVar = v;
                    }
                }
                varToFlip = bestVar;
            }

            assign[varToFlip] ^= 1;
            const auto &cv2 = occ[varToFlip];
            for (int cindex : cv2) {
                bool oldSat = sat[cindex];
                bool newSat = clauseValue(clauses[cindex], assign);
                if (oldSat == newSat) continue;
                sat[cindex] = newSat;
                if (newSat) {
                    ++s;
                    int pos = posInUnsat[cindex];
                    if (pos != -1) {
                        int last = unsatList.back();
                        unsatList[pos] = last;
                        posInUnsat[last] = pos;
                        unsatList.pop_back();
                        posInUnsat[cindex] = -1;
                    }
                } else {
                    --s;
                    if (posInUnsat[cindex] == -1) {
                        posInUnsat[cindex] = (int)unsatList.size();
                        unsatList.push_back(cindex);
                    }
                }
            }

            if (s > bestSat) {
                bestSat = s;
                bestAssign = assign;
                if (s == m) goto search_done;
            }
        }
    }

search_done:
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestAssign[i];
    }
    cout << '\n';
    return 0;
}