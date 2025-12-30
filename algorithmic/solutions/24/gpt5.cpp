#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while (cin >> n) {
        vector<vector<unsigned char>> C(n + 1, vector<unsigned char>(n + 1, 0));
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                char ch;
                cin >> ch; // reads next non-whitespace character
                C[i][j] = static_cast<unsigned char>(ch - '0');
            }
        }

        auto build_paths = [&](bool startOnes, bool preferOnes) -> pair<vector<int>, vector<int>> {
            vector<int> ones, zeros;
            if (startOnes) ones.push_back(1);
            else zeros.push_back(1);
            for (int v = 2; v <= n; ++v) {
                bool canOne = ones.empty() || C[ones.back()][v] == 1;
                bool canZero = zeros.empty() || C[zeros.back()][v] == 0;
                if (canOne && canZero) {
                    if (preferOnes) ones.push_back(v);
                    else zeros.push_back(v);
                } else if (canOne) {
                    ones.push_back(v);
                } else if (canZero) {
                    zeros.push_back(v);
                } else {
                    // both paths non-empty and neither can append directly: perform restructure
                    int x = ones.back();
                    int y = zeros.back();
                    if (C[x][y] == 1) {
                        ones.push_back(y);
                        zeros.pop_back();
                        ones.push_back(v);
                    } else {
                        zeros.push_back(x);
                        ones.pop_back();
                        zeros.push_back(v);
                    }
                }
            }
            return {ones, zeros};
        };

        auto join_paths = [&](const vector<int>& A, bool revA, const vector<int>& B, bool revB) -> vector<int> {
            vector<int> res;
            res.reserve(n);
            if (!revA) res.insert(res.end(), A.begin(), A.end());
            else res.insert(res.end(), A.rbegin(), A.rend());
            if (!revB) res.insert(res.end(), B.begin(), B.end());
            else res.insert(res.end(), B.rbegin(), B.rend());
            return res;
        };

        auto lex_less = [&](const vector<int>& a, const vector<int>& b) -> bool {
            for (int i = 0; i < (int)a.size(); ++i) {
                if (a[i] != b[i]) return a[i] < b[i];
            }
            return false;
        };

        vector<int> best;
        bool hasBest = false;

        for (int start = 0; start < 2; ++start) {       // 0: startOnes, 1: startZeros
            for (int prefer = 0; prefer < 2; ++prefer) { // 0: preferOnes, 1: preferZeros
                auto pr = build_paths(start == 0, prefer == 0);
                const vector<int>& ones = pr.first;
                const vector<int>& zeros = pr.second;

                for (int swapPaths = 0; swapPaths < 2; ++swapPaths) {
                    const vector<int>& L = (swapPaths == 0 ? ones : zeros);
                    const vector<int>& R = (swapPaths == 0 ? zeros : ones);
                    for (int ra = 0; ra < 2; ++ra) {
                        for (int rb = 0; rb < 2; ++rb) {
                            vector<int> cand = join_paths(L, ra, R, rb);
                            if ((int)cand.size() != n) continue;
                            if (!hasBest || lex_less(cand, best)) {
                                best = move(cand);
                                hasBest = true;
                            }
                        }
                    }
                }
            }
        }

        if (!hasBest) {
            cout << -1 << '\n';
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << best[i];
            }
            if (!cin.eof()) cout << '\n';
        }
    }
    return 0;
}