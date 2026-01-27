#include <bits/stdc++.h>
using namespace std;

struct ClauseOcc {
    int c;
    unsigned char posCount, negCount;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<array<int,3>> litVar(m);
    vector<array<char,3>> litSign(m); // 1 for positive, 0 for negative
    vector<int> posAppear(n,0), negAppear(n,0);
    for (int i = 0; i < m; ++i) {
        int a,b,c;
        cin >> a >> b >> c;
        int arr[3] = {a,b,c};
        for (int j = 0; j < 3; ++j) {
            int v = abs(arr[j]) - 1;
            char s = (arr[j] > 0) ? 1 : 0;
            litVar[i][j] = v;
            litSign[i][j] = s;
            if (s) posAppear[v]++; else negAppear[v]++;
        }
    }
    
    // Build var -> clauses with counts of positive/negative occurrences in each clause
    vector<vector<ClauseOcc>> occ2(n);
    for (int c = 0; c < m; ++c) {
        // accumulate counts per variable within this clause
        int vars[3] = {litVar[c][0], litVar[c][1], litVar[c][2]};
        char signs[3] = {litSign[c][0], litSign[c][1], litSign[c][2]};
        // Since clause size is 3, use small temp list
        int tmpVar[3];
        unsigned char tmpPos[3], tmpNeg[3];
        int sz = 0;
        for (int j = 0; j < 3; ++j) {
            int v = vars[j];
            int k = -1;
            for (int t = 0; t < sz; ++t) {
                if (tmpVar[t] == v) { k = t; break; }
            }
            if (k == -1) {
                k = sz++;
                tmpVar[k] = v;
                tmpPos[k] = 0;
                tmpNeg[k] = 0;
            }
            if (signs[j]) tmpPos[k]++; else tmpNeg[k]++;
        }
        for (int t = 0; t < sz; ++t) {
            occ2[tmpVar[t]].push_back(ClauseOcc{c, tmpPos[t], tmpNeg[t]});
        }
    }
    
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto rand01 = [&](double p)->bool {
        uniform_real_distribution<double> dist(0.0,1.0);
        return dist(rng) < p;
    };
    auto randint = [&](int l, int r)->int {
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };
    
    vector<char> bestVal(n, 0);
    vector<char> curVal(n, 0);
    vector<int> satCount(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsat;
    int bestS = -1;
    
    auto compute_init = [&](bool use_majority){
        // Initialize assignment
        for (int i = 0; i < n; ++i) {
            if (use_majority) {
                if (posAppear[i] == 0 && negAppear[i] == 0) {
                    curVal[i] = (char)randint(0,1);
                } else {
                    curVal[i] = (posAppear[i] >= negAppear[i]) ? 1 : 0;
                }
            } else {
                curVal[i] = (char)randint(0,1);
            }
        }
        // Compute satCount and unsat
        unsat.clear();
        for (int i = 0; i < m; ++i) posInUnsat[i] = -1;
        int S = 0;
        for (int c = 0; c < m; ++c) {
            int sc = 0;
            for (int j = 0; j < 3; ++j) {
                int v = litVar[c][j];
                char s = litSign[c][j];
                if (curVal[v] == s) sc++;
            }
            satCount[c] = sc;
            if (sc == 0) {
                posInUnsat[c] = (int)unsat.size();
                unsat.push_back(c);
            } else {
                S++;
            }
        }
        return S;
    };
    
    auto flip_var = [&](int x, int &S) {
        char oldVal = curVal[x];
        char newVal = oldVal ^ 1;
        curVal[x] = newVal;
        for (const auto &occ : occ2[x]) {
            int c = occ.c;
            int before = satCount[c];
            int oldx = oldVal ? occ.posCount : occ.negCount;
            int newx = oldVal ? occ.negCount : occ.posCount;
            int after = before - oldx + newx;
            if (before == 0 && after > 0) {
                // remove from unsat
                int pos = posInUnsat[c];
                if (pos != -1) {
                    int last = unsat.back();
                    unsat[pos] = last;
                    posInUnsat[last] = pos;
                    unsat.pop_back();
                    posInUnsat[c] = -1;
                }
                S++;
            } else if (before > 0 && after == 0) {
                // add to unsat
                posInUnsat[c] = (int)unsat.size();
                unsat.push_back(c);
                S--;
            }
            satCount[c] = after;
        }
    };
    
    auto eval_break_make = [&](int x, int &brk, int &make) {
        brk = 0; make = 0;
        char valx = curVal[x];
        for (const auto &occ : occ2[x]) {
            int c = occ.c;
            int cur = satCount[c];
            int oldx = valx ? occ.posCount : occ.negCount;
            int newx = valx ? occ.negCount : occ.posCount;
            int newSat = cur - oldx + newx;
            if (cur > 0 && newSat == 0) brk++;
            if (cur == 0 && newSat > 0) make++;
        }
    };
    
    // Time budget
    const double TIME_LIMIT_SEC = 0.95;
    auto start_time = chrono::steady_clock::now();
    auto time_elapsed = [&](){
        chrono::duration<double> diff = chrono::steady_clock::now() - start_time;
        return diff.count();
    };
    
    // If no clauses, output any assignment (all zeros)
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }
    
