#include <iostream>
#include <vector>
#include <utility>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cmath>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<pair<int,int>> clause(m);
    vector<vector<int>> adj(n + 1);

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clause[i] = {a, b};
        int va = std::abs(a), vb = std::abs(b);
        if (va == vb) {
            if (va >= 1 && va <= n) adj[va].push_back(i);
        } else {
            if (va >= 1 && va <= n) adj[va].push_back(i);
            if (vb >= 1 && vb <= n) adj[vb].push_back(i);
        }
    }

    vector<char> bestVal(n + 1, 0);
    int bestSat = -1;

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    using namespace std::chrono;
    const double timeLimit = 0.9; // seconds
    auto start = steady_clock::now();
    mt19937_64 rng((uint64_t) start.time_since_epoch().count());

    vector<char> val(n + 1);
    vector<char> clauseSat(m);
    vector<int> unsatClauses;
    unsatClauses.reserve(m);
    vector<int> unsatPos(m);

    auto evalClause = [&](int idx) -> bool {
        int a = clause[idx].first;
        int b = clause[idx].second;
        int va = std::abs(a), vb = std::abs(b);
        bool aval = (a > 0) ? (val[va] != 0) : (val[va] == 0);
        if (aval) return true;
        bool bval = (b > 0) ? (val[vb] != 0) : (val[vb] == 0);
        return bval;
    };

    while (true) {
        auto now = steady_clock::now();
        double elapsed = duration<double>(now - start).count();
        if (elapsed > timeLimit) break;

        // Random initial assignment
        for (int i = 1; i <= n; ++i) {
            val[i] = (char)(rng() & 1);
        }

        // Initialize clause satisfaction and unsatisfied list
        unsatClauses.clear();
        std::fill(unsatPos.begin(), unsatPos.end(), -1);

        int currSat = 0;
        for (int i = 0; i < m; ++i) {
            bool sat = evalClause(i);
            clauseSat[i] = sat;
            if (sat) {
                ++currSat;
            } else {
                unsatPos[i] = (int)unsatClauses.size();
                unsatClauses.push_back(i);
            }
        }

        if (currSat > bestSat) {
            bestSat = currSat;
            bestVal = val;
            if (bestSat == m) break;
        }

        int64_t maxSteps = (int64_t)2 * m + 1000;

        for (int64_t step = 0; step < maxSteps; ++step) {
            if (unsatClauses.empty()) {
                if (currSat > bestSat) {
                    bestSat = currSat;
                    bestVal = val;
                }
                break;
            }

            if ((step & 255) == 0) {
                now = steady_clock::now();
                elapsed = duration<double>(now - start).count();
                if (elapsed > timeLimit) goto END_SEARCH;
            }

            int ci = unsatClauses.size() > 1 ? (int)(rng() % unsatClauses.size()) : 0;
            int cidx = unsatClauses[ci];
            int a = clause[cidx].first;
            int b = clause[cidx].second;
            int va = std::abs(a);
            int vb = std::abs(b);

            int chooseVar;
            if (va == vb) {
                chooseVar = va;
            } else {
                auto computeGain = [&](int v) -> int {
                    int gain = 0;
                    if (adj[v].empty()) return 0;
                    val[v] ^= 1;
                    for (int idx : adj[v]) {
                        bool before = clauseSat[idx];
                        bool after = evalClause(idx);
                        if (!before && after) ++gain;
                        else if (before && !after) --gain;
                    }
                    val[v] ^= 1;
                    return gain;
                };

                int gainA = computeGain(va);
                int gainB = computeGain(vb);

                if (gainA > gainB) chooseVar = va;
                else if (gainB > gainA) chooseVar = vb;
                else chooseVar = (rng() & 1) ? va : vb;

                if (gainA <= 0 && gainB <= 0) {
                    if ((rng() % 10) < 3) {
                        chooseVar = (rng() & 1) ? va : vb;
                    }
                }
            }

            int v = chooseVar;
            if (v < 1 || v > n) continue;
            if (adj[v].empty()) continue;

            val[v] ^= 1;
            for (int idx : adj[v]) {
                bool before = clauseSat[idx];
                bool after = evalClause(idx);
                if (before == after) continue;
                clauseSat[idx] = after;
                if (after) {
                    ++currSat;
                    int pos = unsatPos[idx];
                    if (pos != -1) {
                        int lastIdx = unsatClauses.back();
                        unsatClauses[pos] = lastIdx;
                        unsatPos[lastIdx] = pos;
                        unsatClauses.pop_back();
                        unsatPos[idx] = -1;
                    }
                } else {
                    --currSat;
                    if (unsatPos[idx] == -1) {
                        unsatPos[idx] = (int)unsatClauses.size();
                        unsatClauses.push_back(idx);
                    }
                }
            }

            if (currSat > bestSat) {
                bestSat = currSat;
                bestVal = val;
                if (bestSat == m) goto END_SEARCH;
            }
        }
    }

END_SEARCH:
    for (int i = 1; i <= n; ++i) {
        cout << (bestVal[i] ? 1 : 0);
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}