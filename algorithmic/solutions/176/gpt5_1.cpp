#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

struct Clause {
    int v[3];
    bool sign[3]; // true for positive literal, false for negated
};

struct Occ {
    int clause;
    bool sign; // sign of literal in that clause
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<Clause> clauses(max(0, m));
    vector<vector<Occ>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int var = abs(lit);
            bool sgn = lit > 0;
            clauses[i].v[j] = var;
            clauses[i].sign[j] = sgn;
            occ[var].push_back({i, sgn});
            if (sgn) posCnt[var]++; else negCnt[var]++;
        }
    }

    for (int v = 1; v <= n; ++v) {
        auto &vec = occ[v];
        sort(vec.begin(), vec.end(), [](const Occ &a, const Occ &b) {
            if (a.clause != b.clause) return a.clause < b.clause;
            return a.sign < b.sign;
        });
    }

    vector<char> assign(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        assign[v] = (posCnt[v] >= negCnt[v]) ? 1 : 0;
    }

    vector<int> clauseTrueCount(max(0, m), 0);
    vector<int> posInUnsat(max(0, m), -1);
    vector<int> unsat;
    unsat.reserve(m);

    for (int i = 0; i < m; ++i) {
        int cnt = 0;
        for (int j = 0; j < 3; ++j) {
            int var = clauses[i].v[j];
            bool sgn = clauses[i].sign[j];
            bool litSat = sgn ? (assign[var] != 0) : (assign[var] == 0);
            if (litSat) cnt++;
        }
        clauseTrueCount[i] = cnt;
        if (cnt == 0) {
            posInUnsat[i] = (int)unsat.size();
            unsat.push_back(i);
        }
    }

    vector<char> bestAssign = assign;
    int bestUnsat = (int)unsat.size();

    if (m > 0 && bestUnsat > 0) {
        mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
        auto randu = [&]() -> uint32_t { return rng(); };
        auto randDouble = [&]() -> double { return std::uniform_real_distribution<double>(0.0, 1.0)(rng); };

        auto deltaVar = [&](int v)->int {
            int delta = 0;
            const auto &list = occ[v];
            bool val = assign[v];
            int idx = 0, sz = (int)list.size();
            while (idx < sz) {
                int cid = list[idx].clause;
                int kpos = 0, kneg = 0;
                do {
                    if (list[idx].sign) kpos++; else kneg++;
                    idx++;
                } while (idx < sz && list[idx].clause == cid);
                int tc = clauseTrueCount[cid];
                int ks = val ? kpos : kneg;
                int ku = val ? kneg : kpos;
                int newtc = tc + (ku - ks);
                if (tc > 0 && newtc == 0) delta -= 1;
                else if (tc == 0 && newtc > 0) delta += 1;
            }
            return delta;
        };

        auto flipVar = [&](int v) {
            bool old = assign[v];
            assign[v] ^= 1;
            const auto &list = occ[v];
            int idx = 0, sz = (int)list.size();
            while (idx < sz) {
                int cid = list[idx].clause;
                int kpos = 0, kneg = 0;
                do {
                    if (list[idx].sign) kpos++; else kneg++;
                    idx++;
                } while (idx < sz && list[idx].clause == cid);
                int dcount = old ? (kneg - kpos) : (kpos - kneg);
                if (dcount == 0) continue;
                int tc = clauseTrueCount[cid];
                int newtc = tc + dcount;
                if (tc == 0 && newtc > 0) {
                    int pos = posInUnsat[cid];
                    if (pos >= 0) {
                        int lastIdx = (int)unsat.size() - 1;
                        int lastClause = unsat[lastIdx];
                        unsat[pos] = lastClause;
                        posInUnsat[lastClause] = pos;
                        unsat.pop_back();
                        posInUnsat[cid] = -1;
                    }
                } else if (tc > 0 && newtc == 0) {
                    posInUnsat[cid] = (int)unsat.size();
                    unsat.push_back(cid);
                }
                clauseTrueCount[cid] = newtc;
            }
        };

        const double walkP = 0.5;
        const long long timeLimitMs = 900; // conservative
        auto tStart = chrono::steady_clock::now();

        size_t steps = 0;
        const size_t checkInterval = 16384;

        while (!unsat.empty()) {
            if ((steps & (checkInterval - 1)) == 0) {
                auto now = chrono::steady_clock::now();
                if (chrono::duration_cast<chrono::milliseconds>(now - tStart).count() > timeLimitMs) break;
            }
            steps++;
            int cidx = unsat[randu() % unsat.size()];
            int chooseVar = -1;

            if (randDouble() < walkP) {
                int j = randu() % 3;
                chooseVar = clauses[cidx].v[j];
            } else {
                int bestDelta = INT_MIN;
                int candidateVars[3];
                int candCount = 0;

                for (int j = 0; j < 3; ++j) {
                    int v = clauses[cidx].v[j];
                    int d = deltaVar(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        candidateVars[0] = v;
                        candCount = 1;
                    } else if (d == bestDelta) {
                        // avoid duplicates if same var appears multiple times
                        bool exists = false;
                        for (int k = 0; k < candCount; ++k) if (candidateVars[k] == v) { exists = true; break; }
                        if (!exists && candCount < 3) candidateVars[candCount++] = v;
                    }
                }
                if (candCount == 0) {
                    int j = randu() % 3;
                    chooseVar = clauses[cidx].v[j];
                } else {
                    chooseVar = candidateVars[randu() % candCount];
                }
            }

            if (chooseVar <= 0 || chooseVar > n) continue;
            flipVar(chooseVar);

            if ((int)unsat.size() < bestUnsat) {
                bestUnsat = (int)unsat.size();
                bestAssign = assign;
                if (bestUnsat == 0) break;
            }
        }
    }

    // Output best assignment
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}