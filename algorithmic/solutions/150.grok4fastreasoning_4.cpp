#include <bits/stdc++.h>
using namespace std;

bool is_covered(const string& s, const vector<vector<char>>& grid) {
    const int N = 20;
    int k = s.size();
    for (int dir = 0; dir < 2; dir++) {
        for (int fixed = 0; fixed < N; fixed++) {
            for (int st = 0; st < N; st++) {
                bool match = true;
                for (int p = 0; p < k && match; p++) {
                    int r = (dir == 0 ? fixed : (st + p) % N);
                    int c = (dir == 0 ? (st + p) % N : fixed);
                    if (grid[r][c] != s[p]) match = false;
                }
                if (match) return true;
            }
        }
    }
    return false;
}

bool try_place(const string& s, vector<vector<char>>& grid) {
    const int N = 20;
    int k = s.size();
    int best_overlap = -1;
    int best_dir = -1, best_fixed = -1, best_start = -1;
    for (int dir = 0; dir < 2; dir++) {
        for (int fixed = 0; fixed < N; fixed++) {
            for (int st = 0; st < N; st++) {
                bool can = true;
                int olap = 0;
                for (int p = 0; p < k && can; p++) {
                    int r = (dir == 0 ? fixed : (st + p) % N);
                    int c = (dir == 0 ? (st + p) % N : fixed);
                    char curr = grid[r][c];
                    if (curr != '.' && curr != s[p]) {
                        can = false;
                    } else if (curr != '.') {
                        olap++;
                    }
                }
                if (can) {
                    bool better = (olap > best_overlap) ||
                                  (olap == best_overlap &&
                                   (dir < best_dir ||
                                    (dir == best_dir &&
                                     (fixed < best_fixed ||
                                      (fixed == best_fixed && st < best_start)))));
                    if (better) {
                        best_overlap = olap;
                        best_dir = dir;
                        best_fixed = fixed;
                        best_start = st;
                    }
                }
            }
        }
    }
    if (best_overlap == -1) return false;
    // place
    int dir = best_dir, fixed = best_fixed, st = best_start;
    for (int p = 0; p < k; p++) {
        int r = (dir == 0 ? fixed : (st + p) % N);
        int c = (dir == 0 ? (st + p) % N : fixed);
        if (grid[r][c] == '.') {
            grid[r][c] = s[p];
        }
    }
    return true;
}

int main() {
    int N, M;
    cin >> N >> M;
    vector<string> reads(M);
    for (auto& str : reads) cin >> str;
    vector<vector<char>> grid(N, vector<char>(N, '.'));
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        int la = reads[a].size(), lb = reads[b].size();
        if (la != lb) return la > lb;
        return a < b;
    });
    for (int ii = 0; ii < M; ii++) {
        int id = order[ii];
        try_place(reads[id], grid);
    }
    int passes = 0;
    const int MAX_PASSES = 50;
    bool improved = true;
    while (improved && passes < MAX_PASSES) {
        passes++;
        improved = false;
        vector<int> uncovered;
        for (int id = 0; id < M; id++) {
            if (!is_covered(reads[id], grid)) uncovered.push_back(id);
        }
        if (uncovered.empty()) break;
        sort(uncovered.begin(), uncovered.end(), [&](int a, int b) {
            int la = reads[a].size(), lb = reads[b].size();
            if (la != lb) return la > lb;
            return a < b;
        });
        for (int id : uncovered) {
            if (try_place(reads[id], grid)) improved = true;
        }
    }
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (grid[i][j] == '.') grid[i][j] = 'A';
        }
    }
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    return 0;
}