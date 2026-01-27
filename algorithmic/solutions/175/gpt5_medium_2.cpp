#include <bits/stdc++.h>
using namespace std;

struct FastInput {
    static const size_t BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastInput() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c; int sgn = 1; int x = 0;
        c = read();
        if (!c) return false;
        while (c && (c == ' ' || c == '\n' || c == '\r' || c == '\t')) c = read();
        if (!c) return false;
        if (c == '-') { sgn = -1; c = read(); }
        if (!c) return false;
        for (; c >= '0' && c <= '9'; c = read()) x = x * 10 + (c - '0');
        out = x * sgn;
        return true;
    }
} In;

static inline uint64_t rng64() {
    static uint64_t x = 88172645463393265ull ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    x ^= x << 7;
    x ^= x >> 9;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!In.readInt(n)) return 0;
    In.readInt(m);

    const int64_t M = m;
    const int64_t TOTLIT = 3LL * M;

    vector<int> lits;
    lits.reserve((size_t)TOTLIT);
    vector<int> deg(n + 1, 0);
    vector<int> posCount(n + 1, 0), negCount(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        In.readInt(a); In.readInt(b); In.readInt(c);
        lits.push_back(a);
        lits.push_back(b);
        lits.push_back(c);
        int va = abs(a), vb = abs(b), vc = abs(c);
        if (va >= 1 && va <= n) { deg[va]++; if (a > 0) posCount[va]++; else negCount[va]++; }
        if (vb >= 1 && vb <= n) { deg[vb]++; if (b > 0) posCount[vb]++; else negCount[vb]++; }
        if (vc >= 1 && vc <= n) { deg[vc]++; if (c > 0) posCount[vc]++; else negCount[vc]++; }
    }

    vector<uint8_t> assign(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCount[v] + negCount[v] == 0) {
            assign[v] = (rng64() & 1);
        } else {
            assign[v] = (posCount[v] >= negCount[v]) ? 1 : 0;
        }
    }

    vector<uint8_t> sc(m, 0);           // satisfied count per clause
    vector<int8_t> uni(m, -1);          // index of unique satisfied literal if sc==1 else -1
    vector<int> posUnsat(m, -1);        // position in unsat vector or -1
    vector<int> unsat; unsat.reserve(m);

    auto evalLit = [&](int lit, uint8_t val)->uint8_t {
        return (lit > 0) ? val : (uint8_t)(1 - val);
    };

    for (int c = 0; c < m; ++c) {
        int base = 3 * c;
        int l0 = lits[base], l1 = lits[base + 1], l2 = lits[base + 2];
        uint8_t t0 = evalLit(l0, assign[abs(l0)]);
        uint8_t t1 = evalLit(l1, assign[abs(l1)]);
        uint8_t t2 = evalLit(l2, assign[abs(l2)]);
        uint8_t s = t0 + t1 + t2;
        sc[c] = s;
        if (s == 0) {
            posUnsat[c] = (int)unsat.size();
            unsat.push_back(c);
            uni[c] = -1;
        } else if (s == 1) {
            if (t0) uni[c] = 0;
            else if (t1) uni[c] = 1;
            else uni[c] = 2;
        } else {
            uni[c] = -1;
        }
    }

    // Occurrence structure: for each variable, list of literal positions (3*c + k)
    vector<int> start(n + 2, 0);
    for (int v = 1; v <= n; ++v) start[v + 1] = start[v] + deg[v];
    vector<int> occ(TOTLIT);
    vector<int> cur = start;
    for (int c = 0; c < m; ++c) {
        int base = 3 * c;
        for (int k = 0; k < 3; ++k) {
            int lit = lits[base + k];
            int v = abs(lit);
            occ[cur[v]++] = base + k; // store literal position
        }
    }

    vector<int> brk(n + 1, 0);
    vector<int> make(n + 1, 0);
    for (int c = 0; c < m; ++c) {
        if (sc[c] == 1) {
            int idx = uni[c];
            int var = abs(lits[3 * c + idx]);
            brk[var]++;
        } else if (sc[c] == 0) {
            int base = 3 * c;
            make[abs(lits[base])]   ++;
            make[abs(lits[base+1])] ++;
            make[abs(lits[base+2])] ++;
        }
    }

    auto removeUnsat = [&](int cidx) {
        int p = posUnsat[cidx];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posUnsat[last] = p;
        unsat.pop_back();
        posUnsat[cidx] = -1;
    };
    auto addUnsat = [&](int cidx) {
        if (posUnsat[cidx] != -1) return;
        posUnsat[cidx] = (int)unsat.size();
        unsat.push_back(cidx);
    };

    auto updateClauseAfterFlip = [&](int clause, int litIdx, uint8_t oldValOfVar) {
        int base = 3 * clause;
        int litpos = base + litIdx;
        int lit = lits[litpos];
        uint8_t litTrueBefore = (lit > 0) ? oldValOfVar : (uint8_t)(1 - oldValOfVar);
        uint8_t old_s = sc[clause];

        if (old_s == 1) {
            int uidx = uni[clause];
            if (uidx >= 0) {
                int uvar = abs(lits[base + uidx]);
                brk[uvar]--;
            }
        }
        if (old_s == 0) {
            // remove make contributions and from unsat list
            int v0 = abs(lits[base]);
            int v1 = abs(lits[base + 1]);
            int v2 = abs(lits[base + 2]);
            make[v0]--; make[v1]--; make[v2]--;
            removeUnsat(clause);
        }

        uint8_t new_s = old_s + (litTrueBefore ? (uint8_t) -1 : (uint8_t) +1);
        sc[clause] = new_s;

        if (new_s == 0) {
            // add make contributions and to unsat list
            int v0 = abs(lits[base]);
            int v1 = abs(lits[base + 1]);
            int v2 = abs(lits[base + 2]);
            make[v0]++; make[v1]++; make[v2]++;
            addUnsat(clause);
            uni[clause] = -1;
        } else if (new_s == 1) {
            // compute unique true literal after flip
            uint8_t t0 = evalLit(lits[base], assign[abs(lits[base])]);
            uint8_t t1 = evalLit(lits[base + 1], assign[abs(lits[base + 1])]);
            // we can avoid computing t2 if t0 or t1 is 1
            int newUni = -1;
            if (t0) newUni = 0;
            else if (t1) newUni = 1;
            else newUni = 2;
            uni[clause] = (int8_t)newUni;
            int uvar = abs(lits[base + newUni]);
            brk[uvar]++;
        } else {
            uni[clause] = -1;
        }
    };

    auto flipVar = [&](int v) {
        uint8_t oldVal = assign[v];
        assign[v] ^= 1;
        int s = start[v], e = start[v + 1];
        for (int i = s; i < e; ++i) {
            int litpos = occ[i];
            int clause = litpos / 3;
            int litIdx = litpos % 3;
            updateClauseAfterFlip(clause, litIdx, oldVal);
        }
    };

    if (!unsat.empty()) {
        int64_t TOT = (int64_t)TOTLIT;
        int maxFlips = (int)min<int64_t>(30000, max<int64_t>(1000, TOT / 600));
        int noisePermil = 350; // 0.35

        for (int step = 0; step < maxFlips; ++step) {
            if (unsat.empty()) break;
            int c = unsat[(size_t)(rng64() % unsat.size())];
            int base = 3 * c;
            int v0 = abs(lits[base]);
            int v1 = abs(lits[base + 1]);
            int v2 = abs(lits[base + 2]);

            int b0 = brk[v0], b1 = brk[v1], b2 = brk[v2];

            int chosenVar;
            if (b0 == 0 || b1 == 0 || b2 == 0) {
                // choose random among zeros
                int candidates[3]; int cnt = 0;
                if (b0 == 0) candidates[cnt++] = v0;
                if (b1 == 0) candidates[cnt++] = v1;
                if (b2 == 0) candidates[cnt++] = v2;
                chosenVar = candidates[(size_t)(rng64() % cnt)];
            } else {
                uint64_t r = rng64() % 1000;
                if ((int)r < noisePermil) {
                    int arr[3] = {v0, v1, v2};
                    chosenVar = arr[(size_t)(rng64() % 3)];
                } else {
                    // choose minimal break, tie-break by max make
                    int vars[3] = {v0, v1, v2};
                    int brs[3] = {b0, b1, b2};
                    int best = 0;
                    for (int i = 1; i < 3; ++i) {
                        if (brs[i] < brs[best] || (brs[i] == brs[best] && make[vars[i]] > make[vars[best]])) {
                            best = i;
                        }
                    }
                    chosenVar = vars[best];
                }
            }
            flipVar(chosenVar);
        }
    }

    // Output assignment
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)assign[i];
    }
    cout << '\n';
    return 0;
}