#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];
    unsigned char sgn[3]; // 1 for positive, 0 for negative
    unsigned char cntTrue;
};

int n, m;
vector<Clause> clauses;
vector<vector<int>> varClausesUnique; // per variable, list of clause indices (unique per clause)
vector<unsigned char> val, bestVal;
vector<int> brkCnt, makeCnt;
vector<int> unsat, posInUnsat;

mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

inline bool litTrue(const Clause& c, int j) {
    return val[c.v[j]] == c.sgn[j];
}

inline int getUniqueVars(const Clause &c, int out[3]) {
    int len = 0;
    for (int j = 0; j < 3; ++j) {
        int v = c.v[j];
        bool seen = false;
        for (int i = 0; i < len; ++i) if (out[i] == v) { seen = true; break; }
        if (!seen) out[len++] = v;
    }
    return len;
}

inline void addUnsat(int k) {
    if (posInUnsat[k] == -1) {
        posInUnsat[k] = (int)unsat.size();
        unsat.push_back(k);
    }
}
inline void removeUnsat(int k) {
    int pos = posInUnsat[k];
    if (pos != -1) {
        int last = (int)unsat.size() - 1;
        int ck = unsat[last];
        unsat[pos] = ck;
        posInUnsat[ck] = pos;
        unsat.pop_back();
        posInUnsat[k] = -1;
    }
}

void initAssignment() {
    val.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) val[i] = (unsigned char)(rng() & 1);

    brkCnt.assign(n + 1, 0);
    makeCnt.assign(n + 1, 0);
    posInUnsat.assign(m, -1);
    unsat.clear();

    for (int k = 0; k < m; ++k) {
        Clause &c = clauses[k];
        int t = 0;
        for (int j = 0; j < 3; ++j) t += litTrue(c, j);
        c.cntTrue = (unsigned char)t;
    }

    for (int k = 0; k < m; ++k) {
        Clause &c = clauses[k];
        int t = c.cntTrue;
        if (t == 0) {
            addUnsat(k);
            int uniq[3]; int len = getUniqueVars(c, uniq);
            for (int i = 0; i < len; ++i) makeCnt[uniq[i]]++;
        } else if (t == 1) {
            int idxTrue = -1;
            for (int j = 0; j < 3; ++j) if (litTrue(c, j)) { idxTrue = j; break; }
            if (idxTrue != -1) brkCnt[c.v[idxTrue]]++;
        }
    }
}

void flipVar(int x) {
    // For each clause containing x (unique per clause)
    for (int ki : varClausesUnique[x]) {
        Clause &c = clauses[ki];
        int oldT = c.cntTrue;

        bool oldTruth[3];
        for (int j = 0; j < 3; ++j) oldTruth[j] = litTrue(c, j);

        int idxTrueOld = -1;
        if (oldT == 1) {
            for (int j = 0; j < 3; ++j) if (oldTruth[j]) { idxTrueOld = j; break; }
        }

        int h = 0, p = 0; // occurrences of x true/false
        for (int j = 0; j < 3; ++j) if (c.v[j] == x) {
            if (oldTruth[j]) ++h; else ++p;
        }

        int newT = oldT - h + p;

        if (oldT == 0 && newT != 0) removeUnsat(ki);
        else if (oldT != 0 && newT == 0) addUnsat(ki);

        if (oldT == 0) {
            int uniq[3]; int len = getUniqueVars(c, uniq);
            for (int i = 0; i < len; ++i) makeCnt[uniq[i]]--;
        } else if (oldT == 1) {
            if (idxTrueOld != -1) brkCnt[c.v[idxTrueOld]]--;
        }

        if (newT == 0) {
            int uniq[3]; int len = getUniqueVars(c, uniq);
            for (int i = 0; i < len; ++i) makeCnt[uniq[i]]++;
        } else if (newT == 1) {
            int idxTrueNew = -1;
            for (int j = 0; j < 3; ++j) {
                bool now = oldTruth[j];
                if (c.v[j] == x) now = !now;
                if (now) { idxTrueNew = j; break; }
            }
            if (idxTrueNew != -1) brkCnt[c.v[idxTrueNew]]++;
        }

        c.cntTrue = (unsigned char)newT;
    }
    val[x] ^= 1;
}

