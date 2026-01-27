#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000;
unsigned char Cmat[MAXN][MAXN];

int n;

inline int edgeColor(int u, int v) {
    return Cmat[u][v];
}

// Check if permutation p is almost monochromatic (cost <= 1)
int computeCost(const vector<int> &p, vector<int> &col) {
    col.resize(n);
    for (int i = 0; i < n; ++i) {
        int u = p[i];
        int v = p[(i + 1) % n];
        col[i] = edgeColor(u, v);
    }
    int cost = 0;
    for (int i = 0; i < n - 1; ++i) {
        if (col[i] != col[i + 1]) ++cost;
    }
    return cost;
}

// Local search using pairwise swaps to reduce cost
bool localSearch(vector<int> &p) {
    if (n <= 2) return true;
    static vector<int> col;
    int cost = computeCost(p, col);
    if (cost <= 1) return true;

    const int maxSteps = 3;
    for (int step = 0; step < maxSteps && cost > 1; ++step) {
        bool improved = false;

        for (int i = 0; i < n && !improved; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int idx[4];
                int newCol[4];
                int cn = 0;

                auto addEdgeIdx = [&](int x) {
                    x = (x + n) % n;
                    for (int t = 0; t < cn; ++t)
                        if (idx[t] == x) return;
                    idx[cn++] = x;
                };

                addEdgeIdx(i - 1);
                addEdgeIdx(i);
                addEdgeIdx(j - 1);
                addEdgeIdx(j);

                auto getAfter = [&](int pos) -> int {
                    if (pos == i) return p[j];
                    if (pos == j) return p[i];
                    return p[pos];
                };

                for (int t = 0; t < cn; ++t) {
                    int k = idx[t];
                    int a = getAfter(k);
                    int b = getAfter((k + 1) % n);
                    newCol[t] = edgeColor(a, b);
                }

                int compIdx[8];
                int cp = 0;
                auto addComp = [&](int x) {
                    if (x < 0 || x >= n - 1) return;
                    for (int t = 0; t < cp; ++t)
                        if (compIdx[t] == x) return;
                    compIdx[cp++] = x;
                };
                for (int t = 0; t < cn; ++t) {
                    addComp(idx[t] - 1);
                    addComp(idx[t]);
                }

                auto colorAfter = [&](int k) -> int {
                    for (int t = 0; t < cn; ++t)
                        if (idx[t] == k) return newCol[t];
                    return col[k];
                };

                int delta = 0;
                for (int u = 0; u < cp; ++u) {
                    int t = compIdx[u];
                    int old1 = col[t];
                    int old2 = col[t + 1];
                    int new1 = colorAfter(t);
                    int new2 = colorAfter(t + 1);
                    int oldVal = (old1 != old2);
                    int newVal = (new1 != new2);
                    delta += (newVal - oldVal);
                }

                if (delta < 0) {
                    // Apply swap
                    swap(p[i], p[j]);
                    for (int t = 0; t < cn; ++t) {
                        col[idx[t]] = newCol[t];
                    }
                    cost += delta;
                    improved = true;
                    if (cost <= 1) return true;
                    break;
                }
            }
        }

        if (!improved) break;
    }

    return (cost <= 1);
}

// Exact backtracking for small n (<=10)
bool dfsSmall(int pos, vector<int> &perm, vector<int> &used,
              int changeCnt, int lastColor, vector<int> &ans) {
    if (changeCnt > 1) return false;
    if (pos == n) {
        if (n == 1) {
            ans = perm;
            return true;
        }
        int lastEdge = edgeColor(perm[n - 1], perm[0]);
        int finalChange = changeCnt + (lastColor != -1 && lastColor != lastEdge);
        if (finalChange <= 1) {
            ans = perm;
            return true;
        }
        return false;
    }

    for (int v = 0; v < n; ++v) {
        if (used[v]) continue;
        perm[pos] = v;
        used[v] = 1;
        int nc = changeCnt;
        int nl = lastColor;
        if (pos >= 1) {
            int e = edgeColor(perm[pos - 1], v);
            if (lastColor != -1 && lastColor != e) ++nc;
            nl = e;
        }
        if (dfsSmall(pos + 1, perm, used, nc, nl, ans)) return true;
        used[v] = 0;
    }
    return false;
}

bool solveSmall(vector<int> &ans) {
    vector<int> perm(n), used(n, 0);
    return dfsSmall(0, perm, used, 0, -1, ans);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    while (true) {
        if (!(cin >> n)) break;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                char ch;
                do {
                    if (!(cin >> ch)) return 0;
                } while (ch != '0' && ch != '1');
                Cmat[i][j] = (ch - '0');
            }
        }

        vector<int> answer;
        bool found = false;

        if (n <= 10) {
            if (solveSmall(answer)) {
                found = true;
            }
        } else {
            // Heuristic for larger n
            mt19937 rng(712367);
            vector<int> base(n);
            iota(base.begin(), base.end(), 0);

            vector<vector<int>> starts;
            starts.push_back(base);
            vector<int> rev = base;
            reverse(rev.begin(), rev.end());
            starts.push_back(rev);

            int extraRand = min(8, max(0, n / 5));
            for (int t = 0; t < extraRand; ++t) {
                vector<int> rnd = base;
                shuffle(rnd.begin(), rnd.end(), rng);
                starts.push_back(rnd);
            }

            for (auto p : starts) {
                if (localSearch(p)) {
                    answer = p;
                    found = true;
                    break;
                }
            }
        }

        if (!found) {
            cout << -1 << "\n";
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << (answer[i] + 1);
            }
            cout << "\n";
        }
    }

    return 0;
}