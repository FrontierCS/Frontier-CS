#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
    }
    int pos1 = 0;
    for (int i = 1; i <= n; ++i) {
        if (p[i] == 1) {
            pos1 = i;
            break;
        }
    }

    auto better = [&](const vector<int>& a, const vector<int>& b) -> bool {
        for (int i = 1; i <= n; ++i) {
            if (a[i] < b[i]) return true;
            if (a[i] > b[i]) return false;
        }
        return false;
    };

    vector<int> best_perm(n + 1);
    for (int i = 1; i <= n; ++i) best_perm[i] = p[i];
    int best_m = 0;
    vector<pair<int, int>> best_ops;

    // Candidate 0: original
    vector<int> orig(n + 1);
    for (int i = 1; i <= n; ++i) orig[i] = p[i];

    // Best 1 op
    vector<int> INF(n + 1, n + 1);
    vector<int> min1 = INF;
    pair<int, int> best1_xy = {-1, -1};
    bool has1 = false;
    for (int x = 1; x <= n - 2; ++x) {
        for (int y = 1; y <= n - 1 - x; ++y) {
            vector<int> temp(n + 1);
            int idx = 1;
            int start_suf = n - y + 1;
            for (int j = start_suf; j <= n; ++j) {
                temp[idx++] = p[j];
            }
            for (int j = x + 1; j <= n - y; ++j) {
                temp[idx++] = p[j];
            }
            for (int j = 1; j <= x; ++j) {
                temp[idx++] = p[j];
            }
            if (better(temp, min1)) {
                min1 = temp;
                best1_xy = {x, y};
                has1 = true;
            }
        }
    }
    if (has1 && better(min1, best_perm)) {
        best_perm = min1;
        best_m = 1;
        best_ops = {best1_xy};
    }

    // Best 2 op if pos1 == 2 and n >= 4
    if (pos1 == 2 && n >= 4) {
        vector<int> best2 = INF;
        vector<pair<int, int>> best2_ops(2, {-1, -1});
        bool has2 = false;
        for (int y0 = 2; y0 <= n - 2; ++y0) {
            // Preliminary op x0=1, y0
            vector<int> p1(n + 1);
            int idx = 1;
            int x0 = 1;
            int start_suf0 = n - y0 + 1;
            for (int j = start_suf0; j <= n; ++j) {
                p1[idx++] = p[j];
            }
            for (int j = x0 + 1; j <= n - y0; ++j) {
                p1[idx++] = p[j];
            }
            for (int j = 1; j <= x0; ++j) {
                p1[idx++] = p[j];
            }
            // Find kp in p1
            int kp = 0;
            for (int j = 1; j <= n; ++j) {
                if (p1[j] == 1) {
                    kp = j;
                    break;
                }
            }
            if (kp < 2) continue;
            int max_xp = kp - 2;
            if (max_xp < 1) continue;
            // Best second for this p1
            vector<int> min_for_this = INF;
            pair<int, int> best_xyp = {-1, -1};
            int yp = n - kp + 1;
            for (int xp = 1; xp <= max_xp; ++xp) {
                vector<int> temp(n + 1);
                int idxx = 1;
                int start_sufp = n - yp + 1;
                for (int j = start_sufp; j <= n; ++j) {
                    temp[idxx++] = p1[j];
                }
                for (int j = xp + 1; j <= n - yp; ++j) {
                    temp[idxx++] = p1[j];
                }
                for (int j = 1; j <= xp; ++j) {
                    temp[idxx++] = p1[j];
                }
                if (better(temp, min_for_this)) {
                    min_for_this = temp;
                    best_xyp = {xp, yp};
                }
            }
            if (best_xyp.first != -1 && better(min_for_this, best2)) {
                best2 = min_for_this;
                best2_ops[0] = {1, y0};
                best2_ops[1] = best_xyp;
                has2 = true;
            }
        }
        if (has2 && better(best2, best_perm)) {
            best_perm = best2;
            best_m = 2;
            best_ops = best2_ops;
        }
    }

    // Output
    cout << best_m << endl;
    for (auto pr : best_ops) {
        cout << pr.first << " " << pr.second << endl;
    }

    return 0;
}