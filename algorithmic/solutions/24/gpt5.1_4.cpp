#include <bits/stdc++.h>
using namespace std;

using ll = long long;

mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

bool betterLex(const vector<int> &a, const vector<int> &b) {
    if (b.empty()) return true;
    int n = a.size();
    for (int i = 0; i < n; ++i) {
        if (a[i] != b[i]) return a[i] < b[i];
    }
    return false;
}

// Booth's algorithm for lexicographically minimal rotation
int least_rotation(const vector<int> &s) {
    int n = (int)s.size();
    vector<int> ss(2 * n);
    for (int i = 0; i < 2 * n; ++i) ss[i] = s[i % n];
    int i = 0, j = 1, k = 0;
    while (i < n && j < n && k < n) {
        int a = ss[i + k];
        int b = ss[j + k];
        if (a == b) {
            ++k;
        } else if (a < b) {
            j = j + k + 1;
            if (j == i) ++j;
            k = 0;
        } else {
            i = i + k + 1;
            if (i == j) ++i;
            k = 0;
        }
    }
    return min(i, j);
}

// compute cyclic transitions (edges considered with c[n-1] vs c[0] too)
int computeCyclicTransitions(const vector<int> &p, const vector<vector<char>> &C,
                             vector<char> &ce, vector<char> &dt) {
    int n = (int)p.size();
    ce.assign(n, 0);
    for (int i = 0; i < n; ++i) {
        int j = (i + 1) % n;
        ce[i] = C[p[i]][p[j]];
    }
    dt.assign(n, 0);
    int T = 0;
    for (int i = 0; i < n; ++i) {
        int j = (i + 1) % n;
        dt[i] = (ce[i] != ce[j]);
        if (dt[i]) ++T;
    }
    return T;
}

// From a cycle p with Tcyc <= 2, get lexicographically minimal permutation (rotation and direction)
vector<int> bestFromCycle(const vector<int> &p) {
    int n = (int)p.size();
    vector<int> best;
    // normal orientation
    {
        int start = least_rotation(p);
        vector<int> q(n);
        for (int i = 0; i < n; ++i) q[i] = p[(start + i) % n];
        if (betterLex(q, best)) best = q;
    }
    // reversed orientation
    {
        vector<int> r(n);
        for (int i = 0; i < n; ++i) r[i] = p[n - 1 - i];
        int start = least_rotation(r);
        vector<int> q(n);
        for (int i = 0; i < n; ++i) q[i] = r[(start + i) % n];
        if (betterLex(q, best)) best = q;
    }
    return best;
}

// exact brute force for small n <= 9
vector<int> solveSmall(int n, const vector<vector<char>> &C) {
    vector<int> perm(n);
    iota(perm.begin(), perm.end(), 0);
    vector<int> best;
    do {
        // compute cyclic transitions
        vector<char> ce(n), dt(n);
        int T = computeCyclicTransitions(perm, C, ce, dt);
        if (T <= 2) {
            vector<int> cand = bestFromCycle(perm);
            if (betterLex(cand, best)) best = cand;
        }
    } while (next_permutation(perm.begin(), perm.end()));
    // convert to 1-based
    if (!best.empty()) {
        for (int &x : best) ++x;
    }
    return best;
}

