#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> cnt(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < n; j++) {
            int x;
            cin >> x;
            cnt[i][x]++;
        }
    }
    auto dist = [&](int a, int b) -> int {
        return (b - a + n) % n;
    };
    vector<vector<int>> rem(n + 1, vector<int>(n + 1, 0));
    for (int p = 1; p <= n; p++) {
        for (int t = 1; t <= n; t++) {
            int num = cnt[p][t];
            if (num == 0) continue;
            int dpt = dist(p, t);
            for (int j = 1; j <= n; j++) {
                int dpj = dist(p, j);
                if (dpj < dpt) {
                    rem[j][t] += num;
                }
            }
        }
    }
    vector<vector<int>> operations;
    int maxk = n * (n - 1) + 100;
    while (operations.size() < maxk) {
        bool is_solid = true;
        for (int i = 1; i <= n; i++) {
            if (cnt[i][i] != n) {
                is_solid = false;
                break;
            }
        }
        if (is_solid) break;
        vector<int> pass(n + 1);
        for (int j = 1; j <= n; j++) {
            int chosen = -1;
            for (int t = 1; t <= n; t++) {
                if (rem[j][t] > 0 && cnt[j][t] > 0) {
                    chosen = t;
                    break;
                }
            }
            if (chosen != -1) {
                pass[j] = chosen;
                rem[j][chosen]--;
            } else {
                chosen = -1;
                for (int t = 1; t <= n; t++) {
                    if (t != j && cnt[j][t] > 0) {
                        chosen = t;
                        break;
                    }
                }
                if (chosen != -1) {
                    pass[j] = chosen;
                } else {
                    pass[j] = j;
                }
            }
        }
        vector<int> op(n);
        for (int j = 1; j <= n; j++) {
            op[j - 1] = pass[j];
        }
        operations.push_back(op);
        for (int j = 1; j <= n; j++) {
            int t = pass[j];
            cnt[j][t]--;
        }
        vector<int> passed(n + 1);
        for (int j = 1; j <= n; j++) passed[j] = pass[j];
        for (int j = 1; j <= n; j++) {
            int prevj = (j == 1 ? n : j - 1);
            int incoming = passed[prevj];
            cnt[j][incoming]++;
        }
    }
    cout << operations.size() << endl;
    for (auto& op : operations) {
        for (int d : op) {
            cout << d << " ";
        }
        cout << endl;
    }
    return 0;
}