    bool first = true;
    int currentS = 0;
    const double noiseP = 0.5;
    int stepsSinceBest = 0;
    int lastBestStep = 0;
    int globalStep = 0;
    int restartCount = 0;
    int stagnationLimit = max(2000, 10 * m);
    
    while (time_elapsed() < TIME_LIMIT_SEC) {
        // Restart
        bool use_majority = first;
        first = false;
        currentS = compute_init(use_majority);
        stepsSinceBest = 0;
        lastBestStep = globalStep;
        restartCount++;
        
        if (currentS > bestS) {
            bestS = currentS;
            bestVal = curVal;
            if (bestS == m) break;
        }
        
        while (time_elapsed() < TIME_LIMIT_SEC) {
            if (unsat.empty()) {
                // Found satisfying assignment
                if (currentS > bestS) {
                    bestS = currentS;
                    bestVal = curVal;
                }
                break;
            }
            int c = unsat[rng() % unsat.size()];
            // Candidate variables in this clause
            int candVar[3] = {litVar[c][0], litVar[c][1], litVar[c][2]};
            
            // Evaluate break/make for each candidate
            int brk[3], make[3];
            int zeroBreakIdx[3]; int zbCount = 0;
            for (int i = 0; i < 3; ++i) {
                eval_break_make(candVar[i], brk[i], make[i]);
                if (brk[i] == 0) zeroBreakIdx[zbCount++] = i;
            }
            
            int chooseIdx = -1;
            if (zbCount > 0) {
                chooseIdx = zeroBreakIdx[rng() % zbCount];
            } else {
                if (rand01(noiseP)) {
                    chooseIdx = randint(0,2);
                } else {
                    // choose minimal break, tie by maximal make, tie random
                    int bestIdx = 0;
                    int bestBr = brk[0];
                    int bestMk = make[0];
                    int ties[3]; int tieCnt = 1;
                    ties[0] = 0;
                    for (int i = 1; i < 3; ++i) {
                        if (brk[i] < bestBr || (brk[i] == bestBr && make[i] > bestMk)) {
                            bestBr = brk[i];
                            bestMk = make[i];
                            tieCnt = 0;
                            ties[tieCnt++] = i;
                        } else if (brk[i] == bestBr && make[i] == bestMk) {
                            ties[tieCnt++] = i;
                        }
                    }
                    chooseIdx = ties[rng() % tieCnt];
                }
            }
            
            int x = candVar[chooseIdx];
            flip_var(x, currentS);
            globalStep++;
            
            if (currentS > bestS) {
                bestS = currentS;
                bestVal = curVal;
                lastBestStep = globalStep;
                if (bestS == m) break;
            }
            if (globalStep - lastBestStep > stagnationLimit) {
                break; // restart
            }
        }
        if (bestS == m || time_elapsed() >= TIME_LIMIT_SEC) break;
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}