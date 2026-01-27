#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[2];      // variable indices (0-based)
    bool sgn[2];   // true if positive literal
    unsigned char t[2];   // current literal truth values (0/1)
    unsigned char sat;    // clause satisfaction (0/1)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<int>> occ(n); // clause indices per variable (unique per clause)
    vector<int> posCnt(n, 0), negCnt(n, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int va = abs(a) - 1;
        int vb = abs(b) - 1;
        bool sa = (a > 0);
        bool sb = (b > 0);
        clauses[i].v[0] = va; clauses[i].sgn[0] = sa;
        clauses[i].v[1] = vb; clauses[i].sgn[1] = sb;
        if (sa) posCnt[va]++; else negCnt[va]++;
        if (sb) posCnt[vb]++; else negCnt[vb]++;
        occ[va].push_back(i);
        if (vb != va) occ[vb].push_back(i);
    }

    // Remove duplicate clause indices in occ (in case of repeated variable entries from malformed input)
    for (int i = 0; i < n; ++i) {
        auto &vec = occ[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    // Random generator
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto rand01 = [&]() -> double {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng);
    };
    auto randInt = [&](int L, int R) -> int {
        return std::uniform_int_distribution<int>(L, R)(rng);
    };

    // Structures for local search
    vector<unsigned char> x(n, 0), best_x(n, 0);
    vector<int> make(n, 0), brk(n, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    auto lit_val = [&](unsigned char xv, bool sgn)->unsigned char {
        return sgn ? xv : (unsigned char)(1 - xv);
    };

    int best_satisfied = -1;

    // Time limit (approx)
    auto t_start = chrono::steady_clock::now();
    auto time_elapsed = [&]() {
        return chrono::duration<double>(chrono::steady_clock::now() - t_start).count();
    };
    double TIME_LIM = 1.8; // seconds, conservative default

    auto initialize = [&](bool useMajority) -> int {
        // assignment
        for (int i = 0; i < n; ++i) {
            if (useMajority) {
                if (posCnt[i] > negCnt[i]) x[i] = 1;
                else if (posCnt[i] < negCnt[i]) x[i] = 0;
                else x[i] = randInt(0, 1);
            } else {
                x[i] = randInt(0, 1);
            }
        }
        // reset counts
        fill(make.begin(), make.end(), 0);
        fill(brk.begin(), brk.end(), 0);
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        int satisfied = 0;
        for (int i = 0; i < m; ++i) {
            Clause &c = clauses[i];
            c.t[0] = lit_val(x[c.v[0]], c.sgn[0]);
            c.t[1] = lit_val(x[c.v[1]], c.sgn[1]);
            c.sat = (unsigned char)(c.t[0] | c.t[1]);
            if (c.sat) satisfied++;
            else {
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }

            if (c.v[0] == c.v[1]) {
                int v = c.v[0];
                if (c.sgn[0] == c.sgn[1]) {
                    if (c.sat) brk[v] += 1;
                    else make[v] += 1;
                } else {
                    // tautology, no contribution
                }
            } else {
                if (!c.sat) {
                    make[c.v[0]] += 1;
                    make[c.v[1]] += 1;
                } else {
                    if (c.t[0] && !c.t[1]) brk[c.v[0]] += 1;
                    else if (c.t[1] && !c.t[0]) brk[c.v[1]] += 1;
                }
            }
        }
        return satisfied;
    };

    auto removeUnsat = [&](int cid) {
        int pos = posInUnsat[cid];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        posInUnsat[last] = pos;
        unsatList.pop_back();
        posInUnsat[cid] = -1;
    };

    auto addUnsat = [&](int cid) {
        if (posInUnsat[cid] != -1) return;
        posInUnsat[cid] = (int)unsatList.size();
        unsatList.push_back(cid);
    };

    auto flipVar = [&](int u, int &satisfied) {
        x[u] ^= 1; // flip assignment
        const auto &clist = occ[u];
        for (int idxc = 0; idxc < (int)clist.size(); ++idxc) {
            int cid = clist[idxc];
            Clause &c = clauses[cid];

            bool sameVar = (c.v[0] == c.v[1]);
            unsigned char s_old = c.sat;

            int before_m_u = 0, before_b_u = 0;
            int before_m_w = 0, before_b_w = 0;

            if (sameVar) {
                if (c.v[0] == u) {
                    if (c.sgn[0] == c.sgn[1]) {
                        if (s_old) before_b_u = 1;
                        else before_m_u = 1;
                    }
                }
            } else {
                int idxu = (c.v[0] == u ? 0 : 1);
                int idxw = 1 - idxu;
                int w = c.v[idxw];

                if (!s_old) {
                    before_m_u = 1;
                    before_m_w = 1;
                } else {
                    if (c.t[idxu] && !c.t[idxw]) before_b_u = 1;
                    if (c.t[idxw] && !c.t[idxu]) before_b_w = 1;
                }
            }

            // Toggle literal truths where var u appears
            if (c.v[0] == u) c.t[0] ^= 1;
            if (c.v[1] == u) c.t[1] ^= 1;

            unsigned char s_new = (unsigned char)(c.t[0] | c.t[1]);
            c.sat = s_new;

            int after_m_u = 0, after_b_u = 0;
            int after_m_w = 0, after_b_w = 0;

            if (sameVar) {
                if (c.v[0] == u) {
                    if (c.sgn[0] == c.sgn[1]) {
                        if (s_new) after_b_u = 1;
                        else after_m_u = 1;
                    }
                }
            } else {
                int idxu = (c.v[0] == u ? 0 : 1);
                int idxw = 1 - idxu;
                int w = c.v[idxw];

                if (!s_new) {
                    after_m_u = 1;
                    after_m_w = 1;
                } else {
                    if (c.t[idxu] && !c.t[idxw]) after_b_u = 1;
                    if (c.t[idxw] && !c.t[idxu]) after_b_w = 1;
                }
            }

            // Apply deltas
            make[u] += after_m_u - before_m_u;
            brk[u]  += after_b_u - before_b_u;

            if (!sameVar) {
                int w = (c.v[0] == u ? c.v[1] : c.v[0]);
                make[w] += after_m_w - before_m_w;
                brk[w]  += after_b_w - before_b_w;
            }

            if (s_old != s_new) {
                if (s_new) {
                    satisfied++;
                    removeUnsat(cid);
                } else {
                    satisfied--;
                    addUnsat(cid);
                }
            }
        }
    };

    // Main search loop with restarts
    bool firstInit = true;
    while (time_elapsed() < TIME_LIM) {
        int satisfied = initialize(firstInit);
        firstInit = false;

        if (satisfied > best_satisfied) {
            best_satisfied = satisfied;
            best_x = x;
            if (best_satisfied == m) break;
        }

        int stepsSinceImprovement = 0;
        int localBest = satisfied;

        while (time_elapsed() < TIME_LIM) {
            if (satisfied == m) { // optimal
                best_x = x;
                best_satisfied = m;
                break;
            }

            // Choose variable to flip
            int bestVar = -1;
            int bestGain = INT_MIN;
            for (int i = 0; i < n; ++i) {
                int gain = make[i] - brk[i];
                if (gain > bestGain) {
                    bestGain = gain;
                    bestVar = i;
                }
            }

            int chosenVar;
            if (bestGain > 0) {
                chosenVar = bestVar;
            } else {
                if (!unsatList.empty()) {
                    int cid = unsatList[randInt(0, (int)unsatList.size()-1)];
                    Clause &c = clauses[cid];
                    int va = c.v[0], vb = c.v[1];
                    // If both same variable, flipping it might or might not help.
                    if (va == vb) {
                        chosenVar = va;
                    } else {
                        double p = 0.5;
                        if (rand01() < p) {
                            chosenVar = (randInt(0,1) == 0) ? va : vb;
                        } else {
                            int ba = brk[va];
                            int bb = brk[vb];
                            if (ba < bb) chosenVar = va;
                            else if (bb < ba) chosenVar = vb;
                            else chosenVar = (randInt(0,1) == 0) ? va : vb;
                        }
                    }
                } else {
                    chosenVar = randInt(0, n-1);
                }
            }

            flipVar(chosenVar, satisfied);

            if (satisfied > localBest) {
                localBest = satisfied;
                stepsSinceImprovement = 0;
                if (satisfied > best_satisfied) {
                    best_satisfied = satisfied;
                    best_x = x;
                }
            } else {
                stepsSinceImprovement++;
            }

            if (stepsSinceImprovement > 5000) break; // restart
            if (best_satisfied == m) break;
        }

        if (best_satisfied == m) break;
    }

    // Output best found assignment (fallback to current if none)
    if (best_satisfied < 0) best_x = x;
    for (int i = 0; i < n; ++i) {
        cout << (int)best_x[i] << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}