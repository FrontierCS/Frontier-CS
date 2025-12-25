#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<string> S(M);
    for (int i = 0; i < M; i++) {
        cin >> S[i];
    }
    vector<vector<char>> grid(N, vector<char>(N, '.'));
    vector<int> idxs(M);
    iota(idxs.begin(), idxs.end(), 0);
    sort(idxs.begin(), idxs.end(), [&](int a, int b) {
        int la = S[a].size(), lb = S[b].size();
        return la > lb || (la == lb && a < b);
    });
    auto try_place = [&](int i, vector<vector<char>>& grid) {
        string s = S[i];
        int k = s.size();
        int best_agree = -1;
        int br = -1, bc = -1, bd = -1;
        bool covered = false;
        for (int d = 0; d < 2; d++) {
            for (int r = 0; r < N; r++) {
                for (int c = 0; c < N; c++) {
                    bool compat = true;
                    int agree = 0;
                    for (int p = 0; p < k; p++) {
                        int x = d ? (r + p) % N : r;
                        int y = d ? c : (c + p) % N;
                        char cur = grid[x][y];
                        char need = s[p];
                        if (cur != '.' && cur != need) {
                            compat = false;
                            break;
                        }
                        if (cur == need) agree++;
                    }
                    if (!compat) continue;
                    if (agree == k) {
                        covered = true;
                    } else {
                        if (agree > best_agree) {
                            best_agree = agree;
                            br = r;
                            bc = c;
                            bd = d;
                        }
                    }
                }
            }
        }
        if (!covered && best_agree >= 0) {
            int r = br, cc = bc, d = bd;
            for (int p = 0; p < k; p++) {
                int x = d ? (r + p) % N : r;
                int y = d ? cc : (cc + p) % N;
                if (grid[x][y] == '.') {
                    grid[x][y] = s[p];
                }
            }
            return true;
        }
        return false;
    };
    // First pass: long to short
    for (int ii : idxs) {
        try_place(ii, grid);
    }
    // Second pass: input order
    for (int i = 0; i < M; i++) {
        try_place(i, grid);
    }
    // Compute uncovered
    auto is_covered_func = [&](int i) -> bool {
        string s = S[i];
        int k = s.size();
        for (int d = 0; d < 2; d++) {
            for (int r = 0; r < N; r++) {
                for (int c = 0; c < N; c++) {
                    bool match = true;
                    for (int p = 0; p < k; p++) {
                        int x = d ? (r + p) % N : r;
                        int y = d ? c : (c + p) % N;
                        if (grid[x][y] != s[p]) {
                            match = false;
                            break;
                        }
                    }
                    if (match) return true;
                }
            }
        }
        return false;
    };
    vector<int> uncovered;
    for (int i = 0; i < M; i++) {
        if (!is_covered_func(i)) {
            uncovered.push_back(i);
        }
    }
    // Place for uncovered
    for (int ii : uncovered) {
        try_place(ii, grid);
    }
    // Fill remaining dots with 'A'
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] == '.') {
                grid[i][j] = 'A';
            }
        }
    }
    // Output
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    return 0;
}