int chooseVarFromClause(int k, int noisePct) {
    Clause &c = clauses[k];
    int uniq[3]; int len = getUniqueVars(c, uniq);
    if (len <= 0) return uniq[0]; // should not happen

    if ((int)(rng() % 100) < noisePct) {
        int idx = (int)(rng() % len);
        return uniq[idx];
    } else {
        int minB = INT_MAX;
        vector<int> candIdx;
        candIdx.reserve(3);
        for (int i = 0; i < len; ++i) {
            int v = uniq[i];
            int b = brkCnt[v];
            if (b < minB) {
                minB = b;
                candIdx.clear();
                candIdx.push_back(i);
            } else if (b == minB) {
                candIdx.push_back(i);
            }
        }
        int bestI = candIdx[0];
        int bestMake = makeCnt[uniq[bestI]];
        for (int idx : candIdx) {
            int mk = makeCnt[uniq[idx]];
            if (mk > bestMake) {
                bestMake = mk;
                bestI = idx;
            } else if (mk == bestMake) {
                // break tie randomly
                if (rng() & 1) bestI = idx;
            }
        }
        return uniq[bestI];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m)) {
        return 0;
    }
    clauses.resize(m);
    varClausesUnique.assign(n + 1, {});
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        Clause cl;
        for (int j = 0; j < 3; ++j) {
            int x = abs(lits[j]);
            cl.v[j] = x;
            cl.sgn[j] = (unsigned char)(lits[j] > 0 ? 1 : 0);
        }
        cl.cntTrue = 0;
        clauses[i] = cl;

        // push unique variables for this clause into varClausesUnique
        for (int j = 0; j < 3; ++j) {
            int v = cl.v[j];
            bool dup = false;
            for (int k = 0; k < j; ++k) if (cl.v[k] == v) { dup = true; break; }
            if (!dup) varClausesUnique[v].push_back(i);
        }
    }

    val.assign(n + 1, 0);
    bestVal.assign(n + 1, 0);
    brkCnt.assign(n + 1, 0);
    makeCnt.assign(n + 1, 0);
    posInUnsat.assign(m, -1);

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    auto start = chrono::steady_clock::now();
    const int timeLimitMs = 950; // time budget
    int bestUnsat = m + 1;

    const int NOISE_PCT = 50; // 50% noise for WalkSAT
    while (true) {
        auto now = chrono::steady_clock::now();
        if ((int)chrono::duration_cast<chrono::milliseconds>(now - start).count() >= timeLimitMs) break;

        initAssignment();
        int curUnsat = (int)unsat.size();
        if (curUnsat < bestUnsat) {
            bestUnsat = curUnsat;
            bestVal = val;
            if (bestUnsat == 0) break;
        }

        int stepsSinceImprove = 0;
        int stagnationLimit = max(1000, m * 2);

        while (true) {
            now = chrono::steady_clock::now();
            if ((int)chrono::duration_cast<chrono::milliseconds>(now - start).count() >= timeLimitMs) break;
            if (unsat.empty()) {
                bestUnsat = 0;
                bestVal = val;
                break;
            }

            int idx = (int)(rng() % unsat.size());
            int clauseIdx = unsat[idx];
            int varToFlip = chooseVarFromClause(clauseIdx, NOISE_PCT);
            flipVar(varToFlip);

            int newUnsat = (int)unsat.size();
            if (newUnsat < bestUnsat) {
                bestUnsat = newUnsat;
                bestVal = val;
                stepsSinceImprove = 0;
                if (bestUnsat == 0) break;
            } else {
                stepsSinceImprove++;
                if (stepsSinceImprove >= stagnationLimit) break;
            }
        }
        if (bestUnsat == 0) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}