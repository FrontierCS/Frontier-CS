#include <bits/stdc++.h>
using namespace std;

int n;
vector<string> C;

bool check(const vector<int>& perm) {
    vector<int> c(n);
    for (int i = 0; i < n-1; i++) {
        int u = perm[i]-1, v = perm[i+1]-1;
        c[i] = C[u][v] - '0';
    }
    int u = perm[n-1]-1, v = perm[0]-1;
    c[n-1] = C[u][v] - '0';
    int changes = 0;
    for (int i = 0; i < n-1; i++) {
        if (c[i] != c[i+1]) changes++;
    }
    return changes <= 1;
}

vector<int> greedy(int start) {
    vector<int> perm;
    vector<bool> used(n+1, false);
    perm.push_back(start);
    used[start] = true;
    int last = start;
    int changes = 0;
    int prev_color = -1;
    for (int i = 2; i <= n; i++) {
        int best_v = -1;
        int best_changes = 1e9;
        for (int v = 1; v <= n; v++) {
            if (used[v]) continue;
            int color = C[last-1][v-1] - '0';
            int new_changes = changes;
            if (i > 2) {
                if (color != prev_color) {
                    new_changes++;
                }
            }
            if (new_changes < best_changes || (new_changes == best_changes && v < best_v)) {
                best_changes = new_changes;
                best_v = v;
            }
        }
        if (best_v == -1) return {};
        int color = C[last-1][best_v-1] - '0';
        if (i > 2 && color != prev_color) changes++;
        perm.push_back(best_v);
        used[best_v] = true;
        prev_color = color;
        last = best_v;
    }
    int close_color = C[last-1][start-1] - '0';
    if (close_color != prev_color) changes++;
    if (changes <= 1) return perm;
    else return {};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    while (cin >> n) {
        C.resize(n);
        for (int i = 0; i < n; i++) {
            cin >> C[i];
        }
        vector<int> ans;
        for (int start = 1; start <= min(n, 10); start++) {
            ans = greedy(start);
            if (!ans.empty()) break;
        }
        if (ans.empty()) {
            cout << -1 << '\n';
        } else {
            for (int i = 0; i < n; i++) {
                cout << ans[i] << " \n"[i==n-1];
            }
        }
    }
    return 0;
}