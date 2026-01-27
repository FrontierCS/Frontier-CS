#include <bits/stdc++.h>
using namespace std;

struct ClauseDeltaInfo {
    int c;
    int otherVar;
    int db_v;
    int db_u2;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) {
        return 0;
    }
    vector<int> ca(m), cb(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        ca[i] = a;
        cb[i] = b;
    }
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }
    vector<vector<int>> occ(n + 1);
    occ.reserve(n+1);
    for (int i = 0; i < m; ++i) {
        int va = abs(ca[i]);
        int vb = abs(cb[i]);
        if (va >= 1 && va <= n) occ[va].push_back(i);
        if (vb >= 1 && vb <= n) occ[vb].push_back(i);
    }
    auto now = [](){ return chrono::steady_clock::now(); };
    auto startTime = now();
    const double timeLimitSeconds = 0.9;
    auto timeLimit = chrono::duration<double>(timeLimitSeconds);
    
    std::mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> distVar(1, n);
    uniform_real_distribution<double> dist01(0.0, 1.0);
    
    vector<char> bestAssign(n+1, 0);
    int bestS = -1;
    
    auto litVal = [&](int lit, const vector<char>& val) -> bool {
        int v = abs(lit);
        bool x = val[v];
        return lit > 0 ? x : !x;
    };
    auto clauseDelta = [&](int c, int u, const vector<char>& val, bool satc) -> int {
        int a = ca[c], b = cb[c];
        bool va = litVal(a, val);
        bool vb = litVal(b, val);
        bool newSat;
        if (abs(a) == u) {
            bool vaNew = !va;
            newSat = vaNew || vb;
        } else {
            bool vbNew = !vb;
            newSat = va || vbNew;
        }
        return (int)newSat - (int)satc;
    };
    
    int restarts = 0;
    while (chrono::duration<double>(now() - startTime) < timeLimit) {
        // Random initial assignment
        vector<char> val(n+1);
        for (int i = 1; i <= n; ++i) val[i] = (rng() & 1);
        vector<char> sat(m);
        vector<int> unsatList;
        unsatList.reserve(m);
        vector<int> posInUnsat(m, -1);
        int S = 0;
        for (int i = 0; i < m; ++i) {
            bool s = litVal(ca[i], val) || litVal(cb[i], val);
            sat[i] = s;
            if (s) S++;
            else {
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }
        }
        vector<int> gain(n+1, 0);
        for (int v = 1; v <= n; ++v) {
            long long g = 0;
            for (int c : occ[v]) {
                g += clauseDelta(c, v, val, sat[c]);
            }
            gain[v] = (int)g;
        }
        if (S > bestS) {
            bestS = S;
            bestAssign = val;
            if (bestS == m) break;
        }
        int iterations = 0;
        int noImprove = 0;
        const int maxIterations = 500000;
        while (iterations < maxIterations && chrono::duration<double>(now() - startTime) < timeLimit) {
            iterations++;
            int chooseVar = -1;
            if (!unsatList.empty() && dist01(rng) < 0.5) {
                int c = unsatList[rng() % unsatList.size()];
                int v1 = abs(ca[c]), v2 = abs(cb[c]);
                int g1 = gain[v1], g2 = gain[v2];
                if (g1 > g2) chooseVar = v1;
                else if (g2 > g1) chooseVar = v2;
                else chooseVar = (rng() & 1) ? v1 : v2;
            } else {
                // pick best gain variable
                int bestV = 1, bestG = gain[1];
                for (int v = 2; v <= n; ++v) {
                    if (gain[v] > bestG) {
                        bestG = gain[v];
                        bestV = v;
                    }
                }
                if (bestG <= 0) {
                    chooseVar = distVar(rng);
                } else chooseVar = bestV;
            }
            int v = chooseVar;
            // Prepare before-flip deltas for affected clauses
            vector<ClauseDeltaInfo> tmp;
            tmp.reserve(occ[v].size());
            for (int c : occ[v]) {
                int other = (abs(ca[c]) == v) ? abs(cb[c]) : abs(ca[c]);
                int db_v = clauseDelta(c, v, val, sat[c]);
                int db_u2 = clauseDelta(c, other, val, sat[c]);
                tmp.push_back({c, other, db_v, db_u2});
            }
            // Flip v
            val[v] ^= 1;
            // Update clause satisfaction, S, unsat list
            for (auto &info : tmp) {
                int c = info.c;
                bool oldSat = sat[c];
                bool newSat = (litVal(ca[c], val) || litVal(cb[c], val));
                if (oldSat != newSat) {
                    sat[c] = newSat;
                    if (newSat) {
                        // remove from unsat
                        int pos = posInUnsat[c];
                        if (pos != -1) {
                            int lastIdx = (int)unsatList.size() - 1;
                            int lastClause = unsatList[lastIdx];
                            unsatList[pos] = lastClause;
                            posInUnsat[lastClause] = pos;
                            unsatList.pop_back();
                            posInUnsat[c] = -1;
                        }
                        S++;
                    } else {
                        // add to unsat
                        posInUnsat[c] = (int)unsatList.size();
                        unsatList.push_back(c);
                        S--;
                    }
                }
            }
            // Update gains
            for (auto &info : tmp) {
                int c = info.c;
                int other = info.otherVar;
                int db_v = info.db_v;
                int db_u2 = info.db_u2;
                int da_v = clauseDelta(c, v, val, sat[c]);
                int da_u2 = clauseDelta(c, other, val, sat[c]);
                gain[v] += (da_v - db_v);
                gain[other] += (da_u2 - db_u2);
            }
            // Track best
            if (S > bestS) {
                bestS = S;
                bestAssign = val;
                noImprove = 0;
                if (bestS == m) break;
            } else {
                noImprove++;
            }
            // Occasionally random perturbation if stuck
            if (noImprove > 2000) {
                // flip a few random variables to escape
                int kicks = min(10, n);
                for (int k = 0; k < kicks; ++k) {
                    int rv = distVar(rng);
                    // prepare and perform flip similarly but without too much overhead
                    vector<ClauseDeltaInfo> tmp2;
                    tmp2.reserve(occ[rv].size());
                    for (int c : occ[rv]) {
                        int other = (abs(ca[c]) == rv) ? abs(cb[c]) : abs(ca[c]);
                        int db_v = clauseDelta(c, rv, val, sat[c]);
                        int db_u2 = clauseDelta(c, other, val, sat[c]);
                        tmp2.push_back({c, other, db_v, db_u2});
                    }
                    val[rv] ^= 1;
                    for (auto &info : tmp2) {
                        int c = info.c;
                        bool oldSat = sat[c];
                        bool newSat = (litVal(ca[c], val) || litVal(cb[c], val));
                        if (oldSat != newSat) {
                            sat[c] = newSat;
                            if (newSat) {
                                int pos = posInUnsat[c];
                                if (pos != -1) {
                                    int lastIdx = (int)unsatList.size() - 1;
                                    int lastClause = unsatList[lastIdx];
                                    unsatList[pos] = lastClause;
                                    posInUnsat[lastClause] = pos;
                                    unsatList.pop_back();
                                    posInUnsat[c] = -1;
                                }
                                S++;
                            } else {
                                posInUnsat[c] = (int)unsatList.size();
                                unsatList.push_back(c);
                                S--;
                            }
                        }
                    }
                    for (auto &info : tmp2) {
                        int c = info.c;
                        int other = info.otherVar;
                        int db_v = info.db_v;
                        int db_u2 = info.db_u2;
                        int da_v = clauseDelta(c, rv, val, sat[c]);
                        int da_u2 = clauseDelta(c, other, val, sat[c]);
                        gain[rv] += (da_v - db_v);
                        gain[other] += (da_u2 - db_u2);
                    }
                }
                if (S > bestS) {
                    bestS = S;
                    bestAssign = val;
                    if (bestS == m) break;
                }
                noImprove = 0;
            }
        }
        restarts++;
        // If perfect, break
        if (bestS == m) break;
        // If time left, continue restart
    }
    
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(bestAssign[i]);
    }
    cout << '\n';
    return 0;
}