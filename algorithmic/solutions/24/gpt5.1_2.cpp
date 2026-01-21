#include <bits/stdc++.h>
using namespace std;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

inline int randInt(int l, int r) {
    return l + (int)(rng() % (uint64_t)(r - l + 1));
}

bool lexLess(const vector<int> &a, const vector<int> &b) {
    int n = (int)a.size();
    for (int i = 0; i < n; ++i) {
        if (a[i] != b[i]) return a[i] < b[i];
    }
    return false;
}

int computeChanges(const vector<int> &p, const vector<string> &C, vector<char> &e) {
    int n = (int)p.size();
    if (n <= 2) return 0;
    e.assign(n - 1, 0);
    for (int i = 0; i < n - 1; ++i) {
        e[i] = C[p[i] - 1][p[i + 1] - 1];
    }
    int E = 0;
    for (int i = 0; i < n - 2; ++i) {
        if (e[i] != e[i + 1]) ++E;
    }
    return E;
}

int calcNewEForSwap(const vector<int> &p, const vector<char> &e, int E,
                    int a, int b, const vector<string> &C) {
    int n = (int)p.size();
    if (n <= 2) return 0;

    int changedEdges[4] = {a - 1, a, b - 1, b};
    int pairPos[8];
    int pairCnt = 0;

    auto addPair = [&](int pos) {
        if (pos < 0 || pos > n - 3) return;
        for (int i = 0; i < pairCnt; ++i)
            if (pairPos[i] == pos) return;
        pairPos[pairCnt++] = pos;
    };

    for (int idx = 0; idx < 4; ++idx) {
        int s = changedEdges[idx];
        if (0 <= s && s <= n - 2) {
            addPair(s - 1);
            addPair(s);
        }
    }

    int oldSum = 0, newSum = 0;

    auto getVert = [&](int pos) -> int {
        if (pos == a) return p[b];
        if (pos == b) return p[a];
        return p[pos];
    };

    for (int i = 0; i < pairCnt; ++i) {
        int k = pairPos[i];
        char old_e_k = e[k];
        char old_e_k1 = e[k + 1];
        if (old_e_k != old_e_k1) ++oldSum;

        int v1 = getVert(k);
        int v2 = getVert(k + 1);
        int v3 = getVert(k + 2);

        char new_e_k = C[v1 - 1][v2 - 1];
        char new_e_k1 = C[v2 - 1][v3 - 1];

        if (new_e_k != new_e_k1) ++newSum;
    }

    return E - oldSum + newSum;
}

void applySwapAndUpdate(vector<int> &p, vector<char> &e,
                        int a, int b, const vector<string> &C) {
    int n = (int)p.size();
    if (n <= 2) {
        swap(p[a], p[b]);
        return;
    }
    swap(p[a], p[b]);
    int changedEdges[4] = {a - 1, a, b - 1, b};
    for (int idx = 0; idx < 4; ++idx) {
        int s = changedEdges[idx];
        if (0 <= s && s <= n - 2) {
            int v1 = p[s];
            int v2 = p[s + 1];
            e[s] = C[v1 - 1][v2 - 1];
        }
    }
}

void refineLexicographically(vector<int> &p, const vector<string> &C) {
    int n = (int)p.size();
    if (n <= 2) return;
    vector<char> e;
    int E = computeChanges(p, C, e); // E should be <=1

    for (int i = 1; i < n; ++i) {
        int j = i;
        while (j > 0 && p[j - 1] > p[j]) {
            int a = j - 1, b = j;
            int newE = calcNewEForSwap(p, e, E, a, b, C);
            if (newE <= 1) {
                applySwapAndUpdate(p, e, a, b, C);
                E = newE;
                --j;
            } else {
                break;
            }
        }
    }
}

bool bruteForceSolve(int n, const vector<string> &C, vector<int> &ans) {
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    vector<char> e;
    bool found = false;
    do {
        int E = computeChanges(p, C, e);
        if (E <= 1) {
            if (!found || lexLess(p, ans)) {
                ans = p;
                found = true;
            }
        }
    } while (next_permutation(p.begin(), p.end()));
    return found;
}

