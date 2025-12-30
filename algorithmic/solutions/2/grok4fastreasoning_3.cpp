#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> perm(n + 1, 0);
    set<int> rem_val, rem_pos;
    for (int i = 1; i <= n; i++) {
        rem_val.insert(i);
        rem_pos.insert(i);
    }
    auto find_pair_pos = [&](int u, int w) -> pair<int, int> {
        vector<vector<char>> possible(n + 1, vector<char>(n + 1, 0));
        int num_unk = rem_pos.size();
        int known_cnt = n - num_unk;
        for (int i = 1; i <= n; i++) {
            if (perm[i] != 0) continue;
            for (int j = 1; j <= n; j++) {
                if (perm[j] != 0 || i == j) continue;
                possible[i][j] = 1;
            }
        }
        while (true) {
            vector<vector<int>> cum(n + 2, vector<int>(n + 2, 0));
            for (int i = 1; i <= n; i++) {
                for (int j = 1; j <= n; j++) {
                    int val = possible[i][j];
                    cum[i][j] = val + cum[i - 1][j] + cum[i][j - 1] - cum[i - 1][j - 1];
                }
            }
            long long total = cum[n][n];
            if (total <= 1) {
                pair<int, int> res = {-1, -1};
                if (total == 1) {
                    for (int i = 1; i <= n; i++) {
                        for (int j = 1; j <= n; j++) {
                            if (possible[i][j]) {
                                res = {i, j};
                            }
                        }
                    }
                }
                return res;
            }
            int best_t = 1;
            long long best_max = LLONG_MAX;
            for (int t = 1; t < n; t++) {
                long long A = cum[t][t];
                long long B = cum[t][n] - A;
                long long C = cum[n][t] - A;
                long long D = total - A - B - C;
                long long n0 = C;
                long long n1 = A + D;
                long long n2 = B;
                long long mx = max({n0, n1, n2});
                if (mx < best_max) {
                    best_max = mx;
                    best_t = t;
                }
            }
            vector<int> Q(n + 1);
            for (int i = 1; i <= n; i++) {
                if (perm[i] != 0) {
                    Q[i] = perm[i];
                } else if (i <= best_t) {
                    Q[i] = u;
                } else {
                    Q[i] = w;
                }
            }
            cout << 0;
            for (int i = 1; i <= n; i++) cout << " " << Q[i];
            cout << endl;
            cout.flush();
            int x;
            cin >> x;
            int effective_x = x - known_cnt;
            vector<vector<char>> new_p(n + 1, vector<char>(n + 1, 0));
            for (int i = 1; i <= n; i++) {
                for (int j = 1; j <= n; j++) {
                    if (possible[i][j]) {
                        int i1 = (i <= best_t ? 1 : 0);
                        int i2 = (j > best_t ? 1 : 0);
                        int comp = i1 + i2;
                        if (comp == effective_x) {
                            new_p[i][j] = 1;
                        }
                    }
                }
            }
            possible = std::move(new_p);
        }
    };
    while (rem_val.size() > 1) {
        auto it = rem_val.begin();
        int u = *it;
        rem_val.erase(it);
        it = rem_val.begin();
        int w = *it;
        rem_val.erase(it);
        pair<int, int> pr = find_pair_pos(u, w);
        int pu = pr.first;
        int pw = pr.second;
        perm[pu] = u;
        perm[pw] = w;
        rem_pos.erase(pu);
        rem_pos.erase(pw);
    }
    if (!rem_val.empty()) {
        int u = *rem_val.begin();
        int p = *rem_pos.begin();
        perm[p] = u;
    }
    cout << 1;
    for (int i = 1; i <= n; i++) cout << " " << perm[i];
    cout << endl;
    cout.flush();
    return 0;
}