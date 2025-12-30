#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<string> S(M);
    for (int i = 0; i < M; i++) {
        cin >> S[i];
    }
    vector<pair<int, int>> ord;
    for (int i = 0; i < M; i++) {
        ord.emplace_back(-(int)S[i].size(), i);
    }
    sort(ord.begin(), ord.end());
    vector<vector<char>> mat(N, vector<char>(N, '.'));
    for (auto& pr : ord) {
        int idx = pr.second;
        string s = S[idx];
        int k = s.size();
        int best_dir = -1;
        int best_fixed = -1;
        int best_start = -1;
        int best_sc = -1;
        // horizontal
        for (int r = 0; r < N; r++) {
            for (int st = 0; st < N; st++) {
                bool can = true;
                int sc = 0;
                for (int p = 0; p < k; p++) {
                    int c2 = (st + p) % N;
                    char req = s[p];
                    if (mat[r][c2] != '.' && mat[r][c2] != req) {
                        can = false;
                        break;
                    }
                    if (mat[r][c2] == req) sc++;
                }
                if (can && sc > best_sc) {
                    best_dir = 0;
                    best_fixed = r;
                    best_start = st;
                    best_sc = sc;
                }
            }
        }
        // vertical
        for (int c = 0; c < N; c++) {
            for (int st = 0; st < N; st++) {
                bool can = true;
                int sc = 0;
                for (int p = 0; p < k; p++) {
                    int r2 = (st + p) % N;
                    char req = s[p];
                    if (mat[r2][c] != '.' && mat[r2][c] != req) {
                        can = false;
                        break;
                    }
                    if (mat[r2][c] == req) sc++;
                }
                if (can && sc > best_sc) {
                    best_dir = 1;
                    best_fixed = c;
                    best_start = st;
                    best_sc = sc;
                }
            }
        }
        if (best_dir != -1) {
            if (best_dir == 0) {
                int r = best_fixed;
                int st = best_start;
                for (int p = 0; p < k; p++) {
                    int c2 = (st + p) % N;
                    if (mat[r][c2] == '.') mat[r][c2] = s[p];
                }
            } else {
                int c = best_fixed;
                int st = best_start;
                for (int p = 0; p < k; p++) {
                    int r2 = (st + p) % N;
                    if (mat[r2][c] == '.') mat[r2][c] = s[p];
                }
            }
        }
    }
    // fill remaining with 'A'
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (mat[i][j] == '.') mat[i][j] = 'A';
        }
    }
    // output
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cout << mat[i][j];
        }
        cout << endl;
    }
    return 0;
}