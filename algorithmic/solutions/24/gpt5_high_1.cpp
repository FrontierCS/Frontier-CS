#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<vector<unsigned char>> C(n + 1, vector<unsigned char>(n + 1, 0));
        for (int i = 1; i <= n; ++i) {
            int got = 0;
            while (got < n) {
                string tok;
                cin >> tok;
                for (char ch : tok) {
                    if (ch == '0' || ch == '1') {
                        ++got;
                        if (got <= n) C[i][got] = (unsigned char)(ch - '0');
                    }
                }
            }
        }

        auto dir = [&](int u, int v) -> bool {
            if (u == v) return false;
            if (u < v) return C[u][v] == 1;
            else return C[v][u] == 0;
        };

        auto build_path = [&](const vector<int>& order) -> vector<int> {
            vector<int> ord;
            ord.reserve(n);
            for (int v : order) {
                ord.push_back(v);
                int pos = (int)ord.size() - 1;
                while (pos > 0 && !dir(ord[pos - 1], ord[pos])) {
                    swap(ord[pos - 1], ord[pos]);
                    --pos;
                }
            }
            return ord;
        };

        auto rotation = [&](const vector<int>& a, int s) -> vector<int> {
            vector<int> r;
            r.reserve(n);
            for (int i = 0; i < n; ++i) r.push_back(a[(s + i) % n]);
            return r;
        };

        auto lexLess = [&](const vector<int>& A, const vector<int>& B) -> bool {
            for (int i = 0; i < n; ++i) {
                if (A[i] != B[i]) return A[i] < B[i];
            }
            return false;
        };

        auto minRotationIndex = [&](const vector<int>& a) -> int {
            int i = 0, j = 1, k = 0;
            while (i < n && j < n && k < n) {
                int ai = a[(i + k) % n];
                int aj = a[(j + k) % n];
                if (ai == aj) {
                    ++k;
                } else if (ai < aj) {
                    j = j + k + 1;
                    k = 0;
                    if (j == i) ++j;
                } else {
                    i = i + k + 1;
                    k = 0;
                    if (i == j) ++i;
                }
            }
            int s = min(i, j);
            if (s >= n) s %= n;
            return s;
        };

        auto candidates_from_path = [&](const vector<int>& ord) -> vector<vector<int>> {
            vector<vector<int>> cands;
            if ((int)ord.size() != n) return cands;
            vector<int> e(n);
            for (int i = 0; i < n; ++i) {
                int a = ord[i], b = ord[(i + 1) % n];
                e[i] = (int)C[a][b];
            }
            int r = 0;
            for (int i = 0; i < n; ++i) {
                if (e[i] != e[(i + 1) % n]) ++r;
            }
            if (r == 0) {
                int s = minRotationIndex(ord);
                cands.push_back(rotation(ord, s));
            } else if (r == 2) {
                int first = -1, second = -1;
                for (int i = 0; i < n; ++i) {
                    if (e[i] != e[(i + 1) % n]) {
                        if (first == -1) first = i;
                        else { second = i; break; }
                    }
                }
                // Two valid rotations start after each boundary
                vector<int> A = rotation(ord, (first + 1) % n);
                vector<int> B = rotation(ord, (second + 1) % n);
                if (lexLess(B, A)) cands.push_back(B);
                else cands.push_back(A);
            }
            // else r > 2: no candidate from this path
            return cands;
        };

        vector<int> asc(n), desc(n);
        iota(asc.begin(), asc.end(), 1);
        iota(desc.begin(), desc.end(), 1);
        reverse(desc.begin(), desc.end());

        vector<int> ordAsc = build_path(asc);
        vector<int> ordDesc = build_path(desc);

        vector<vector<int>> allCands;
        {
            auto cc = candidates_from_path(ordAsc);
            allCands.insert(allCands.end(), cc.begin(), cc.end());
        }
        {
            auto cc = candidates_from_path(ordDesc);
            allCands.insert(allCands.end(), cc.begin(), cc.end());
        }

        if (allCands.empty()) {
            cout << -1 << "\n";
            continue;
        }

        vector<int> best = allCands[0];
        for (auto &cand : allCands) {
            if (lexLess(cand, best)) best = cand;
        }

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << best[i];
        }
        cout << "\n";
    }
    return 0;
}