void solveHeuristic(int n, const vector<string> &C, vector<int> &ans, bool &hasAns) {
    vector<vector<int>> initPerms;
    vector<int> base(n);
    iota(base.begin(), base.end(), 1);
    initPerms.push_back(base);

    vector<int> rev = base;
    reverse(rev.begin(), rev.end());
    initPerms.push_back(rev);

    // by degree of '1's ascending and descending
    vector<pair<int,int>> deg(n);
    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int j = 0; j < n; ++j)
            if (C[i][j] == '1') ++d;
        deg[i] = {d, i + 1};
    }
    sort(deg.begin(), deg.end());
    vector<int> byDegAsc(n), byDegDesc(n);
    for (int i = 0; i < n; ++i) byDegAsc[i] = deg[i].second;
    for (int i = 0; i < n; ++i) byDegDesc[i] = deg[n - 1 - i].second;
    initPerms.push_back(byDegAsc);
    initPerms.push_back(byDegDesc);

    // by row lexicographically ascending and descending
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b) {
        if (C[a] == C[b]) return a < b;
        return C[a] < C[b];
    });
    vector<int> byRowAsc(n), byRowDesc(n);
    for (int i = 0; i < n; ++i) byRowAsc[i] = idx[i] + 1;
    for (int i = 0; i < n; ++i) byRowDesc[i] = idx[n - 1 - i] + 1;
    initPerms.push_back(byRowAsc);
    initPerms.push_back(byRowDesc);

    // remove duplicate initial permutations
    vector<vector<int>> uniqPerms;
    for (auto &p : initPerms) {
        bool dup = false;
        for (auto &q : uniqPerms) {
            if (p == q) { dup = true; break; }
        }
        if (!dup) uniqPerms.push_back(p);
    }

    vector<char> e;
    bool solFound = false;
    vector<int> bestSol;
    bool haveBestInit = false;
    int bestE = n;
    vector<int> bestPermE;

    for (auto &p : uniqPerms) {
        int E = computeChanges(p, C, e);
        if (E <= 1) {
            if (!solFound || lexLess(p, bestSol)) {
                solFound = true;
                bestSol = p;
            }
        }
        if (!haveBestInit || E < bestE || (E == bestE && lexLess(p, bestPermE))) {
            haveBestInit = true;
            bestE = E;
            bestPermE = p;
        }
    }

    if (solFound) {
        refineLexicographically(bestSol, C);
        if (!hasAns || lexLess(bestSol, ans)) {
            ans = bestSol;
            hasAns = true;
        }
        return;
    }

    // Random local search
    long long maxIter = min(5000000LL, 3000LL * (long long)n);
    int numRestarts = (int)min<long long>(10, maxIter / 1000LL);
    if (numRestarts <= 0) numRestarts = 1;
    long long iterPerAttempt = maxIter / numRestarts;
    if (iterPerAttempt <= 0) iterPerAttempt = 1;

    vector<int> bestRandSol;
    bool randFound = false;

    for (int attempt = 0; attempt < numRestarts; ++attempt) {
        vector<int> p(n);
        if (attempt == 0 && haveBestInit) {
            p = bestPermE;
        } else {
            p = base;
            shuffle(p.begin(), p.end(), rng);
        }
        vector<char> eCur;
        int E = computeChanges(p, C, eCur);

        for (long long it = 0; it < iterPerAttempt; ++it) {
            if (E <= 1) {
                randFound = true;
                bestRandSol = p;
                goto RAND_DONE;
            }
            int a = randInt(0, n - 1);
            int b = randInt(0, n - 1);
            if (a == b) continue;
            if (a > b) swap(a, b);

            int newE = calcNewEForSwap(p, eCur, E, a, b, C);
            if (newE <= E || ((rng() & 1023ULL) == 0ULL)) { // occasionally accept worse
                applySwapAndUpdate(p, eCur, a, b, C);
                E = newE;
            }
        }
    }
RAND_DONE:;

    if (randFound) {
        refineLexicographically(bestRandSol, C);
        if (!hasAns || lexLess(bestRandSol, ans)) {
            ans = bestRandSol;
            hasAns = true;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<string> C(n, string(n, '0'));
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                char ch;
                cin >> ch;
                C[i][j] = ch;
            }
        }

        vector<int> ans;
        bool hasAns = false;

        const int EXACT_N_MAX = 10;
        if (n <= EXACT_N_MAX) {
            if (bruteForceSolve(n, C, ans)) {
                hasAns = true;
            }
        }

        if (!hasAns) {
            solveHeuristic(n, C, ans, hasAns);
        }

        if (!hasAns) {
            cout << -1 << '\n';
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << ans[i];
            }
            cout << '\n';
        }
    }
    return 0;
}