// heuristic local search for large n
vector<int> solveLarge(int n, const vector<vector<char>> &C) {
    vector<vector<int>> initials;

    // natural order
    {
        vector<int> p(n);
        iota(p.begin(), p.end(), 0);
        initials.push_back(p);
    }
    // reverse order
    {
        vector<int> p(n);
        iota(p.begin(), p.end(), 0);
        reverse(p.begin(), p.end());
        initials.push_back(p);
    }
    // sort by #0-edges
    {
        vector<pair<int,int>> deg0(n);
        for (int i = 0; i < n; ++i) {
            int d0 = 0;
            for (int j = 0; j < n; ++j) if (C[i][j] == 0) ++d0;
            deg0[i] = {d0, i};
        }
        sort(deg0.begin(), deg0.end());
        vector<int> p(n);
        for (int i = 0; i < n; ++i) p[i] = deg0[i].second;
        initials.push_back(p);
    }
    // sort by #1-edges
    {
        vector<pair<int,int>> deg1(n);
        for (int i = 0; i < n; ++i) {
            int d1 = 0;
            for (int j = 0; j < n; ++j) if (C[i][j] == 1) ++d1;
            deg1[i] = {d1, i};
        }
        sort(deg1.begin(), deg1.end());
        vector<int> p(n);
        for (int i = 0; i < n; ++i) p[i] = deg1[i].second;
        initials.push_back(p);
    }
    // a few random permutations
    int randPerms = 4;
    for (int r = 0; r < randPerms; ++r) {
        vector<int> p(n);
        iota(p.begin(), p.end(), 0);
        shuffle(p.begin(), p.end(), rng);
        initials.push_back(p);
    }

    vector<int> globalBest;

    for (auto p : initials) {
        vector<char> ce, dt;
        int T = computeCyclicTransitions(p, C, ce, dt);
        int maxIter = 8000;
        if (n > 500) maxIter = 20000;
        if (n > 1000) maxIter = 30000;

        for (int iter = 0; iter < maxIter && T > 2; ++iter) {
            int i = (int)(rng() % n);
            int j = (int)(rng() % n);
            if (i == j) continue;
            if (i > j) swap(i, j);

            vector<int> edgeIdx;
            auto addEdge = [&](int idx) {
                idx %= n;
                if (idx < 0) idx += n;
                edgeIdx.push_back(idx);
            };
            addEdge(i - 1);
            addEdge(i);
            addEdge(j - 1);
            addEdge(j);

            sort(edgeIdx.begin(), edgeIdx.end());
            edgeIdx.erase(unique(edgeIdx.begin(), edgeIdx.end()), edgeIdx.end());

            vector<int> transIdx;
            auto addTrans = [&](int idx) {
                idx %= n;
                if (idx < 0) idx += n;
                transIdx.push_back(idx);
            };
            for (int e : edgeIdx) {
                addTrans(e);
                addTrans(e - 1);
            }
            sort(transIdx.begin(), transIdx.end());
            transIdx.erase(unique(transIdx.begin(), transIdx.end()), transIdx.end());

            // store old values
            vector<char> oldCe(edgeIdx.size());
            vector<char> oldDt(transIdx.size());
            for (int k = 0; k < (int)edgeIdx.size(); ++k) oldCe[k] = ce[edgeIdx[k]];
            for (int k = 0; k < (int)transIdx.size(); ++k) oldDt[k] = dt[transIdx[k]];
            int oldT = T;

            // perform swap
            swap(p[i], p[j]);

            // recompute affected edges
            for (int k = 0; k < (int)edgeIdx.size(); ++k) {
                int e = edgeIdx[k];
                int u = p[e];
                int v = p[(e + 1) % n];
                ce[e] = C[u][v];
            }
            // recompute affected transitions
            for (int k = 0; k < (int)transIdx.size(); ++k) {
                int idx = transIdx[k];
                int j2 = (idx + 1) % n;
                dt[idx] = (ce[idx] != ce[j2]);
            }
            // recompute T from dt locally
            int newT = oldT;
            for (int k = 0; k < (int)transIdx.size(); ++k) {
                int idx = transIdx[k];
                newT += (int)dt[idx] - (int)oldDt[k];
            }

            if (newT <= oldT) {
                T = newT;
            } else {
                // revert
                swap(p[i], p[j]);
                for (int k = 0; k < (int)edgeIdx.size(); ++k) {
                    ce[edgeIdx[k]] = oldCe[k];
                }
                for (int k = 0; k < (int)transIdx.size(); ++k) {
                    dt[transIdx[k]] = oldDt[k];
                }
            }
        }

        if (T <= 2) {
            vector<int> cand = bestFromCycle(p);
            if (betterLex(cand, globalBest)) globalBest = cand;
        }
    }

    if (!globalBest.empty()) {
        for (int &x : globalBest) ++x; // to 1-based
    }
    return globalBest;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<vector<char>> C(n, vector<char>(n));
        for (int i = 0; i < n; ++i) {
            string s;
            cin >> s;
            if ((int)s.size() == n) {
                for (int j = 0; j < n; ++j) C[i][j] = s[j] - '0';
            } else {
                // space separated
                C[i][0] = s[0] - '0';
                for (int j = 1; j < n; ++j) {
                    string t;
                    cin >> t;
                    C[i][j] = t[0] - '0';
                }
            }
        }

        vector<int> ans;
        if (n <= 9) {
            ans = solveSmall(n, C);
        } else {
            ans = solveLarge(n, C);
        }

        if (ans.empty()) {
            cout << -1 << "\n";
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << ans[i];
            }
            cout << "\n";
        }
    }
    return 0;
}